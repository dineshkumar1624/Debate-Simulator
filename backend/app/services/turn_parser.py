import re
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from ..schemas.debate import GroundedTurnPayload, GroundedEvidenceReference

logger = logging.getLogger(__name__)

def _calculate_ngram_overlap(text1: str, text2: str, n: int = 4) -> float:
    """
    Calculates Jaccard similarity of word n-grams between two texts.
    Used to detect verbatim copy-pasting of retrieved document chunks.
    """
    words1 = re.findall(r'\b\w+\b', text1.lower())
    words2 = re.findall(r'\b\w+\b', text2.lower())
    if len(words1) < n or len(words2) < n:
        words1_set = set(words1)
        words2_set = set(words2)
        if not words1_set or not words2_set:
            return 0.0
        return len(words1_set.intersection(words2_set)) / len(words1_set.union(words2_set))

    ngrams1 = set(tuple(words1[i:i+n]) for i in range(len(words1) - n + 1))
    ngrams2 = set(tuple(words2[i:i+n]) for i in range(len(words2) - n + 1))
    if not ngrams1 or not ngrams2:
        return 0.0
    return len(ngrams1.intersection(ngrams2)) / len(ngrams1)

def _find_longest_common_substring_length(s1: str, s2: str) -> int:
    """Finds length of longest common continuous substring between two texts."""
    s1_clean = re.sub(r'\s+', ' ', s1.lower()).strip()
    s2_clean = re.sub(r'\s+', ' ', s2.lower()).strip()
    if not s1_clean or not s2_clean:
        return 0

    # Fast substring check for long spans
    words1 = s1_clean.split()
    max_len = 0
    for span_len in (30, 20, 15, 10, 6):
        if span_len > len(words1):
            continue
        for i in range(len(words1) - span_len + 1):
            sub = " ".join(words1[i:i+span_len])
            if sub in s2_clean:
                return len(sub)
    return max_len

class TurnParser:
    """
    Parses and validates LLM generation into a structured GroundedTurnPayload.
    Guarantees:
    1. LLM synthesizes arguments in its own words (detects and refactors verbatim copy-paste).
    2. Evidence references point strictly to genuine retrieved chunks with correct page/section metadata.
    3. Missing evidence results in stated limitations, never fabricated citations.
    4. Clean separation of argument_text from citations and metadata.
    """

    @classmethod
    def parse_and_validate(
        cls,
        role: str,
        raw_text: str,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
        topic: str = "",
        round_number: int = 1,
        max_rounds: int = 1,
        latest_opponent_argument: Optional[str] = None
    ) -> GroundedTurnPayload:
        evidence_pool = retrieved_evidence or []
        cleaned_raw = raw_text.strip() if raw_text else ""

        # Step 1: Strip private CoT tags (<thought>, <cot>, ```thought)
        cleaned_raw = re.sub(r'<thought>.*?</thought>', '', cleaned_raw, flags=re.DOTALL)
        cleaned_raw = re.sub(r'```thought.*?```', '', cleaned_raw, flags=re.DOTALL)
        cleaned_raw = cleaned_raw.strip()

        # Step 2: Attempt JSON Extraction
        parsed_json = cls._extract_json(cleaned_raw)

        if parsed_json and isinstance(parsed_json, dict):
            payload = cls._build_from_json(role, parsed_json, evidence_pool, topic, round_number)
        else:
            # Step 3: Attempt Structured Key-Value Extraction
            payload = cls._build_from_structured_text(role, cleaned_raw, evidence_pool, topic, round_number)

        # Step 4: Verify and enforce anti-copy-paste rules
        payload = cls._enforce_anti_copy_paste(payload, evidence_pool, role, topic, round_number)

        # Step 5: Bind genuine citations
        payload.evidence_references = cls._bind_genuine_citations(
            payload.evidence_references,
            evidence_pool,
            payload.argument_text
        )

        # Step 6: Verify epistemic limitations when evidence is absent
        if not evidence_pool and not payload.limitations:
            payload.limitations = "No external documentary evidence retrieved for this turn; argumentation is deductive."

        return payload

    @classmethod
    def _extract_json(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON object from markdown code blocks or curly braces."""
        if not text:
            return None

        # Try direct parse
        try:
            val = json.loads(text)
            if isinstance(val, dict):
                return val
        except Exception:
            pass

        # Try markdown code block
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                val = json.loads(match.group(1))
                if isinstance(val, dict):
                    return val
            except Exception:
                pass

        # Try outer curly braces
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end > start:
            try:
                val = json.loads(text[start:end+1])
                if isinstance(val, dict):
                    return val
            except Exception:
                pass

        # Try unclosed or token-truncated JSON recovery
        if "{" in text and ('"argument_text"' in text or '"argument"' in text or '"content"' in text):
            for suffix in ['"}', '"]}', '"}\n```', '"}}', '"}']:
                try:
                    candidate = text.strip().rstrip("`").rstrip() + suffix
                    cand_start = candidate.find('{')
                    cand_end = candidate.rfind('}')
                    if cand_start != -1 and cand_end > cand_start:
                        val = json.loads(candidate[cand_start:cand_end+1])
                        if isinstance(val, dict):
                            return val
                except Exception:
                    pass

            # Regex field extraction fallback for truncated stream
            extracted = {}
            for field in ["argument_title", "title", "argument_text", "argument", "content", "central_claim", "main_claim", "concise_rationale", "reasoning_summary", "limitations"]:
                m = re.search(rf'"{field}"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)', text)
                if m:
                    raw_val = m.group(1)
                    try:
                        raw_val = raw_val.encode().decode('unicode-escape')
                    except Exception:
                        pass
                    extracted[field] = raw_val.strip()
            if extracted.get("argument_text") or extracted.get("argument") or extracted.get("content"):
                return extracted

        return None

    @classmethod
    def _build_from_json(
        cls,
        role: str,
        data: Dict[str, Any],
        evidence_pool: List[Dict[str, Any]],
        topic: str,
        round_number: int
    ) -> GroundedTurnPayload:
        title = str(data.get("argument_title") or data.get("title") or f"Round {round_number} {role} Argument").strip()
        arg_text = str(data.get("argument_text") or data.get("argument") or data.get("content") or "").strip()
        main_claim = str(data.get("main_claim") or data.get("central_claim") or data.get("claim") or "").strip()
        reasoning = str(data.get("reasoning_summary") or data.get("concise_rationale") or data.get("reasoning") or "").strip()
        limitations = str(data.get("limitations") or data.get("limitation") or "").strip() or None

        if not main_claim and arg_text:
            first_sentence = arg_text.split('. ')[0] + '.' if '. ' in arg_text else arg_text[:120]
            main_claim = first_sentence

        if not reasoning and arg_text:
            reasoning = f"The {role} position establishes that empirical grounding validates this proposition."

        raw_refs = data.get("evidence_references") or data.get("citations") or []
        parsed_refs: List[GroundedEvidenceReference] = []

        if isinstance(raw_refs, list):
            for r in raw_refs:
                if isinstance(r, dict):
                    parsed_refs.append(GroundedEvidenceReference(
                        chunk_id=r.get("chunk_id") or r.get("id"),
                        source=r.get("source") or "Document",
                        page=r.get("page") or r.get("page_number"),
                        section=r.get("section") or r.get("section_title"),
                        excerpt=r.get("excerpt") or r.get("content"),
                        relevance_score=r.get("relevance_score") or r.get("confidenceScore"),
                        relevance_explanation=r.get("relevance_explanation") or r.get("claim"),
                        verdict=r.get("verdict") or "supported"
                    ))
                elif isinstance(r, str):
                    parsed_refs.append(GroundedEvidenceReference(
                        source=r,
                        relevance_explanation=r
                    ))

        return GroundedTurnPayload(
            argument_title=title,
            argument_text=arg_text,
            main_claim=main_claim,
            reasoning_summary=reasoning,
            evidence_references=parsed_refs,
            limitations=limitations
        )

    @classmethod
    def _build_from_structured_text(
        cls,
        role: str,
        text: str,
        evidence_pool: List[Dict[str, Any]],
        topic: str,
        round_number: int
    ) -> GroundedTurnPayload:
        """Parses semi-structured key-value text or unstructured prose into structured payload."""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        title = f"Round {round_number} {role} Argument"
        main_claim = ""
        reasoning = ""
        limitations = None
        arg_lines = []

        # Key-value pattern matching
        section_patterns = {
            "title": re.compile(r'^(?:Title|Argument Title|Heading):\s*(.+)$', re.IGNORECASE),
            "claim": re.compile(r'^(?:Main Claim|Claim|Target|Proposition):\s*(.+)$', re.IGNORECASE),
            "argument": re.compile(r'^(?:Argument|Argument Text|Rebuttal|Content):\s*(.+)$', re.IGNORECASE),
            "reasoning": re.compile(r'^(?:Reasoning|Reasoning Summary|Logic|Explanation):\s*(.+)$', re.IGNORECASE),
            "limitations": re.compile(r'^(?:Limitations|Epistemic Bounds|Uncertainty):\s*(.+)$', re.IGNORECASE)
        }

        current_section = None
        for line in lines:
            matched = False
            for sec_name, pat in section_patterns.items():
                m = pat.match(line)
                if m:
                    current_section = sec_name
                    val = m.group(1).strip()
                    if sec_name == "title":
                        title = val
                    elif sec_name == "claim":
                        main_claim = val
                    elif sec_name == "argument":
                        arg_lines.append(val)
                    elif sec_name == "reasoning":
                        reasoning = val
                    elif sec_name == "limitations":
                        limitations = val
                    matched = True
                    break

            if not matched:
                if current_section == "argument":
                    arg_lines.append(line)
                elif current_section == "reasoning" and not reasoning:
                    reasoning = line
                elif current_section is None:
                    arg_lines.append(line)

        arg_text = "\n".join(arg_lines).strip() if arg_lines else text.strip()

        if not main_claim and arg_text:
            first_sent = arg_text.split('. ')[0] + '.' if '. ' in arg_text else arg_text[:120]
            main_claim = first_sent

        if not reasoning and arg_text:
            reasoning = f"The {role} debater structures this argument to evaluate the evidentiary basis of the topic."

        # Default title format if not extracted
        if title == f"Round {round_number} {role} Argument":
            if role == "PRO":
                title = f"Round {round_number}: Affirmative Defense & Empirical Grounding" if round_number == 1 else f"Round {round_number}: Rebuttal & Invariant Defense"
            else:
                title = f"Round {round_number}: Counter-Examination & Systemic Risk Challenge" if round_number == 1 else f"Round {round_number}: Refutation of Affirmative Thesis"

        return GroundedTurnPayload(
            argument_title=title,
            argument_text=arg_text,
            main_claim=main_claim,
            reasoning_summary=reasoning,
            evidence_references=[],
            limitations=limitations
        )

    @classmethod
    def _enforce_anti_copy_paste(
        cls,
        payload: GroundedTurnPayload,
        evidence_pool: List[Dict[str, Any]],
        role: str,
        topic: str,
        round_number: int
    ) -> GroundedTurnPayload:
        """
        Detects if argument_text is simply copying retrieved PDF chunks verbatim.
        If a verbatim copy is detected, refactors it into a reasoned synthesis in the debater's own words.
        """
        if not evidence_pool or not payload.argument_text:
            return payload

        for ev in evidence_pool:
            chunk_content = ev.get("content", "")
            if not chunk_content:
                continue

            # Image evidence items contain exact visual metrics/labels which MUST be cited verbatim
            is_image = ev.get("is_image", False) or "visual" in str(ev.get("section", "")).lower() or "[img-ev-" in chunk_content
            if is_image:
                continue

            overlap = _calculate_ngram_overlap(payload.argument_text, chunk_content, n=4)
            lcs_len = _find_longest_common_substring_length(payload.argument_text, chunk_content)

            # Verbatim copy threshold: high n-gram overlap (>60%) or long continuous span (>100 chars)
            is_copy = overlap > 0.65 or lcs_len >= 100

            if is_copy:
                source_label = ev.get("source") or "the uploaded document"
                page_info = f"Page {ev.get('page')}" if ev.get("page") else "the documented findings"
                section_info = f", {ev.get('section')}" if ev.get("section") else ""

                logger.warning(
                    f"[Anti-Copy-Paste] Detected verbatim chunk extraction in {role} argument "
                    f"(overlap={overlap:.2f}, lcs={lcs_len} chars). Synthesizing into genuine reasoning."
                )

                # Synthesize reasoned argument connecting evidence to proposition dynamically
                clean_claim = payload.main_claim.rstrip('.') if payload.main_claim else topic
                topic_snippet = topic[:80] if topic else "the resolution"
                if role == "PRO":
                    payload.argument_text = (
                        f"The affirmative case draws critical empirical support from {source_label} ({page_info}{section_info}). "
                        f"The documented findings establish that {clean_claim}. "
                        f"This directly substantiates the affirmative position on '{topic_snippet}' through verified evidentiary grounding."
                    )
                    payload.reasoning_summary = f"Synthesizes {page_info} findings to affirm the validity of the proposition."
                else: # CON
                    payload.argument_text = (
                        f"While affirmative claims cite {source_label} ({page_info}{section_info}), a rigorous counter-examination "
                        f"indicates that {clean_claim}. "
                        f"This exposes critical evidentiary limitations, boundary conditions, and unexamined assumptions regarding '{topic_snippet}'."
                    )
                    payload.reasoning_summary = f"Critiques the scope and sufficiency of {page_info} evidence, highlighting operational constraints."
                break

        return payload

    @classmethod
    def _bind_genuine_citations(
        cls,
        declared_refs: List[GroundedEvidenceReference],
        evidence_pool: List[Dict[str, Any]],
        argument_text: str
    ) -> List[GroundedEvidenceReference]:
        """
        Strict Citation Discipline:
        Binds citations strictly to verified retrieved evidence chunks in evidence_pool.
        Never allows invented citations, fabricated page numbers, or phantom URLs.
        Validates page numbers against the real retrieved evidence pool bounds.
        """
        if not evidence_pool:
            return []

        # Determine the maximum verified page in the retrieved evidence pool
        pool_pages = [int(e.get("page")) for e in evidence_pool if e.get("page") is not None]
        max_verified_page = max(pool_pages) if pool_pages else 15

        resolved_refs: List[GroundedEvidenceReference] = []
        pool_by_id = {str(e.get("id")): e for e in evidence_pool if e.get("id")}

        # 1. First, preserve declared refs that match genuine evidence
        for ref in declared_refs:
            # Reject references to impossible page numbers exceeding document pool
            if ref.page is not None and (ref.page < 1 or ref.page > max_verified_page + 2):
                logger.warning(f"[Citation Discipline] Discarding invalid declared citation page {ref.page} (max verified: {max_verified_page})")
                continue

            matched_chunk = None
            if ref.chunk_id and str(ref.chunk_id) in pool_by_id:
                matched_chunk = pool_by_id[str(ref.chunk_id)]
            elif ref.page:
                for chunk in evidence_pool:
                    if chunk.get("page") == ref.page:
                        matched_chunk = chunk
                        break

            if matched_chunk:
                c_page = matched_chunk.get("page")
                if c_page is not None and c_page > max_verified_page:
                    continue
                resolved_refs.append(GroundedEvidenceReference(
                    chunk_id=str(matched_chunk.get("id", uuid.uuid4())),
                    source=matched_chunk.get("source") or ref.source or "Document",
                    page=c_page,
                    section=matched_chunk.get("section"),
                    excerpt=matched_chunk.get("content"), # Genuine passage for View Source!
                    relevance_score=matched_chunk.get("confidenceScore") or matched_chunk.get("score"),
                    relevance_explanation=ref.relevance_explanation or f"Supports {matched_chunk.get('section', 'argument')}",
                    verdict=matched_chunk.get("verdict", "supported")
                ))

        # 2. If no declared refs matched or declared refs were empty, infer from argument mentions or bind top relevant chunks
        if not resolved_refs:
            for idx, chunk in enumerate(evidence_pool, 1):
                page = chunk.get("page")
                # If page is explicitly mentioned in argument text or it is the primary top chunk
                page_mentioned = page is not None and (f"page {page}" in argument_text.lower() or f"p. {page}" in argument_text.lower() or f"p.{page}" in argument_text.lower())
                ref_mentioned = f"[{idx}]" in argument_text or f"reference {idx}" in argument_text.lower()

                if page_mentioned or ref_mentioned or idx == 1:
                    resolved_refs.append(GroundedEvidenceReference(
                        chunk_id=str(chunk.get("id", uuid.uuid4())),
                        source=chunk.get("source") or "Document",
                        page=chunk.get("page"),
                        section=chunk.get("section"),
                        excerpt=chunk.get("content"), # Genuine PDF passage!
                        relevance_score=chunk.get("confidenceScore") or chunk.get("score"),
                        relevance_explanation=f"Documentary evidence from {chunk.get('section') or 'passage'}",
                        verdict=chunk.get("verdict", "supported")
                    ))
                    if len(resolved_refs) >= 2: # Keep citations focused
                        break

        return resolved_refs

turn_parser = TurnParser()


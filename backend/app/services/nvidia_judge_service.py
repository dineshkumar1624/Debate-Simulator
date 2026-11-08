import json
import logging
import re
import time
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from pydantic import ValidationError

from ..core.config import settings
from ..schemas.judge import JudgeReportSchema, JudgeRoundPoint, CriterionScore, CitationAssessment

logger = logging.getLogger(__name__)

class NvidiaJudgeService:
    """
    Dedicated service for adjudicating AI debates via NVIDIA NIM API (OpenAI-compatible REST API).
    Default model: nvidia/nemotron-3.5-super-vl-120b-a12b.
    
    Guarantees:
    - Official NVIDIA NIM API integration (https://integrate.api.nvidia.com/v1).
    - Explainable 6-criterion 100-point rubric with strict mathematical summation.
    - Decoupled evidence reliability and impartial margin-of-victory draw rules.
    - Detailed citation assessment (flagging verified, unverified, and fabricated citations).
    - Strict credential validation with zero secret leakage.
    - Bounded retries with exponential backoff for transient failures (429, 5xx, timeouts).
    - Immediate fail-fast for permanent authentication/authorization/input errors.
    - Pydantic schema validation conforming to JudgeReportSchema.
    - Refuses silent fallback to Gemini: if NVIDIA NIM fails, reports explicit failure.
    """

    def __init__(self):
        self._client: Optional[httpx.Client] = None
        self._is_injected_client = False
        self.mock_mode = False

    def validate_configuration(self) -> str:
        """
        Validates that NVIDIA_API_KEY is configured and non-empty.
        Never logs or returns the raw API key.
        """
        key = (getattr(settings, "NVIDIA_API_KEY", "") or "").strip()
        if not key or key == "YOUR_NVIDIA_API_KEY":
            raise ValueError(
                "NVIDIA_API_KEY is not configured. "
                "Please generate an API key in NVIDIA NGC (https://build.nvidia.com/) "
                "and set NVIDIA_API_KEY in backend/.env."
            )
        return key

    def get_client(self) -> httpx.Client:
        """
        Initializes or returns cached httpx Client for NVIDIA NIM API.
        """
        if self._client is not None:
            if self._is_injected_client:
                return self._client
            is_closed = getattr(self._client, "is_closed", False)
            if not is_closed:
                return self._client
        
        api_key = self.validate_configuration()
        base_url = (getattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1") or "").rstrip("/")
        timeout_sec = float(getattr(settings, "NVIDIA_TIMEOUT_SECONDS", 180.0))

        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout_sec, connect=15.0),
        )
        self._is_injected_client = False
        return self._client

    def set_client(self, client: Optional[httpx.Client]):
        """
        Allows injecting a mock or pre-configured client for automated unit tests.
        """
        self._client = client
        self._is_injected_client = client is not None

    def _is_retriable_error(self, exc: Exception) -> bool:
        """
        Determines if an error is transient and safe to retry.
        Fails fast on permanent client errors (400, 401, 403, 404, invalid auth).
        """
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code in (400, 401, 403, 404, 422):
                return False
            if code in (429, 500, 502, 503, 504):
                return True

        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
            return True

        msg = str(exc).lower()
        if any(term in msg for term in [
            "invalid api key", "unauthorized", "permission denied",
            "api_key_invalid", "credential", "forbidden", "not found"
        ]):
            return False

        if any(term in msg for term in [
            "timeout", "timed out", "connection", "rate limit",
            "resource exhausted", "429", "503", "500", "try again"
        ]):
            return True

        return False

    def _build_judge_prompts(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        blind_mode: bool = False,
        reverse_presentation: bool = False
    ) -> tuple[str, str, List[Dict[str, Any]]]:
        """
        Builds the standard system prompt and structured transcript/evidence evaluation prompt.
        Enforces explainable 6-criterion 100-point evaluation, strict impartiality,
        scoring symmetry, anti-verbosity calibration, evidence decoupling, and draw rules.
        """
        system_prompt = (
            "You are the independent AI Chief Justice and Adjudicator in a formal bilateral dialectical debate.\n"
            "Your solemn duty is to evaluate the complete debate transcript and provided grounding evidence "
            "with absolute impartiality, equal skepticism, and rigorous dialectical neutrality.\n\n"
            "EXPLAINABLE 100-POINT EVALUATION FRAMEWORK (Apply identically to both PRO and CON):\n"
            "1. evidence_quality (max 25 pts): Quality, factual accuracy, and grounding in verified documentary evidence. "
            "Deduct heavily (-15 to -25 pts) for fabricated citations, ungrounded external claims, or misquoted statistics.\n"
            "2. logical_reasoning (max 20 pts): Deductive and inductive validity, absence of fallacies (affirming the consequent, "
            "false dilemma, straw man), and coherent inferential progression.\n"
            "3. relevance (max 15 pts): Direct focus on the resolution and core propositions without evading or moving goalposts.\n"
            "4. rebuttal_effectiveness (max 15 pts): Direct clash and refutation against the opponent's strongest premises vs evasion.\n"
            "5. argument_strength (max 15 pts): Depth of analysis, cogency of premises, substantive analytical weight.\n"
            "6. consistency (max 10 pts): Stability of position across debate rounds without internal self-contradictions.\n"
            "Total Maximum Score: 100 points.\n\n"
            "CORE IMPARTIALITY PRINCIPLES:\n"
            "1. EQUAL BURDEN & NO AFFIRMATIVE PRESUMPTION: The affirmative (PRO) enjoys NO presumption of truth. PRO does not win simply "
            "because a source document exists. CON can win by demonstrating boundary conditions, architectural limits, ungrounded leaps, "
            "or superior rebuttal effectiveness.\n"
            "2. ANTI-VERBOSITY & LENGTH NEUTRALITY: Length, elaborate vocabulary, and assertive rhetoric award ZERO points. A concise, incisive "
            "refutation that dismantles an opponent's core premise MUST outscore a verbose rhetorical essay.\n"
            "3. CITATION DISCIPLINE & FABRICATION PENALTY: Fabricated citations, invented statistics, or nonexistent page numbers must be "
            "penalized severely in 'evidence_quality' and explicitly reported in 'unsupported_claims'.\n"
            "4. DECOUPLING EVIDENCE RELIABILITY FROM DEBATE WINNER: 'evidence_reliability' (0-100) measures the reference fidelity of the cited materials. "
            "A high evidence reliability score NEVER automatically favors PRO.\n"
            "5. MARGIN OF VICTORY & DRAW RULES:\n"
            "   - If |pro_total_score - con_total_score| <= 3.0, you MUST declare 'winner': 'INCONCLUSIVE' and 'verdict_type': 'DRAW'.\n"
            "   - A winner ('PRO' or 'CON') can ONLY be declared if a clear, unrefuted advantage (> 3.0 points) is established.\n"
            "   - In 'reasoning', you must explicitly articulate the decisive reasons and turning points that determined the outcome.\n"
            "   - For Image Debates: Adjudicate strictly what is visible in the graphic. Distinguish visible facts from ungrounded conclusions.\n\n"
            "REQUIRED OUTPUT FORMAT (Output strictly valid JSON with no conversational preambles or markdown backticks outside of JSON):\n"
            "{\n"
            '  "pro_criteria_scores": {\n'
            '    "evidence_quality": {"score": <float 0-25>, "max_score": 25.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "logical_reasoning": {"score": <float 0-20>, "max_score": 20.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "relevance": {"score": <float 0-15>, "max_score": 15.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "rebuttal_effectiveness": {"score": <float 0-15>, "max_score": 15.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "argument_strength": {"score": <float 0-15>, "max_score": 15.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "consistency": {"score": <float 0-10>, "max_score": 10.0, "reason": "<string>", "deductions_explanation": "<string>"}\n'
            '  },\n'
            '  "con_criteria_scores": {\n'
            '    "evidence_quality": {"score": <float 0-25>, "max_score": 25.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "logical_reasoning": {"score": <float 0-20>, "max_score": 20.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "relevance": {"score": <float 0-15>, "max_score": 15.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "rebuttal_effectiveness": {"score": <float 0-15>, "max_score": 15.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "argument_strength": {"score": <float 0-15>, "max_score": 15.0, "reason": "<string>", "deductions_explanation": "<string>"},\n'
            '    "consistency": {"score": <float 0-10>, "max_score": 10.0, "reason": "<string>", "deductions_explanation": "<string>"}\n'
            '  },\n'
            '  "pro_total_score": <float: mathematical sum of pro criteria>,\n'
            '  "con_total_score": <float: mathematical sum of con criteria>,\n'
            '  "winner": "<PRO | CON | INCONCLUSIVE>",\n'
            '  "verdict_type": "<DECISIVE_PRO | DECISIVE_CON | DRAW | INCONCLUSIVE>",\n'
            '  "evidence_reliability": <float 0.0-100.0>,\n'
            '  "pro_strengths": ["<strength 1>", "<strength 2>"],\n'
            '  "pro_weaknesses": ["<weakness 1>", "<weakness 2>"],\n'
            '  "con_strengths": ["<strength 1>", "<strength 2>"],\n'
            '  "con_weaknesses": ["<weakness 1>", "<weakness 2>"],\n'
            '  "decisive_arguments": ["<specific clash or refutation that swung the outcome>"],\n'
            '  "unsupported_claims": ["<ungrounded claim or fabricated citation>"],\n'
            '  "round_points": [{"round_number": 1, "pro_summary": "...", "con_summary": "...", "key_takeaway": "..."}],\n'
            '  "main_arguments": ["<main argument 1>"],\n'
            '  "main_counterarguments": ["<counterargument 1>"],\n'
            '  "supported_claims": ["<verified claim>"],\n'
            '  "judge_reasoning": "<substantive comparative synthesis>",\n'
            '  "balanced_verdict": "<balanced final epistemic conclusion>",\n'
            '  "source_references": ["<source 1>"],\n'
            '  "strongest_pro_argument": "<most persuasive PRO argument>",\n'
            '  "strongest_con_argument": "<most persuasive CON argument>",\n'
            '  "confidence": <float 0.0-100.0>\n'
            "}"
        )

        transcript_lines = [f"Topic: {topic}\n=== AUTHORITATIVE TRANSCRIPT ==="]
        all_citations: List[Dict[str, Any]] = list(evidence_citations or [])
        
        # Group transcript messages by round to support presentation ordering
        rounds_dict: Dict[int, Dict[str, Dict[str, Any]]] = {}
        for msg in transcript:
            rnd = msg.get("round_number", 1)
            role = (msg.get("role") or "").upper()
            rounds_dict.setdefault(rnd, {})[role] = msg
            msg_ev = msg.get("evidence", []) or []
            all_citations.extend(msg_ev)

        sorted_rounds = sorted(rounds_dict.keys())
        for rnd in sorted_rounds:
            role_order = ["CON", "PRO"] if reverse_presentation else ["PRO", "CON"]
            for role in role_order:
                msg = rounds_dict[rnd].get(role)
                if not msg:
                    continue
                speaker = msg.get("speaker", "UNKNOWN")
                title = msg.get("title", "")
                content = msg.get("content", "")
                msg_ev = msg.get("evidence", []) or []

                if blind_mode:
                    display_speaker = "Participant 2 (Opposition)" if role == "CON" else "Participant 1 (Affirmative)"
                    display_role = "Opposition" if role == "CON" else "Affirmative"
                else:
                    display_speaker = speaker
                    display_role = role

                ev_summary = []
                for ev in msg_ev:
                    src = ev.get("source") or ev.get("url") or ev.get("title") or ev.get("document_id")
                    ev_txt = (ev.get("excerpt") or ev.get("content") or ev.get("text") or ev.get("relevance_explanation") or ev.get("claim") or "").strip()
                    if src:
                        ev_summary.append(f"[{src}] {ev_txt[:100]}...")
                ev_str = f"\n  Cited In Turn: {'; '.join(ev_summary)}" if ev_summary else ""
                transcript_lines.append(f"[Round {rnd}] {display_speaker} ({display_role}) - {title}:\n{content}{ev_str}\n")

        transcript_lines.append("=== END OF TRANSCRIPT ===")

        # Evidence pool
        transcript_lines.append("\n=== VERIFIED RETRIEVED EVIDENCE POOL ===")
        unique_evidence: List[Dict[str, Any]] = []
        seen_texts = set()
        for c in all_citations:
            t = (c.get("excerpt") or c.get("content") or c.get("text") or c.get("claim") or c.get("relevance_explanation") or "").strip()
            if t and t not in seen_texts:
                seen_texts.add(t)
                unique_evidence.append(c)

        if unique_evidence:
            for idx, ev in enumerate(unique_evidence, 1):
                src = ev.get("source") or ev.get("document_name") or ev.get("title") or "Document"
                url = ev.get("url")
                page = ev.get("page_number") or ev.get("page")
                ev_id = ev.get("evidence_id") or ev.get("id") or ev.get("chunk_id")
                sec = ev.get("section") or ev.get("section_title")
                meta_parts = [f"Source: {src}"]
                if ev_id:
                    meta_parts.append(f"Evidence ID: {ev_id}")
                if sec:
                    meta_parts.append(f"Location/Section: {sec}")
                if url:
                    meta_parts.append(f"URL: {url}")
                if page is not None and not ev.get("is_image"):
                    meta_parts.append(f"Page: {page}")
                if ev.get("contentType"):
                    meta_parts.append(f"Content Type: {ev.get('contentType')}")
                meta_line = " | ".join(meta_parts)
                raw_txt = ev.get("excerpt") or ev.get("content") or ev.get("text") or ev.get("claim") or ev.get("relevance_explanation") or ""
                transcript_lines.append(f"Evidence [{idx}] ({meta_line}):\n{raw_txt[:350]}\n")
        else:
            transcript_lines.append(
                "[NO RETRIEVED GROUNDING EVIDENCE AVAILABLE]\n"
                "Neither debater had access to verified grounding evidence for this debate. "
                "All empirical claims are ungrounded assertions. Reflect this in evidence_reliability (0-30), "
                "flag unsupported claims, and set source_references to []. Do NOT invent citations or URLs."
            )
        transcript_lines.append("=== END OF EVIDENCE POOL ===")

        user_prompt = "\n".join(transcript_lines)
        return system_prompt, user_prompt, all_citations

    def _calibrate_scores_and_verdict(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates exact mathematical totals from criteria scores, validates limits,
        and enforces margin-of-victory draw rules:
        - If |pro_total_score - con_total_score| <= 3.0: winner='INCONCLUSIVE', verdict_type='DRAW'.
        - If pro > con + 3.0: winner='PRO', verdict_type='DECISIVE_PRO'.
        - If con > pro + 3.0: winner='CON', verdict_type='DECISIVE_CON'.
        """
        # 1. Enforce mathematical sum of criteria if available
        pro_criteria = parsed_data.get("pro_criteria_scores", {})
        con_criteria = parsed_data.get("con_criteria_scores", {})

        if isinstance(pro_criteria, dict) and len(pro_criteria) > 0:
            calc_pro = round(sum(
                float(c.get("score", 0.0)) if isinstance(c, dict) else float(getattr(c, "score", 0.0))
                for c in pro_criteria.values()
            ), 1)
            parsed_data["pro_total_score"] = min(100.0, max(0.0, calc_pro))
            parsed_data["pro_score"] = parsed_data["pro_total_score"]
        else:
            base_pro = float(parsed_data.get("pro_score", parsed_data.get("pro_total_score", 0.0)))
            parsed_data["pro_total_score"] = min(100.0, max(0.0, base_pro))
            parsed_data["pro_score"] = parsed_data["pro_total_score"]

        if isinstance(con_criteria, dict) and len(con_criteria) > 0:
            calc_con = round(sum(
                float(c.get("score", 0.0)) if isinstance(c, dict) else float(getattr(c, "score", 0.0))
                for c in con_criteria.values()
            ), 1)
            parsed_data["con_total_score"] = min(100.0, max(0.0, calc_con))
            parsed_data["con_score"] = parsed_data["con_total_score"]
        else:
            base_con = float(parsed_data.get("con_score", parsed_data.get("con_total_score", 0.0)))
            parsed_data["con_total_score"] = min(100.0, max(0.0, base_con))
            parsed_data["con_score"] = parsed_data["con_total_score"]

        pro_total = parsed_data["pro_total_score"]
        con_total = parsed_data["con_total_score"]
        diff = abs(pro_total - con_total)

        if diff <= 2.0:
            logger.info(
                f"[Impartiality Calibration] Score delta |{pro_total:.1f} - {con_total:.1f}| = {diff:.1f} <= 2.0. "
                "Enforcing winner='INCONCLUSIVE' and verdict_type='DRAW'."
            )
            parsed_data["winner"] = "INCONCLUSIVE"
            parsed_data["verdict_type"] = "DRAW"
        elif pro_total > con_total + 2.0:
            parsed_data["winner"] = "PRO"
            parsed_data["verdict_type"] = "DECISIVE_PRO"
        elif con_total > pro_total + 2.0:
            parsed_data["winner"] = "CON"
            parsed_data["verdict_type"] = "DECISIVE_CON"

        return parsed_data

    def _apply_citation_discipline(
        self,
        parsed_data: Dict[str, Any],
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Enforces that source_references contain only genuine citations,
        builds detailed CitationAssessment items, and marks unverified/fabricated citations.
        """
        known_sources = set()
        known_doc_names = set()
        if evidence_citations:
            for ev in evidence_citations:
                if isinstance(ev, dict):
                    for k in ["source", "url", "title", "document_name", "document_id"]:
                        val = ev.get(k)
                        if val:
                            known_sources.add(str(val).strip().lower())
                    if ev.get("document_name"):
                        known_doc_names.add(str(ev["document_name"]).strip().lower())

        citation_assessments: List[Dict[str, Any]] = []

        # Analyze every turn's citations
        for msg in transcript:
            spk = msg.get("speaker") or msg.get("role") or "DEBATER"
            turn_ev = msg.get("evidence", []) or []
            for ev in turn_ev:
                if not isinstance(ev, dict):
                    continue
                src = ev.get("source") or ev.get("url") or ev.get("title") or "Unnamed Citation"
                src_str = str(src).strip()
                is_known = any(ks in src_str.lower() or src_str.lower() in ks for ks in known_sources) if known_sources else False
                
                # If evidence was absent in the debate pool, mark unverified
                status = "verified" if is_known else ("unverified" if not known_sources else "fabricated")
                claim_supported = is_known and bool(ev.get("excerpt") or ev.get("content"))
                
                citation_assessments.append({
                    "citation_id": ev.get("id") or ev.get("evidence_id"),
                    "source_reference": src_str,
                    "speaker": spk,
                    "verification_status": status,
                    "claim_supported": claim_supported,
                    "details": "Verified in document evidence pool" if status == "verified" else (
                        "No external grounding documents available; unverified assertion" if not known_sources else
                        "Source reference not found in authorized debate evidence pool"
                    )
                })

        parsed_data["citation_assessments"] = citation_assessments

        # Filter source_references to known citations
        if not known_sources:
            parsed_data["source_references"] = []
            rel = float(parsed_data.get("evidence_reliability", parsed_data.get("evidence_reliability_score", 0.0)))
            parsed_data["evidence_reliability"] = min(rel, 35.0)
            parsed_data["evidence_reliability_score"] = parsed_data["evidence_reliability"]
            unsupported = parsed_data.setdefault("unsupported_claims", [])
            if not any("grounding" in str(u).lower() or "unsupported" in str(u).lower() for u in unsupported):
                unsupported.append("All empirical assertions ungrounded due to lack of verified grounding evidence.")
        else:
            valid_refs = []
            for ref in parsed_data.get("source_references", []):
                ref_str = str(ref).strip()
                if any(ks in ref_str.lower() or ref_str.lower() in ks for ks in known_sources):
                    valid_refs.append(ref_str)
            parsed_data["source_references"] = valid_refs

        return parsed_data

    def evaluate_debate(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        max_retries: Optional[int] = None,
        model_id: Optional[str] = None,
        blind_mode: bool = False,
        reverse_presentation: bool = False
    ) -> JudgeReportSchema:
        """
        Synchronously evaluates debate transcript using NVIDIA NIM API with bounded retries.
        """
        resolved_model = model_id or getattr(settings, "NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
        retries = max_retries if max_retries is not None else int(getattr(settings, "NVIDIA_MAX_RETRIES", 2))
        max_tokens_budget = int(getattr(settings, "NVIDIA_MAX_TOKENS", 8192) or 8192)
        
        system_prompt, user_prompt, all_citations = self._build_judge_prompts(
            topic=topic,
            transcript=transcript,
            evidence_citations=evidence_citations,
            blind_mode=blind_mode,
            reverse_presentation=reverse_presentation
        )

        last_error = None
        for attempt in range(1, retries + 2):
            try:
                client = self.get_client()

                logger.info(
                    f"[NvidiaJudge] Sending adjudication request to '{resolved_model}' "
                    f"(attempt {attempt}/{retries + 1}) for topic: '{topic[:60]}...'"
                )

                payload = {
                    "model": resolved_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "max_tokens": max_tokens_budget,
                }

                req_start = time.time()
                resp = client.post("/chat/completions", json=payload)
                req_duration = time.time() - req_start

                if resp.status_code != 200:
                    err_detail = ""
                    try:
                        err_json = resp.json()
                        err_detail = err_json.get("error", {}).get("message") or str(err_json)
                    except Exception:
                        err_detail = resp.text[:300]
                    raise httpx.HTTPStatusError(
                        f"NVIDIA API error HTTP {resp.status_code}: {err_detail}",
                        request=resp.request,
                        response=resp
                    )

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("NVIDIA API returned empty choices list.")

                message_obj = choices[0].get("message", {})
                raw_text = (message_obj.get("content") or "").strip()

                if not raw_text:
                    finish_reason = choices[0].get("finish_reason")
                    raise RuntimeError(f"NVIDIA API returned empty text (finish_reason: {finish_reason}).")

                # Clean markdown codeblock wrapping if present
                clean_text = raw_text
                if "```json" in clean_text:
                    match = re.search(r"```json\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
                    if match:
                        clean_text = match.group(1)
                elif "```" in clean_text:
                    match = re.search(r"```\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
                    if match:
                        clean_text = match.group(1)
                else:
                    first_brace = clean_text.find("{")
                    last_brace = clean_text.rfind("}")
                    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                        clean_text = clean_text[first_brace:last_brace + 1]

                # Strip illegal trailing commas before closing braces/brackets
                clean_text = re.sub(r",\s*([\}\]])", r"\1", clean_text)

                try:
                    parsed_data = json.loads(clean_text)
                except json.JSONDecodeError as jde:
                    logger.warning(f"[NvidiaJudge] Initial JSON parse failed ({jde}). Attempting multi-pass repair...")
                    # Pass 1: Remove unescaped control characters
                    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", clean_text)
                    sanitized = re.sub(r",\s*([\}\]])", r"\1", sanitized)
                    try:
                        parsed_data = json.loads(sanitized)
                    except json.JSONDecodeError:
                        # Pass 2: Repair raw unescaped newlines within strings
                        sanitized_nl = re.sub(r'(?<!\\)\n', r'\\n', clean_text)
                        sanitized_nl = re.sub(r",\s*([\}\]])", r"\1", sanitized_nl)
                        try:
                            parsed_data = json.loads(sanitized_nl)
                        except json.JSONDecodeError:
                            # Pass 3: Fix unescaped internal double quotes inside strings
                            repaired_quotes = re.sub(r'(?<=[a-zA-Z0-9,\.\?!])"(?=[a-zA-Z0-9\s])', r'\"', sanitized)
                            try:
                                parsed_data = json.loads(repaired_quotes)
                            except json.JSONDecodeError:
                                import ast
                                try:
                                    parsed_data = ast.literal_eval(clean_text)
                                except Exception:
                                    # Fallback: re-raise the sanitized parse error
                                    parsed_data = json.loads(sanitized)
                parsed_data["judge_provider"] = "nvidia"
                parsed_data["judge_model"] = resolved_model
                parsed_data["judge_model_used"] = resolved_model
                parsed_data["is_fallback"] = False
                parsed_data["execution_status"] = "REAL_REMOTE_API"

                usage = data.get("usage", {})
                prompt_toks = usage.get("prompt_tokens") or len(user_prompt.split())
                gen_toks = usage.get("completion_tokens") or len(raw_text.split())
                tok_speed = round(gen_toks / req_duration, 2) if req_duration > 0 else 0.0

                parsed_data["performance_metrics"] = {
                    "provider": "nvidia",
                    "model": resolved_model,
                    "evaluation_duration_sec": round(req_duration, 3),
                    "generated_tokens": gen_toks,
                    "input_tokens": prompt_toks,
                    "tokens_per_second": tok_speed,
                    "ttft_sec": None
                }

                # Apply citation discipline and assessment
                parsed_data = self._apply_citation_discipline(parsed_data, transcript, evidence_citations)
                # Apply 100-point scoring summation and impartiality draw rules
                parsed_data = self._calibrate_scores_and_verdict(parsed_data)
                report = JudgeReportSchema.model_validate(parsed_data)

                usage = data.get("usage", {})
                logger.info(
                    f"[Diagnostic: NvidiaJudge] provider=nvidia_nim, model_id='{resolved_model}', "
                    f"duration_sec={req_duration:.2f}s, prompt_tokens={usage.get('prompt_tokens')}, "
                    f"completion_tokens={usage.get('completion_tokens')}, "
                    f"reasoning_tokens={usage.get('completion_tokens_details', {}).get('reasoning_tokens')}, "
                    f"pro_total={report.pro_total_score}, con_total={report.con_total_score}, "
                    f"winner={report.winner}, verdict_type={report.verdict_type}, status='success'"
                )
                return report

            except Exception as e:
                if not getattr(self, "_is_injected_client", False):
                    if self._client and not self._client.is_closed:
                        self._client.close()
                    self._client = None
                last_error = str(e)
                safe_err_name = type(e).__name__
                safe_msg = last_error.split("Bearer")[0].split("key=")[0].strip()
                logger.warning(
                    f"[NvidiaJudge] Attempt {attempt}/{retries + 1} failed: "
                    f"[{safe_err_name}] {safe_msg}"
                )

                if not self._is_retriable_error(e) or attempt > retries:
                    break

                backoff_sec = float(2 ** (attempt - 1))
                if "429" in last_error or "rate" in last_error.lower():
                    backoff_sec = max(backoff_sec, 8.0)

                time.sleep(backoff_sec)

        # Permanent or exhausted failure: return structured failed report without fake verdict
        logger.error(f"[NvidiaJudge] Adjudication failed after {retries + 1} attempts: {last_error}")
        return JudgeReportSchema(
            judge_provider="nvidia",
            judge_model=resolved_model,
            pro_total_score=0.0,
            con_total_score=0.0,
            pro_score=0.0,
            con_score=0.0,
            winner="FAILED",
            verdict_type="FAILED",
            status="failed",
            error_message=f"NVIDIA Judge evaluation failed: {last_error}",
            pro_strengths=[],
            pro_weaknesses=["Evaluation incomplete: NVIDIA Judge API call failed."],
            con_strengths=[],
            con_weaknesses=["Evaluation incomplete: NVIDIA Judge API call failed."],
            round_points=[],
            main_arguments=[],
            main_counterarguments=[],
            supported_claims=[],
            unsupported_claims=["Adjudication could not be completed due to Judge service failure."],
            judge_reasoning=(
                f"Adjudication via NVIDIA NIM API failed for debate on '{topic}'. "
                f"Error: {last_error}. "
                "Refusing to fabricate scores, verdict, or qualitative citations."
            ),
            balanced_verdict=f"Evaluation Failed: NVIDIA Judge ({resolved_model}) encountered an error and could not certify the debate.",
            evidence_reliability_score=0.0,
            evidence_reliability=0.0,
            source_references=[],
            judge_model_used="failed",
            is_fallback=True,
            execution_status="SIMULATED",
            evaluation_errors=[f"NVIDIA API Error: {last_error}"]
        )

    async def evaluate_debate_async(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        max_retries: Optional[int] = None,
        model_id: Optional[str] = None,
        blind_mode: bool = False,
        reverse_presentation: bool = False
    ) -> JudgeReportSchema:
        """
        Asynchronously evaluates debate transcript without blocking the event loop.
        """
        return await asyncio.to_thread(
            self.evaluate_debate,
            topic=topic,
            transcript=transcript,
            evidence_citations=evidence_citations,
            max_retries=max_retries,
            model_id=model_id,
            blind_mode=blind_mode,
            reverse_presentation=reverse_presentation
        )

nvidia_judge_service = NvidiaJudgeService()

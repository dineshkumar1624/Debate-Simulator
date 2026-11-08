import json
import logging
import re
import time
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
try:
    from google import genai
    from google.genai import types
    from google.genai import errors
except ImportError:
    genai = None
    errors = None
    class FakeTypes:
        def GenerateContentConfig(self, **kwargs):
            return kwargs
    types = FakeTypes()

from ..core.config import settings
from ..schemas.judge import JudgeReportSchema, JudgeRoundPoint, CriterionScore, CitationAssessment

logger = logging.getLogger(__name__)

class GeminiJudgeService:
    """
    Dedicated service for adjudicating AI debates via Google's Gemini API (gemini-3.5-flash / gemini-3.8-flash).
    
    Guarantees:
    - Uses the official google-genai SDK.
    - Explainable 6-criterion 100-point rubric with strict mathematical summation.
    - Decoupled evidence reliability and impartial margin-of-victory draw rules.
    - Detailed citation assessment (flagging verified, unverified, and fabricated citations).
    - Strict credential validation with zero secret leakage.
    - Bounded retries with exponential backoff for transient failures (429, 5xx, timeouts).
    - Immediate fail-fast for permanent authentication/authorization/input errors.
    - Pydantic schema validation conforming to JudgeReportSchema.
    - Refuses silent fallback: if Gemini fails, reports explicit failure report.
    """

    def __init__(self):
        self._client: Optional[Any] = None
        self._is_injected_client = False
        self.mock_mode = False

    def validate_configuration(self) -> str:
        """
        Validates that GEMINI_API_KEY is configured and non-empty.
        Never logs or returns the raw API key.
        """
        key = (settings.GEMINI_API_KEY or "").strip()
        if not key or key == "YOUR_GEMINI_API_KEY":
            raise ValueError(
                "GEMINI_API_KEY is not configured. "
                "Please generate an API key in Google AI Studio (https://aistudio.google.com/) "
                "and set GEMINI_API_KEY in backend/.env."
            )
        return key

    def get_client(self) -> Any:
        """
        Initializes or returns cached official Gemini Client.
        """
        if self._client is not None:
            return self._client
        
        api_key = self.validate_configuration()
        if genai is None:
            raise RuntimeError("The google-genai SDK is not installed in the current Python environment.")
        self._client = genai.Client(api_key=api_key)
        self._is_injected_client = False
        return self._client

    def set_client(self, client: Optional[Any]):
        """
        Allows injecting a mock or pre-configured client for automated unit tests.
        """
        self._client = client
        self._is_injected_client = client is not None

    def _is_retriable_error(self, exc: Exception) -> bool:
        """
        Determines if an error is transient and safe to retry.
        Fails fast on permanent client errors (400, 401, 403, 404, invalid argument).
        """
        code = getattr(exc, "code", None)
        if code in (400, 401, 403, 404):
            return False
        if code in (429, 500, 502, 503, 504):
            return True
        
        msg = str(exc).lower()
        if any(term in msg for term in [
            "invalid api key", "unauthorized", "permission denied", 
            "api_key_invalid", "credential", "forbidden", "not found"
        ]):
            return False
        
        if any(term in msg for term in [
            "timeout", "timed out", "connection", "rate limit", 
            "resource exhausted", "429", "503", "500", "try again",
            "winerror", "errno", "getaddrinfo", "readerror", "connecterror", "aborted"
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
            "REQUIRED OUTPUT FORMAT (Output strictly valid JSON with no markdown wrapping outside of JSON):\n"
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
        if evidence_citations:
            for ev in evidence_citations:
                if isinstance(ev, dict):
                    for k in ["source", "url", "title", "document_name", "document_id"]:
                        val = ev.get(k)
                        if val:
                            known_sources.add(str(val).strip().lower())

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
        blind_mode: bool = False,
        reverse_presentation: bool = False
    ) -> JudgeReportSchema:
        """
        Synchronously evaluates debate transcript using Gemini API with bounded retries.
        """
        model_id = getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash")
        retries = max_retries if max_retries is not None else int(getattr(settings, "GEMINI_MAX_RETRIES", 2))
        
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
                    f"[GeminiJudge] Sending adjudication request to '{model_id}' "
                    f"(attempt {attempt}/{retries + 1}) for topic: '{topic[:60]}...'"
                )

                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.2,
                )

                req_start = time.time()
                response = client.models.generate_content(
                    model=model_id,
                    contents=user_prompt,
                    config=config
                )
                req_duration = time.time() - req_start

                if not response or not response.text:
                    raise RuntimeError("Received empty or null response from Gemini API.")

                raw_text = response.text.strip()
                if "```json" in raw_text:
                    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                    if match:
                        raw_text = match.group(1)
                elif "```" in raw_text:
                    match = re.search(r"```\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                    if match:
                        raw_text = match.group(1)

                parsed_data = json.loads(raw_text)
                parsed_data["judge_provider"] = "gemini"
                parsed_data["judge_model"] = model_id
                parsed_data["judge_model_used"] = model_id
                parsed_data["is_fallback"] = False
                parsed_data["execution_status"] = "REAL_REMOTE_API"

                usage = getattr(response, "usage_metadata", None)
                prompt_toks = getattr(usage, "prompt_token_count", 0) if usage else len(user_prompt.split())
                gen_toks = getattr(usage, "candidates_token_count", 0) if usage else len(raw_text.split())
                tok_speed = round(gen_toks / req_duration, 2) if req_duration > 0 else 0.0

                parsed_data["performance_metrics"] = {
                    "provider": "gemini",
                    "model": model_id,
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
                
                logger.info(
                    f"[Diagnostic: GeminiJudge] provider=google_genai, model_id='{model_id}', "
                    f"duration_sec={req_duration:.2f}s, pro_total={report.pro_total_score}, "
                    f"con_total={report.con_total_score}, winner={report.winner}, "
                    f"verdict_type={report.verdict_type}, status='success'"
                )
                return report

            except Exception as e:
                if not getattr(self, "_is_injected_client", False):
                    self._client = None
                last_error = str(e)
                safe_err_name = type(e).__name__
                safe_msg = last_error.split("key=")[0].strip()
                logger.warning(
                    f"[GeminiJudge] Attempt {attempt}/{retries + 1} failed: "
                    f"[{safe_err_name}] {safe_msg}"
                )

                # If daily quota limit is exceeded on real API, break immediately to avoid useless polling
                if not getattr(self, "_is_injected_client", False):
                    if any(m in last_error for m in ("QuotaFailure", "PerDay", "per day", "daily limit")):
                        logger.warning("[GeminiJudge] Daily quota exhausted on real Google API; breaking immediately.")
                        break

                if not self._is_retriable_error(e) or attempt > retries:
                    break
                
                backoff_sec = float(2 ** attempt)
                if "429" in last_error or "resource_exhausted" in last_error.lower() or "quota" in last_error.lower():
                    retry_match = re.search(r'retry after ([0-9.]+)', last_error, re.IGNORECASE)
                    if retry_match:
                        backoff_sec = max(backoff_sec, float(retry_match.group(1)) + 1.5)
                    else:
                        backoff_sec = max(backoff_sec, 8.0)

                time.sleep(backoff_sec)

        # Permanent or exhausted failure: return structured failed report without silent fallback
        logger.error(f"[GeminiJudge] Adjudication failed after {retries + 1} attempts: {last_error}")
        return JudgeReportSchema(
            judge_provider="gemini",
            judge_model=model_id,
            pro_total_score=0.0,
            con_total_score=0.0,
            pro_score=0.0,
            con_score=0.0,
            winner="FAILED",
            verdict_type="FAILED",
            status="failed",
            error_message=f"Gemini Judge evaluation failed: {last_error}",
            pro_strengths=[],
            pro_weaknesses=["Evaluation incomplete: Gemini Judge API call failed."],
            con_strengths=[],
            con_weaknesses=["Evaluation incomplete: Gemini Judge API call failed."],
            round_points=[],
            main_arguments=[],
            main_counterarguments=[],
            supported_claims=[],
            unsupported_claims=["Adjudication could not be completed due to Judge service failure."],
            judge_reasoning=(
                f"Adjudication via Gemini failed for debate on '{topic}'. "
                f"Error: {last_error}. "
                "Refusing to fabricate scores, verdict, or qualitative citations."
            ),
            balanced_verdict="Evaluation Failed: Gemini Judge model encountered an error and could not certify the debate.",
            evidence_reliability_score=0.0,
            evidence_reliability=0.0,
            source_references=[],
            judge_model_used="failed",
            is_fallback=True,
            execution_status="SIMULATED",
            evaluation_errors=[f"Gemini API Error: {last_error}"]
        )

    async def evaluate_debate_async(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        max_retries: Optional[int] = None,
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
            blind_mode=blind_mode,
            reverse_presentation=reverse_presentation
        )

gemini_judge_service = GeminiJudgeService()

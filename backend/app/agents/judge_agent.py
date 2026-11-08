import json
import logging
import re
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
from ..schemas.judge import JudgeReportSchema, JudgeRoundPoint
from ..llm.model_manager import local_model_manager
from ..services.gemini_judge_service import gemini_judge_service
from ..services.nvidia_judge_service import nvidia_judge_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class JudgeAgent:
    def __init__(self):
        self.role = "JUDGE"

    def evaluate_debate(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 2,
        provider: Optional[str] = None,
        judge_model: Optional[str] = None,
        blind_mode: bool = False,
        reverse_presentation: bool = False
    ) -> JudgeReportSchema:
        """
        Adjudicates the completed debate using either Google Gemini API or NVIDIA NIM API as the Judge.
        Provider resolution priority:
        1. Explicit 'provider' parameter ('gemini' or 'nvidia').
        2. Inferred from 'judge_model' identifier.
        3. Configured default JUDGE_PROVIDER in settings.
        """
        # Determine provider
        resolved_provider = (provider or "").strip().lower()
        if not resolved_provider:
            if judge_model:
                jm_lower = judge_model.lower()
                if "nvidia" in jm_lower or "nemotron" in jm_lower:
                    resolved_provider = "nvidia"
                elif "gemini" in jm_lower:
                    resolved_provider = "gemini"
            if not resolved_provider:
                resolved_provider = getattr(settings, "JUDGE_PROVIDER", "nvidia").strip().lower()

        if resolved_provider not in ("gemini", "nvidia"):
            resolved_provider = "nvidia"

        is_mock_active = getattr(local_model_manager, "mock_mode", False) or getattr(gemini_judge_service, "mock_mode", False)
        if is_mock_active:
            target_service = nvidia_judge_service if resolved_provider == "nvidia" else gemini_judge_service
            client = getattr(target_service, "_client", None)
            is_mock_client = client is not None and (
                hasattr(client, "_mock_return_value") or
                hasattr(client, "mock") or
                "Mock" in type(client).__name__
            )
            if not is_mock_client:
                return self._evaluate_mock(
                    topic=topic,
                    transcript=transcript,
                    evidence_citations=evidence_citations,
                    max_retries=max_retries
                )

        if resolved_provider == "nvidia":
            logger.info(f"[JudgeAgent] Adjudicating via NVIDIA NIM provider (model: {judge_model or settings.NVIDIA_JUDGE_MODEL})")
            try:
                rep = nvidia_judge_service.evaluate_debate(
                    topic=topic,
                    transcript=transcript,
                    evidence_citations=evidence_citations,
                    max_retries=max_retries,
                    model_id=judge_model,
                    blind_mode=blind_mode,
                    reverse_presentation=reverse_presentation
                )
                if rep and getattr(rep, "status", "") != "failed" and getattr(rep, "winner", "") != "FAILED":
                    return rep
                logger.warning(
                    f"[JudgeAgent] NVIDIA NIM adjudication returned unsuccessful result (status={getattr(rep, 'status', None)}). "
                    "Falling back gracefully to Google Gemini provider..."
                )
            except Exception as e:
                logger.warning(
                    f"[JudgeAgent] NVIDIA NIM adjudication raised ({e}). Falling back gracefully to Google Gemini provider..."
                )

        logger.info(f"[JudgeAgent] Adjudicating via Google Gemini provider (model: {settings.GEMINI_MODEL_ID})")
        gemini_rep = None
        try:
            gemini_rep = gemini_judge_service.evaluate_debate(
                topic=topic,
                transcript=transcript,
                evidence_citations=evidence_citations,
                max_retries=max_retries,
                blind_mode=blind_mode,
                reverse_presentation=reverse_presentation
            )
            if gemini_rep and getattr(gemini_rep, "status", "") != "failed" and getattr(gemini_rep, "winner", "") != "FAILED":
                return gemini_rep
            logger.warning("[JudgeAgent] Gemini adjudication returned unsuccessful result. Attempting fallback to NVIDIA NIM...")
        except Exception as e:
            logger.warning(f"[JudgeAgent] Gemini adjudication raised ({e}). Attempting fallback to NVIDIA NIM...")

        if getattr(settings, "NVIDIA_API_KEY", ""):
            try:
                logger.info(f"[JudgeAgent] Falling back to NVIDIA NIM provider (model: {settings.NVIDIA_JUDGE_MODEL})")
                nim_rep = nvidia_judge_service.evaluate_debate(
                    topic=topic,
                    transcript=transcript,
                    evidence_citations=evidence_citations,
                    max_retries=max_retries,
                    blind_mode=blind_mode,
                    reverse_presentation=reverse_presentation
                )
                if nim_rep and getattr(nim_rep, "status", "") != "failed" and getattr(nim_rep, "winner", "") != "FAILED":
                    return nim_rep
            except Exception as e:
                logger.error(f"[JudgeAgent] NVIDIA NIM fallback also raised ({e})")

        return gemini_rep or JudgeReportSchema(
            pro_score=0.0,
            con_score=0.0,
            winner="FAILED",
            status="failed",
            pro_strengths=[],
            pro_weaknesses=[],
            con_strengths=[],
            con_weaknesses=[],
            round_points=[],
            judge_reasoning="Both primary and fallback adjudication providers were unable to complete evaluation.",
            balanced_verdict="Adjudication failed due to API connectivity/service errors.",
            evidence_reliability_score=0.0,
            source_references=[]
        )

    def _evaluate_mock(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 2
    ) -> JudgeReportSchema:
        """
        Offline dialectical simulation used when local_model_manager.mock_mode is True.
        """
        system_prompt = (
            "You are the independent AI Adjudicator and Chief Justice in a formal bilateral debate. "
            "Your solemn duty is to dispassionately evaluate the complete persisted transcript, relevant retrieved evidence, "
            "and source references according to strict dialectical standards. "
            "CRITICAL: Do NOT simply choose the longer or more confident response. Length and rhetorical confidence do not substitute "
            "for factual grounding, rebuttal depth, and dialectical consistency.\n\n"
            "EVALUATION CRITERIA:\n"
            "1. Argument Quality & Relevance: Direct address of the resolution and strength of core premises.\n"
            "2. Factual Grounding & Evidence Quality: Use of verified retrieved evidence vs ungrounded assertions.\n"
            "3. Logical Consistency: Structural soundness and freedom from fallacies.\n"
            "4. Strength of Rebuttals: Direct clash and counter-arguments versus evasion.\n"
            "5. Addressing Opposing Arguments: Did the speaker answer opposing claims or dodge them?\n"
            "6. Unsupported Claims, Contradictions, and Uncertainty: Identification of speculative or contradictory claims.\n"
            "7. Overall Persuasiveness and Balance: Even-handed synthesis without length bias.\n\n"
            "CRITICAL CITATION DISCIPLINE:\n"
            "- NEVER invent or fabricate citations, URLs, or external source titles.\n"
            "- Only cite sources that are present in the provided Retrieved Evidence Pool.\n"
            "- If evidence is insufficient or missing, you must explicitly state this limitation in unsupported_claims "
            "and judge_reasoning, and keep source_references as an empty list [].\n\n"
            "CRITICAL: You must return your evaluation strictly as a valid JSON object matching this schema:\n"
            "{\n"
            '  "pro_score": float (0-100),\n'
            '  "con_score": float (0-100),\n'
            '  "winner": "PRO" | "CON" | "INCONCLUSIVE",\n'
            '  "status": "completed",\n'
            '  "pro_strengths": [str],\n'
            '  "pro_weaknesses": [str],\n'
            '  "con_strengths": [str],\n'
            '  "con_weaknesses": [str],\n'
            '  "round_points": [{"round_number": int, "pro_summary": str, "con_summary": str, "key_takeaway": str}],\n'
            '  "main_arguments": [str],\n'
            '  "main_counterarguments": [str],\n'
            '  "supported_claims": [str],\n'
            '  "unsupported_claims": [str],\n'
            '  "judge_reasoning": str,\n'
            '  "balanced_verdict": str,\n'
            '  "evidence_reliability_score": float (0-100),\n'
            '  "source_references": [str]\n'
            "}\n"
            "Do NOT include conversational preambles or markdown backticks outside of valid JSON."
        )

        # 1. Assemble full formatted transcript
        transcript_lines = [f"Topic: {topic}\n=== AUTHORITATIVE TRANSCRIPT ==="]
        all_citations: List[Dict[str, Any]] = list(evidence_citations or [])
        for msg in transcript:
            speaker = msg.get("speaker", "UNKNOWN")
            role = msg.get("role", "")
            rnd = msg.get("round_number", 1)
            title = msg.get("title", "")
            content = msg.get("content", "")
            msg_ev = msg.get("evidence", []) or []
            all_citations.extend(msg_ev)

            ev_summary = []
            for ev in msg_ev:
                src = ev.get("source") or ev.get("url") or ev.get("title") or ev.get("document_id")
                ev_txt = (ev.get("excerpt") or ev.get("content") or ev.get("text") or ev.get("relevance_explanation") or ev.get("claim") or "").strip()
                if src:
                    ev_summary.append(f"[{src}] {ev_txt[:100]}...")
            ev_str = f"\n  Cited In Turn: {'; '.join(ev_summary)}" if ev_summary else ""
            transcript_lines.append(f"[Round {rnd}] {speaker} ({role}) - {title}:\n{content}{ev_str}\n")
        transcript_lines.append("=== END OF TRANSCRIPT ===")

        # 2. Assemble verified retrieved evidence pool
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
                meta_parts = [f"Source: {src}"]
                if ev_id:
                    meta_parts.append(f"Evidence ID: {ev_id}")
                if url:
                    meta_parts.append(f"URL: {url}")
                if page is not None:
                    meta_parts.append(f"Page: {page}")
                meta_line = " | ".join(meta_parts)
                raw_txt = ev.get("excerpt") or ev.get("content") or ev.get("text") or ev.get("claim") or ev.get("relevance_explanation") or ""
                transcript_lines.append(f"Evidence [{idx}] ({meta_line}):\n{raw_txt[:300]}\n")
        else:
            transcript_lines.append(
                "[NO RETRIEVED GROUNDING EVIDENCE AVAILABLE]\n"
                "Neither debater had access to verified grounding evidence for this debate. "
                "All factual claims are unverified assertions. "
                "You must reflect this in evidence_reliability_score (0.0 to 30.0), "
                "explicitly flag unsupported claims under unsupported_claims, "
                "state the evidence limitation in judge_reasoning, "
                "and set source_references to an empty list []. Do NOT invent citations or URLs."
            )
        transcript_lines.append("=== END OF EVIDENCE POOL ===")

        base_user_prompt = "\n".join(transcript_lines)
        last_error = None

        for attempt in range(1, max_retries + 1):
            if attempt == 1:
                user_prompt = base_user_prompt
            else:
                user_prompt = (
                    f"{base_user_prompt}\n\n"
                    f"CRITICAL FIX REQUIRED: Attempt {attempt - 1} failed validation: {last_error}.\n"
                    "Please regenerate the evaluation strictly conforming to the JSON schema. "
                    "Ensure valid JSON syntax, numerical scores 0-100, and no fabricated source references. "
                    "Output ONLY the JSON object."
                )

            try:
                raw_output = local_model_manager.generate(
                    role=self.role,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_new_tokens=1024,
                    temperature=0.2 if attempt == 1 else 0.1
                )

                report = self._parse_and_validate_output(
                    raw_output=raw_output,
                    topic=topic,
                    transcript=transcript,
                    evidence_citations=all_citations
                )
                if report.status == "completed":
                    return report
                last_error = report.error_message
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Judge evaluation attempt {attempt}/{max_retries} failed with error: {e}")

        # Structured failed report fallback after bounded retries
        logger.error(f"Judge evaluation failed after {max_retries} bounded retries: {last_error}")
        return JudgeReportSchema(
            pro_score=0.0,
            con_score=0.0,
            winner="FAILED",
            status="failed",
            error_message=f"Judge evaluation failed schema validation after {max_retries} retries: {last_error}",
            pro_strengths=[],
            pro_weaknesses=["Evaluation incomplete: Judge model output could not be parsed."],
            con_strengths=[],
            con_weaknesses=["Evaluation incomplete: Judge model output could not be parsed."],
            round_points=[],
            main_arguments=[],
            main_counterarguments=[],
            supported_claims=[],
            unsupported_claims=["Judge evaluation could not be certified due to malformed model output."],
            judge_reasoning=(
                f"Adjudication failed schema validation for debate on '{topic}'. "
                f"Error: {last_error}. Output did not conform to the 7-criterion JSON rubric. "
                "Refusing to fabricate scores, citations, or qualitative findings."
            ),
            balanced_verdict="Evaluation Inconclusive: Adjudicator output was malformed and could not be certified.",
            evidence_reliability_score=0.0,
            source_references=[]
        )

    def _parse_and_validate_output(
        self,
        raw_output: str,
        topic: str,
        transcript: List[Dict[str, Any]],
        evidence_citations: Optional[List[Dict[str, Any]]] = None
    ) -> JudgeReportSchema:
        """
        Extracts JSON block, cleans formatting, enforces citation discipline, and validates using Pydantic.
        If invalid, returns explicit status='failed', winner='FAILED'.
        """
        clean_text = raw_output.strip()
        # Strip potential markdown json tags
        if "```json" in clean_text:
            match = re.search(r"```json\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)
        elif "```" in clean_text:
            match = re.search(r"```\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)

        try:
            parsed_data = json.loads(clean_text)
            if not isinstance(parsed_data, dict):
                raise ValueError("Parsed JSON root must be an object dictionary.")

            # Citation discipline enforcement
            known_sources = set()
            if evidence_citations:
                for ev in evidence_citations:
                    if isinstance(ev, dict):
                        for key in ["source", "url", "title", "document_name", "document_id"]:
                            val = ev.get(key)
                            if val:
                                known_sources.add(str(val).strip())
            for msg in transcript:
                for ev in msg.get("evidence", []) or []:
                    if isinstance(ev, dict):
                        for key in ["source", "url", "title", "document_name", "document_id"]:
                            val = ev.get(key)
                            if val:
                                known_sources.add(str(val).strip())

            if not known_sources:
                # Evidence was absent
                parsed_data["source_references"] = []
                parsed_data["evidence_reliability_score"] = min(float(parsed_data.get("evidence_reliability_score", 0.0)), 50.0)
                if not any("grounding" in str(s).lower() or "unsupported" in str(s).lower() or "evidence" in str(s).lower() for s in parsed_data.get("unsupported_claims", [])):
                    parsed_data.setdefault("unsupported_claims", []).append("All empirical claims ungrounded due to lack of verified external grounding evidence.")
            else:
                # Filter out invented/hallucinated citations
                raw_refs = parsed_data.get("source_references", [])
                valid_refs = []
                for ref in raw_refs:
                    ref_str = str(ref).strip()
                    if any(ks.lower() in ref_str.lower() or ref_str.lower() in ks.lower() for ks in known_sources):
                        valid_refs.append(ref_str)
                parsed_data["source_references"] = valid_refs

            parsed_data["judge_model_used"] = "mock_adjudicator"
            parsed_data["is_fallback"] = True
            parsed_data["execution_status"] = "SIMULATED"
            parsed_data["performance_metrics"] = {
                "provider": "mock",
                "model": "mock_adjudicator",
                "evaluation_duration_sec": 0.15,
                "generated_tokens": 180,
                "input_tokens": 500,
                "tokens_per_second": 1200.0,
                "ttft_sec": 0.05
            }
            return JudgeReportSchema.model_validate(parsed_data)
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.warning(f"Judge output JSON validation error: {e}. Marking evaluation explicitly as failed.")
            return JudgeReportSchema(
                pro_score=0.0,
                con_score=0.0,
                winner="FAILED",
                status="failed",
                error_message=f"JSON schema validation failed: {e}",
                pro_strengths=[],
                pro_weaknesses=["Adjudication incomplete: Judge model output could not be parsed."],
                con_strengths=[],
                con_weaknesses=["Adjudication incomplete: Judge model output could not be parsed."],
                round_points=[],
                main_arguments=[],
                main_counterarguments=[],
                supported_claims=[],
                unsupported_claims=["Judge evaluation could not be certified due to malformed model output."],
                judge_reasoning=(
                    f"Adjudication failed schema validation for debate on '{topic}'. "
                    f"Error: {e}. Output did not conform to the 9-criterion JSON rubric. "
                    "Refusing to fabricate scores, citations, or qualitative findings."
                ),
                balanced_verdict=(
                    "Evaluation Inconclusive: Adjudicator output was malformed and could not be certified."
                ),
                evidence_reliability_score=0.0,
                source_references=[],
                judge_model_used="failed",
                is_fallback=True
            )

judge_agent = JudgeAgent()

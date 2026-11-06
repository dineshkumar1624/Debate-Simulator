import time
import logging
import re
from typing import Dict, Any, List, Optional, Callable
from ..llm.model_manager import local_model_manager
from ..core.config import settings
from ..services.response_validator import response_validator
from ..services.turn_parser import turn_parser
from ..services.context_manager import context_manager

logger = logging.getLogger(__name__)

class ConAgent:
    def __init__(self):
        self.role = "CON"

    def _clean_substantive_text(self, text: str) -> str:
        """
        Removes redundant Markdown header syntax (#, ##) and excess markdown bolding
        without truncating or removing any substantive claims, reasoning, evidence,
        citations, or qualifications.
        """
        if not text:
            return ""
        cleaned = re.sub(r'#+\s*', '', text)
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        return cleaned

    def generate_turn(
        self,
        topic: str,
        round_number: int,
        max_rounds: int,
        evidence_context: str,
        latest_pro_argument: Optional[str] = None,
        debate_history: Optional[List[Dict[str, Any]]] = None,
        max_new_tokens: Optional[int] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        permanent_context: Optional[str] = None,
        rolling_summary: Optional[Any] = None,
        debate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes CON agent turn using Qwen with analytical rigor and direct clash.
        Rebuts Gemma's actual latest argument:
        1. Identifies Gemma's central claim.
        2. Identifies the key assumption or inference supporting that claim.
        3. Determines which part of Gemma's argument is weakest or insufficiently supported.
        4. Explains why that weakness matters.
        5. Provides a substantive counterargument in own words.
        6. Uses relevant evidence when available.
        7. Addresses Gemma's actual reasoning rather than discussing the topic generally.
        8. Acknowledges valid parts before challenging limitations when appropriate.
        9. Avoids repeating earlier objections without new development.
        10. Finishes with a clear conclusion explaining why the rebuttal weakens PRO.
        """
        tokens_limit = max_new_tokens if max_new_tokens is not None else settings.CON_MAX_NEW_TOKENS

        # Workflow validation: CON cannot proceed without a preceding PRO argument
        clean_pro = self._clean_substantive_text(latest_pro_argument) if latest_pro_argument else ""
        if not clean_pro:
            err_msg = (
                f"Workflow Error: CON agent cannot generate rebuttal for Round {round_number} "
                "because no preceding PRO argument is available. Refusing to fabricate an ungrounded turn."
            )
            logger.error(f"[CON Agent] {err_msg}")
            raise RuntimeError(err_msg)

        clean_ev = self._clean_substantive_text(evidence_context) if evidence_context else ""
        is_image_grounded = "IMAGE EVIDENCE" in clean_ev or "Visual Item [img-ev-" in clean_ev

        if is_image_grounded:
            system_prompt = (
                "You are the CON (Opposition) debater powered by Qwen in a formal bilateral debate grounded on an uploaded image.\n"
                "Your critical task is to DIRECTLY REBUT the preceding affirmative argument presented by Gemma (PRO) using the visual evidence.\n\n"
                "INSTRUCTIONS:\n"
                "1. Scrutinize whether the uploaded image and data truly support Gemma's affirmative claim.\n"
                "2. Directly cite visual evidence items by ID (e.g. [img-ev-1], [img-ev-2]) without inventing page numbers.\n"
                "3. Ground your critique on observable visual facts; point out what the image fails to prove.\n"
                "4. Limit argument_text to 3-4 dense, substantive sentences so your rebuttal concludes cleanly with complete terminal punctuation.\n\n"
                "OUTPUT FORMAT: Return a valid JSON object matching:\n"
                "{\n"
                '  "argument_title": "Concise clash / counterargument title",\n'
                '  "argument_text": "Substantive 3-4 sentence rebuttal directly confronting Gemma using image evidence",\n'
                '  "central_claim": "Core counter-thesis challenging PRO",\n'
                '  "evidence_references": []\n'
                "}"
            )
        else:
            system_prompt = (
                "You are the CON (Opposition) debater powered by Qwen in a formal bilateral debate.\n"
                "Your critical task is to DIRECTLY REBUT the preceding argument presented by Gemma (PRO).\n\n"
                "INSTRUCTIONS:\n"
                "1. Target Gemma's specific claim, assumption, or methodological vulnerability.\n"
                "2. Provide a substantive counterargument in your own words, citing relevant document evidence (e.g. [p.1], [p.2]).\n"
                "3. Finish with a clear conclusion explaining why your counter-analysis weakens the PRO position.\n"
                "4. Limit argument_text to 3-4 dense, substantive sentences so your rebuttal concludes cleanly with complete terminal punctuation.\n\n"
                "OUTPUT FORMAT: Return a valid JSON object matching:\n"
                "{\n"
                '  "argument_title": "Concise clash / counterargument title",\n'
                '  "argument_text": "Substantive 3-4 sentence rebuttal directly confronting Gemma in your own words",\n'
                '  "central_claim": "Core counter-thesis challenging PRO",\n'
                '  "evidence_references": []\n'
                "}"
            )

        if permanent_context is not None or rolling_summary is not None:
            system_prompt, user_prompt = context_manager.assemble_con_prompt(
                topic=topic,
                round_number=round_number,
                max_rounds=max_rounds,
                permanent_context=permanent_context or "",
                rolling_summary=rolling_summary,
                latest_pro_argument=clean_pro,
                fresh_evidence_context=clean_ev,
                system_prompt=system_prompt
            )
        else:
            user_prompt_lines = [
                f"Topic: {topic}",
                f"Round: {round_number} of {max_rounds} (CON - Qwen)",
                "Mandate: DIRECT CLASH & REBUTTAL against Gemma's preceding PRO argument",
                "",
                "=== RETRIEVED VERIFIED EVIDENCE (FOR REASONING, DO NOT COPY VERBATIM) ===",
                clean_ev if clean_ev else "No external grounding documents retrieved. Rely on core deductive principles.",
                "",
                "=== OPPOSING GEMMA (PRO) ARGUMENT TO DIRECTLY REBUT ===",
                clean_pro,
                "",
                "INSTRUCTION: Target Gemma's specific claim and assumptions above. Do NOT speak generally about the topic."
            ]

            if debate_history and round_number > 1:
                history_snippets = []
                for item in debate_history[-2:]:
                    r_num = item.get("round_number", "")
                    r_role = item.get("role", "")
                    r_content = self._clean_substantive_text(item.get("content", ""))
                    first_sent = r_content.split('. ')[0] + '.' if '. ' in r_content else r_content[:140]
                    history_snippets.append(f"[R{r_num} {r_role}: {first_sent}]")
                if history_snippets:
                    user_prompt_lines.extend(["", "=== PRIOR ROUND CONTEXT ===", " ".join(history_snippets)])

            user_prompt = "\n".join(user_prompt_lines)

        req_start = time.time()
        gen_output = local_model_manager.generate(
            role=self.role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_new_tokens=tokens_limit,
            return_metadata=True,
            on_token=on_token,
            debate_id=debate_id,
            round_number=round_number
        )
        req_duration = time.time() - req_start

        ttft_val = None
        input_toks = 0
        cache_reused = 0
        tok_speed = None
        if isinstance(gen_output, dict):
            raw_content = gen_output.get("text", "").strip()
            gen_tokens = gen_output.get("generated_tokens")
            input_toks = gen_output.get("input_tokens", 0)
            ttft_val = gen_output.get("ttft_seconds")
            cache_reused = gen_output.get("cache_n", 0)
            tok_speed = gen_output.get("tokens_per_second")
            exec_status = gen_output.get("execution_status", "SIMULATED" if getattr(local_model_manager, "mock_mode", False) else "REAL_LOCAL_MODEL")
        else:
            raw_content = gen_output.strip()
            gen_tokens = None
            exec_status = "SIMULATED" if getattr(local_model_manager, "mock_mode", False) else "REAL_LOCAL_MODEL"

        # Parse into structured payload and enforce anti-copy-paste
        payload = turn_parser.parse_and_validate(
            role=self.role,
            raw_text=raw_content,
            retrieved_evidence=retrieved_evidence,
            topic=topic,
            round_number=round_number,
            max_rounds=max_rounds,
            latest_opponent_argument=latest_pro_argument
        )

        # Step 1: Initial Multi-Criteria Completion Validation on clean argument text
        val_result = response_validator.validate(
            text=payload.argument_text,
            role=self.role,
            max_tokens_configured=tokens_limit,
            actual_tokens_generated=gen_tokens
        )

        final_content = payload.argument_text

        # Step 2: Bounded Recovery (if incomplete or invalid)
        if not val_result.is_valid:
            logger.warning(
                f"[CON Agent] Output for Round {round_number} failed initial validation: "
                f"{val_result.errors} (finish_reason={val_result.finish_reason}). Initiating bounded recovery..."
            )
            recovered_text, val_result = response_validator.attempt_recovery(
                role=self.role,
                text=payload.argument_text,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                validation=val_result,
                model_manager=local_model_manager
            )
            recovered_payload = turn_parser.parse_and_validate(
                role=self.role,
                raw_text=recovered_text,
                retrieved_evidence=retrieved_evidence,
                topic=topic,
                round_number=round_number,
                max_rounds=max_rounds,
                latest_opponent_argument=latest_pro_argument
            )
            final_content = recovered_payload.argument_text
            payload.argument_text = final_content

        # Safe diagnostic logging (no keys or raw document dumps)
        provider = "local_llama_server" if local_model_manager.is_qwen_running() else "local_pytorch"
        logger.info(
            f"[Diagnostic: CON (Qwen)] provider={provider}, "
            f"model_path='{local_model_manager.get_model_path(self.role)}', "
            f"role=CON, round={round_number}/{max_rounds}, prompt_chars={len(user_prompt)}, "
            f"prompt_tokens={input_toks}, duration_sec={req_duration:.2f}s, ttft={ttft_val}s, "
            f"cache_reuse={cache_reused}, output_tokens={gen_tokens}, "
            f"is_valid={val_result.is_valid}, finish_reason={val_result.finish_reason}"
        )

        return {
            "speaker": "DEBATER_B",
            "role": "CON",
            "round_number": round_number,
            "title": payload.argument_title,
            "content": final_content, # Clean LLM argument, NOT raw JSON or raw chunk!
            "main_claim": payload.main_claim,
            "reasoning_summary": payload.reasoning_summary,
            "limitations": payload.limitations,
            "evidence_references": [r.model_dump() for r in payload.evidence_references],
            "confidence": 91.0,
            "is_valid": val_result.is_valid,
            "is_truncated": val_result.is_truncated,
            "finish_reason": val_result.finish_reason,
            "validation_errors": val_result.errors,
            "recovery_attempted": val_result.recovery_attempted,
            "recovery_successful": val_result.recovery_successful,
            "max_tokens_configured": tokens_limit,
            "execution_status": exec_status,
            "ttft_seconds": ttft_val,
            "prompt_tokens": input_toks,
            "cache_tokens": cache_reused,
            "tokens_per_second": tok_speed,
            "duration_seconds": round(req_duration, 2)
        }

con_agent = ConAgent()

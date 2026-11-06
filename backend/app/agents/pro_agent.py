import time
import logging
from typing import Dict, Any, List, Optional, Callable
from ..core.config import settings
from ..llm.model_manager import local_model_manager
from ..services.response_validator import response_validator
from ..services.turn_parser import turn_parser
from ..services.context_manager import context_manager

logger = logging.getLogger(__name__)

class ProAgent:
    def __init__(self):
        self.role = "PRO"

    def generate_turn(
        self,
        topic: str,
        round_number: int,
        max_rounds: int,
        evidence_context: str,
        latest_con_argument: Optional[str] = None,
        debate_history: Optional[List[Dict[str, Any]]] = None,
        max_new_tokens: Optional[int] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        permanent_context: Optional[str] = None,
        rolling_summary: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes PRO agent turn using Gemma with structured dialectical reasoning.
        Produces an original, substantive affirmative argument with real token streaming.
        """
        effective_tokens = max_new_tokens or getattr(settings, "PRO_MAX_NEW_TOKENS", 220)
        is_image_grounded = "IMAGE EVIDENCE" in evidence_context or "Visual Item [img-ev-" in evidence_context
        if is_image_grounded:
            system_prompt = (
                "You are the PRO (Affirmative) debater powered by Gemma in a formal bilateral dialectical debate.\n"
                "Build the affirmative case grounded strictly on the uploaded image.\n\n"
                "INSTRUCTIONS:\n"
                "1. State your affirmative thesis clearly based on the visual data.\n"
                "2. Directly cite visual evidence items by ID (e.g. [img-ev-1], [img-ev-2]) without inventing page numbers.\n"
                "3. In Round 2+, directly refute the opposing CON objections with new visual analysis.\n"
                "4. Limit argument_text to 3-4 dense, substantive sentences so your argument concludes cleanly with complete terminal punctuation.\n\n"
                "OUTPUT FORMAT: Return a valid JSON object matching:\n"
                "{\n"
                '  "argument_title": "Clear concise argument title",\n'
                '  "argument_text": "Substantive 3-4 sentence argument grounded on the image",\n'
                '  "central_claim": "Core proposition thesis",\n'
                '  "evidence_references": []\n'
                "}"
            )
        else:
            system_prompt = (
                "You are the PRO (Affirmative) debater powered by Gemma in a formal bilateral dialectical debate.\n"
                "Build the affirmative case for the proposition.\n\n"
                "INSTRUCTIONS:\n"
                "1. State your affirmative thesis and causal mechanisms clearly.\n"
                "2. Synthesize all points in your own words; directly cite evidence passages (e.g. [p.1], [p.2]).\n"
                "3. In Round 2+, directly confront and refute the opposing CON objections.\n"
                "4. Limit argument_text to 3-4 dense, substantive sentences so your argument concludes cleanly with complete terminal punctuation.\n\n"
                "OUTPUT FORMAT: Return a valid JSON object matching:\n"
                "{\n"
                '  "argument_title": "Clear concise argument title",\n'
                '  "argument_text": "Substantive 3-4 sentence affirmative argument in your own words",\n'
                '  "central_claim": "Core proposition thesis",\n'
                '  "evidence_references": []\n'
                "}"
            )

        if permanent_context is not None or rolling_summary is not None:
            system_prompt, user_prompt = context_manager.assemble_pro_prompt(
                topic=topic,
                round_number=round_number,
                max_rounds=max_rounds,
                permanent_context=permanent_context or "",
                rolling_summary=rolling_summary,
                latest_con_argument=latest_con_argument,
                fresh_evidence_context=evidence_context,
                system_prompt=system_prompt
            )
        else:
            user_prompt_lines = [
                f"Topic: {topic}",
                f"Round: {round_number} of {max_rounds}",
                f"Role: Affirmative (PRO - Gemma)",
                "Desired Position: AFFIRMATIVE (Support the proposition)",
                "",
                "=== RETRIEVED VERIFIED EVIDENCE (FOR REASONING, DO NOT COPY VERBATIM) ===",
                evidence_context.strip() if evidence_context and evidence_context.strip() else "No external grounding documents retrieved. Rely on core deductive principles.",
                ""
            ]

            if latest_con_argument:
                user_prompt_lines.append(
                    f"=== PREVIOUS CON OBJECTION TO REBUT & ADVANCE BEYOND ===\n"
                    f"{latest_con_argument.strip()}\n"
                    "Refute this specific objection directly, point out its flaw or limitation, and advance the affirmative case."
                )
            else:
                user_prompt_lines.append(
                    "This is Round 1. Establish your initial affirmative framework with clear claims, reasoning, assumptions, and practical consequences."
                )

            if debate_history and round_number > 1:
                history_snippets = []
                for item in debate_history[-2:]:
                    r_num = item.get("round_number", "")
                    r_role = item.get("role", "")
                    r_content = item.get("content", "").strip()
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
            max_new_tokens=effective_tokens,
            return_metadata=True,
            on_token=on_token
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
            latest_opponent_argument=latest_con_argument
        )

        # Step 1: Initial Validation on the clean argument text
        val_result = response_validator.validate(
            text=payload.argument_text,
            role=self.role,
            max_tokens_configured=effective_tokens,
            actual_tokens_generated=gen_tokens
        )

        final_content = payload.argument_text

        # Step 2: Bounded Recovery (if incomplete or invalid)
        if not val_result.is_valid:
            logger.warning(
                f"[PRO Agent] Output for Round {round_number} failed initial validation: "
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
                latest_opponent_argument=latest_con_argument
            )
            final_content = recovered_payload.argument_text
            payload.argument_text = final_content

        # Safe diagnostic logging (no keys or raw document dumps)
        provider = "local_llama_server" if local_model_manager.is_gemma_running() else "local_pytorch"
        logger.info(
            f"[Diagnostic: PRO (Gemma)] provider={provider}, "
            f"model_path='{local_model_manager.get_model_path(self.role)}', "
            f"role=PRO, round={round_number}/{max_rounds}, prompt_chars={len(user_prompt)}, "
            f"prompt_tokens={input_toks}, duration_sec={req_duration:.2f}s, ttft={ttft_val}s, "
            f"cache_reuse={cache_reused}, output_tokens={gen_tokens}, "
            f"is_valid={val_result.is_valid}, finish_reason={val_result.finish_reason}"
        )

        return {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": round_number,
            "title": payload.argument_title,
            "content": final_content, # Clean LLM argument, NOT raw JSON or raw chunk!
            "main_claim": payload.main_claim,
            "reasoning_summary": payload.reasoning_summary,
            "limitations": payload.limitations,
            "evidence_references": [r.model_dump() for r in payload.evidence_references],
            "confidence": 92.0,
            "is_valid": val_result.is_valid,
            "is_truncated": val_result.is_truncated,
            "finish_reason": val_result.finish_reason,
            "validation_errors": val_result.errors,
            "recovery_attempted": val_result.recovery_attempted,
            "recovery_successful": val_result.recovery_successful,
            "max_tokens_configured": max_new_tokens,
            "execution_status": exec_status,
            "ttft_seconds": ttft_val,
            "prompt_tokens": input_toks,
            "cache_tokens": cache_reused,
            "tokens_per_second": tok_speed,
            "duration_seconds": round(req_duration, 2)
        }

pro_agent = ProAgent()

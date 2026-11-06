import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

DANGLING_TAIL_WORDS = {
    "the", "a", "an", "to", "and", "or", "of", "in", "that", "with",
    "because", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "for", "by", "on", "at", "about", "into",
    "through", "during", "before", "after", "above", "below", "from",
    "up", "down", "out", "off", "over", "under", "which", "who", "whom",
    "whose", "if", "their", "its", "our", "your", "my", "his", "her",
    "such", "than", "so", "then"
}

VALID_TERMINAL_PUNCTUATION = ('.', '!', '?', '"', "'", ')', ']', '”', '’', '```')

PLACEHOLDER_CITATION_PATTERNS = [
    re.compile(r'\[[^\]]*\]\((?:year_of_study|year|date|source|link|url|insert[_\s]?[a-z]*)\b', re.IGNORECASE),
    re.compile(r'\[\s*(?:citation needed|source needed|insert citation|placeholder|author|source)\s*\]', re.IGNORECASE),
    re.compile(r'\[[^\]]+\]\(\s*\)'),
    re.compile(r'\[\s*\]\([^)]+\)'),
    re.compile(r'\(year_of_study\)', re.IGNORECASE),
    re.compile(r'\(insert[_\s]?[a-z]+\)', re.IGNORECASE),
]

@dataclass
class ValidationResult:
    is_valid: bool
    is_truncated: bool
    finish_reason: str # "stop", "length", "malformed", "placeholder", "empty"
    has_placeholder_citation: bool
    has_unfinished_sentence: bool
    missing_sections: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    cleaned_content: str = ""
    token_count: Optional[int] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False

class ResponseValidator:
    """
    Validates debater turns for genuine completion, structural integrity,
    and freedom from placeholder hallucinations or abrupt truncation.
    """

    @classmethod
    def validate(
        cls,
        text: str,
        role: str = "CON",
        max_tokens_configured: Optional[int] = None,
        actual_tokens_generated: Optional[int] = None
    ) -> ValidationResult:
        errors: List[str] = []
        missing_sections: List[str] = []
        has_placeholder = False
        has_unfinished = False
        is_truncated = False
        finish_reason = "stop"

        cleaned = text.strip() if text else ""
        if not cleaned:
            return ValidationResult(
                is_valid=False,
                is_truncated=False,
                finish_reason="empty",
                has_placeholder_citation=False,
                has_unfinished_sentence=False,
                errors=["Response content is empty."],
                cleaned_content=""
            )

        # 1. Token ceiling saturation check
        if max_tokens_configured is not None and actual_tokens_generated is not None:
            if actual_tokens_generated >= max_tokens_configured:
                finish_reason = "length"

        # 2. Terminal punctuation & dangling tail word check
        last_char = cleaned[-1]
        has_terminal_punct = last_char in VALID_TERMINAL_PUNCTUATION

        words = re.findall(r'[A-Za-z0-9_\'\-]+', cleaned)
        last_word = words[-1].lower() if words else ""

        if not has_terminal_punct:
            if last_word not in DANGLING_TAIL_WORDS and len(words) >= 20:
                # Complete grammatical sentence ending on substantive noun/verb; append period safely
                cleaned += "."
                has_terminal_punct = True
            else:
                has_unfinished = True
                is_truncated = True
                finish_reason = "length" if finish_reason == "length" else "malformed"
                errors.append(f"Output ends abruptly without terminal punctuation (ends with '{cleaned[-25:]}').")
        elif last_word in DANGLING_TAIL_WORDS:
            has_unfinished = True
            is_truncated = True
            finish_reason = "length" if finish_reason == "length" else "malformed"
            errors.append(f"Output ends on dangling grammatical connector '{last_word}'.")

        # 3. Empty citation placeholder checks
        for pat in PLACEHOLDER_CITATION_PATTERNS:
            match = pat.search(cleaned)
            if match:
                has_placeholder = True
                errors.append(f"Contains ungrounded citation placeholder: '{match.group(0)}'.")
                break

        # 4. Substantive content & word count threshold
        word_count = len(words)
        if word_count < 15:
            errors.append(f"Output too brief ({word_count} words < 15 words) to constitute a substantive debate argument.")

        # Check if text is only markdown headings without body text
        lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
        non_heading_lines = [l for l in lines if not re.match(r'^#{1,6}\s+', l)]
        if not non_heading_lines:
            errors.append("Output consists entirely of section headings with no substantive argument text.")
            missing_sections.append("Argument Body")

        # 5. Heading-to-content trailing check (heading followed by EOF)
        if lines and re.match(r'^#{1,6}\s+', lines[-1]):
            has_unfinished = True
            is_truncated = True
            errors.append(f"Output terminates on empty trailing section heading '{lines[-1]}'.")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            is_truncated=is_truncated,
            finish_reason=finish_reason if not is_valid else "stop",
            has_placeholder_citation=has_placeholder,
            has_unfinished_sentence=has_unfinished,
            missing_sections=missing_sections,
            errors=errors,
            cleaned_content=cleaned,
            token_count=actual_tokens_generated
        )

    @classmethod
    def sanitize_placeholders(cls, text: str) -> Tuple[str, bool]:
        """
        Safely sanitizes unresolved placeholder citations without altering
        substantive argument text (e.g. '[Schunk and Pajares](year_of_study)' -> 'Schunk and Pajares').
        """
        if not text:
            return text, False

        modified = False
        result = text

        # Replace [Author](year_of_study) or [Author](year) with Author
        def _replace_author_placeholder(m):
            nonlocal modified
            modified = True
            author = m.group(1).strip()
            return author

        pattern_author_meta = re.compile(
            r'\[([^\]]+)\]\((?:year_of_study|year|date|source|link|url|insert[_\s]?[a-z]*)\b[^\)]*\)',
            re.IGNORECASE
        )
        result, count1 = pattern_author_meta.subn(_replace_author_placeholder, result)
        if count1 > 0:
            modified = True

        # Strip [citation needed], [source needed], [placeholder]
        pattern_bracket_needed = re.compile(
            r'\[\s*(?:citation needed|source needed|insert citation|placeholder|author|source)\s*\]',
            re.IGNORECASE
        )
        result, count2 = pattern_bracket_needed.subn('', result)
        if count2 > 0:
            modified = True

        # Strip dangling (year_of_study)
        pattern_standalone = re.compile(r'\(\s*year_of_study\s*\)', re.IGNORECASE)
        result, count3 = pattern_standalone.subn('', result)
        if count3 > 0:
            modified = True

        # Clean up double spaces created by deletions
        result = re.sub(r' {2,}', ' ', result)

        return result.strip(), modified

    @classmethod
    def attempt_recovery(
        cls,
        role: str,
        text: str,
        system_prompt: str,
        user_prompt: str,
        validation: ValidationResult,
        model_manager: Any,
        max_continuation_tokens: int = 36
    ) -> Tuple[str, ValidationResult]:
        """
        Executes AT MOST ONE bounded recovery attempt when output is incomplete or malformed.
        Guarantees zero duplicate database messages or silent concatenation of unrelated text.
        """
        if validation.is_valid:
            return text, validation

        logger.info(f"[{role} Agent] Attempting bounded recovery for invalid output (reasons: {validation.errors})...")

        # Strategy 1: Sanitization for placeholder-only defects
        if validation.has_placeholder_citation and not validation.is_truncated and not validation.has_unfinished_sentence:
            sanitized, was_modified = cls.sanitize_placeholders(text)
            if was_modified:
                reval = cls.validate(sanitized, role=role)
                if reval.is_valid:
                    logger.info(f"[{role} Agent] Successfully recovered via placeholder sanitization.")
                    reval.recovery_attempted = True
                    reval.recovery_successful = True
                    return sanitized, reval

        # Strategy 2: Bounded continuation for trailing sentence truncation
        if validation.has_unfinished_sentence or validation.is_truncated:
            raw_text = text.strip()
            # Bounded continuation prompt targeting the specific trailing clause
            last_clause = raw_text[-120:] if len(raw_text) > 120 else raw_text
            cont_sys = (
                f"You are the {role} debater. Complete the unfinished thought and state a brief definitive concluding sentence. "
                "Do NOT repeat prior text. Conclude within 1-2 complete sentences."
            )
            cont_user = f"Unfinished statement:\n\"...{last_clause}\"\n\nConclude and finish the sentence now:"

            try:
                continuation = model_manager.generate(
                    role=role,
                    system_prompt=cont_sys,
                    user_prompt=cont_user,
                    max_new_tokens=max_continuation_tokens,
                    temperature=0.3
                ).strip()

                # Verify continuation is meaningful, non-empty, and doesn't parrot the prompt
                if continuation and len(continuation) > 5 and not continuation.lower().startswith("unfinished"):
                    # Strip any redundant repetition of the prompt prefix
                    if continuation.lower().startswith(last_clause.lower()[:30]):
                        continuation = continuation[len(last_clause[:30]):].strip()

                    combined = raw_text + (" " if not raw_text.endswith(" ") else "") + continuation
                    sanitized_combined, _ = cls.sanitize_placeholders(combined)
                    reval = cls.validate(sanitized_combined, role=role)
                    if reval.is_valid:
                        logger.info(f"[{role} Agent] Successfully recovered via bounded continuation (added {len(continuation)} chars).")
                        reval.recovery_attempted = True
                        reval.recovery_successful = True
                        return sanitized_combined, reval
                    else:
                        logger.warning(f"[{role} Agent] Continuation produced output that still failed validation: {reval.errors}")
            except Exception as e:
                logger.error(f"[{role} Agent] Recovery continuation error: {e}")

        # Strategy 3: Bounded concise regeneration (at most 1 attempt)
        try:
            logger.info(f"[{role} Agent] Attempting bounded concise regeneration (max 64 tokens)...")
            regen_sys = (
                f"You are the {role} debater. Deliver a strictly concise, complete rebuttal in 40-50 words. "
                "Ensure every sentence finishes with complete terminal punctuation."
            )
            regenerated = model_manager.generate(
                role=role,
                system_prompt=regen_sys,
                user_prompt=user_prompt,
                max_new_tokens=64,
                temperature=0.4
            ).strip()

            sanitized_regen, _ = cls.sanitize_placeholders(regenerated)
            reval_regen = cls.validate(sanitized_regen, role=role)
            if reval_regen.is_valid:
                logger.info(f"[{role} Agent] Successfully recovered via bounded concise regeneration.")
                reval_regen.recovery_attempted = True
                reval_regen.recovery_successful = True
                return sanitized_regen, reval_regen
        except Exception as e:
            logger.error(f"[{role} Agent] Recovery regeneration error: {e}")

        # Recovery failed: mark failed status honestly
        logger.warning(f"[{role} Agent] Bounded recovery was unsuccessful. Marking output as unresolved incomplete.")
        validation.recovery_attempted = True
        validation.recovery_successful = False
        return text, validation

response_validator = ResponseValidator()


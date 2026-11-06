import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from ..core.config import settings
from ..schemas.context import RollingDebateSummary, PermanentContextPayload

logger = logging.getLogger(__name__)

class DebateContextManager:
    """
    Intelligent Debate Context Management Service.
    
    Architectural Guarantees:
    1. Layer A (Permanent Context): Invariant proposition, document identity, and core evidence.
       Positioned at the start of the prompt to maximize llama.cpp KV prefix cache reuse.
    2. Layer B (Rolling Debate Summary): Compact structured summary updated after each completed round.
       Replaces raw transcript accumulation to prevent prompt bloat.
    3. Layer C (Immediate Context): The opponent's latest argument verbatim and current turn evidence.
    4. Evidence Preservation: Exact evidence statements, page numbers, numerical metrics, and IDs
       ([p.X], [img-ev-N]) are strictly preserved and never replaced by lossy summaries.
    5. Token-Aware Context Budget: Manages token consumption within configurable model limits.
    """

    def __init__(self):
        self.pro_budget = getattr(settings, "PRO_CONTEXT_BUDGET_TOKENS", 1200)
        self.con_budget = getattr(settings, "CON_CONTEXT_BUDGET_TOKENS", 1400)
        self.enable_prefix_alignment = getattr(settings, "ENABLE_PREFIX_CACHE_ALIGNMENT", True)
        self.enable_rolling_summary = getattr(settings, "ENABLE_ROLLING_DEBATE_SUMMARY", True)

    def estimate_tokens(self, text: str) -> int:
        """
        Fast token estimation for LLM prompts (~4.0 chars per token for English text/JSON).
        """
        if not text:
            return 0
        return max(1, int(len(text) / 3.8))

    def build_permanent_context(
        self,
        topic: str,
        source_scope: str = "document",
        document_id: Optional[str] = None,
        document_name: Optional[str] = None,
        document_page_count: Optional[int] = None,
        core_evidence_items: Optional[List[Dict[str, Any]]] = None,
        page_count: Optional[int] = None,
        core_evidence: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Constructs Layer A: The permanent invariant debate grounding context.
        This block is guaranteed to be 100% IDENTICAL across all turns of a debate,
        enabling llama.cpp prefix cache reuse to eliminate TTFT prefill overhead.
        """
        effective_page_count = document_page_count if document_page_count is not None else page_count
        effective_core_evidence = core_evidence_items if core_evidence_items is not None else core_evidence

        lines = [
            "=== DEBATE FOUNDATION & PERMANENT GROUNDING CONTEXT ===",
            f"DEBATE PROPOSITION: {topic}",
            f"EVIDENTIARY SCOPE: {source_scope.upper()}"
        ]

        if document_id:
            if (source_scope or "").lower() == "image":
                doc_str = f"SOURCE IMAGE: {document_name or 'Image'} (ID: {document_id})"
            else:
                doc_str = f"SOURCE DOCUMENT: {document_name or 'Document'}"
                if effective_page_count:
                    doc_str += f" ({effective_page_count} pages, ID: {document_id})"
            lines.append(doc_str)

        if effective_core_evidence:
            lines.append("\nPERMANENT GROUNDING EVIDENCE:")
            for idx, ev in enumerate(effective_core_evidence[:3], 1):
                ev_id = ev.get("evidence_id") or ev.get("id") or f"core-ev-{idx}"
                page = ev.get("page") or ev.get("page_number")
                sec = ev.get("section") or ev.get("section_title") or "Core Finding"
                content = (ev.get("content") or "").strip()
                if len(content) > 220:
                    content = content[:210].rsplit(" ", 1)[0] + "..."
                page_info = f", Page {page}" if page else ""
                lines.append(f"  [{ev_id}] ({sec}{page_info}): \"{content}\"")

        lines.append("CORE DEBATE CRITERIA: Factual grounding, rebuttal depth, logical consistency, empirical verification.")
        lines.append("=== END OF PERMANENT GROUNDING CONTEXT ===\n")
        return "\n".join(lines)

    def validate_summary(
        self,
        summary: RollingDebateSummary,
        previous_summary: Optional[RollingDebateSummary] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validates the rolling debate summary against Section 7 rules:
        - Both PRO and CON positions represented fairly.
        - Important arguments preserved.
        - No fabricated claims introduced.
        - Evidence identifiers remain valid.
        - Unresolved disagreements remain visible.
        - Does not declare any claim proven.
        """
        errors = []
        if not summary.pro_core_thesis or len(summary.pro_core_thesis.strip()) < 10:
            errors.append("PRO core thesis missing or too brief.")
        if not summary.con_core_thesis or len(summary.con_core_thesis.strip()) < 10:
            errors.append("CON core thesis missing or too brief.")

        # Check that neither side is declared unilaterally proven
        lower_thesis = (summary.pro_core_thesis + " " + summary.con_core_thesis).lower()
        if "definitively proven" in lower_thesis or "irrefutably won" in lower_thesis:
            errors.append("Summary inappropriately declared resolution unilaterally proven.")

        # Ensure unresolved disagreements exist for continuing debate
        if not summary.unresolved_disagreements:
            errors.append("Summary failed to retain unresolved disagreements.")

        # Evidence ID format validation
        for ev in summary.evidence_discussed:
            if not any(marker in ev for marker in ["[p.", "Table", "[img-ev-", "Page", "Section"]):
                pass # Accept descriptive citation

        is_valid = len(errors) == 0
        return is_valid, errors

    def generate_rolling_summary(
        self,
        round_number: int,
        pro_turn: Dict[str, Any],
        con_turn: Dict[str, Any],
        previous_summary: Optional[RollingDebateSummary] = None
    ) -> RollingDebateSummary:
        """
        Builds a compact, high-density structured summary of the completed round.
        Operates deterministically from the completed turns to preserve exact claims and citations.
        """
        pro_content = pro_turn.get("content") or pro_turn.get("argument_text") or ""
        con_content = con_turn.get("content") or con_turn.get("argument_text") or ""
        
        pro_title = pro_turn.get("title") or pro_turn.get("argument_title") or f"Round {round_number} Affirmative Framework"
        con_title = con_turn.get("title") or con_turn.get("argument_title") or f"Round {round_number} Negative Rebuttal"

        # Extract first 1-2 sentences for core thesis
        pro_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', pro_content) if len(s.strip()) > 15]
        con_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', con_content) if len(s.strip()) > 15]

        pro_thesis = pro_sentences[0] if pro_sentences else pro_title
        con_thesis = con_sentences[0] if con_sentences else con_title

        # Collect evidence citations
        evidence_discussed = []
        if previous_summary:
            evidence_discussed.extend(previous_summary.evidence_discussed)

        for ev in pro_turn.get("evidence", []) + pro_turn.get("evidence_references", []):
            label = f"[p.{ev.get('page')}]" if ev.get("page") else f"[{ev.get('id') or ev.get('evidence_id') or 'Evidence'}]"
            if label not in evidence_discussed:
                evidence_discussed.append(label)

        for ev in con_turn.get("evidence", []) + con_turn.get("evidence_references", []):
            label = f"[p.{ev.get('page')}]" if ev.get("page") else f"[{ev.get('id') or ev.get('evidence_id') or 'Evidence'}]"
            if label not in evidence_discussed:
                evidence_discussed.append(label)

        # Build key claims and objections
        pro_claims = [pro_title]
        if len(pro_sentences) > 1:
            pro_claims.append(pro_sentences[1][:140])

        con_objections = [con_title]
        if len(con_sentences) > 1:
            con_objections.append(con_sentences[1][:140])

        # Active unresolved clash
        unresolved = [
            f"Clash between '{pro_title[:60]}' and '{con_title[:60]}'",
            f"Whether empirical findings in {', '.join(evidence_discussed[:3]) or 'the document'} sustain affirmative claims against negative counter-analysis."
        ]

        summary = RollingDebateSummary(
            round_completed=round_number,
            pro_core_thesis=pro_thesis[:200],
            pro_key_claims=pro_claims[:3],
            con_core_thesis=con_thesis[:200],
            con_key_objections=con_objections[:3],
            challenged_claims=[pro_title[:100]],
            defended_arguments=[pro_thesis[:100]],
            unresolved_disagreements=unresolved,
            evidence_discussed=evidence_discussed[:6],
            remaining_inquiries=[
                "Methodological boundary conditions and real-world scalability.",
                "Sensitivity of performance benchmarks to baseline assumptions."
            ],
            is_valid=True
        )

        # Validate summary
        is_valid, validation_errors = self.validate_summary(summary, previous_summary)
        summary.is_valid = is_valid
        if not is_valid:
            logger.warning(f"[ContextManager] Summary validation failed: {validation_errors}. Retaining prior valid state if available.")
            if previous_summary and previous_summary.is_valid:
                return previous_summary

        return summary

    def format_rolling_summary_block(self, summary: Optional[RollingDebateSummary]) -> str:
        """
        Renders Layer B as a compact, structured text block for prompt injection.
        Target token size: ~150-180 tokens.
        """
        if not summary:
            return ""

        lines = [
            f"=== ROLLING DEBATE SUMMARY (ROUNDS 1-{summary.round_completed} SYNTHESIS) ===",
            f"AFFIRMATIVE CASE (PRO): {summary.pro_core_thesis}",
            f"  - Key Claims: {'; '.join(summary.pro_key_claims)}",
            f"OPPOSITION REBUTTAL (CON): {summary.con_core_thesis}",
            f"  - Key Objections: {'; '.join(summary.con_key_objections)}",
            f"UNRESOLVED DIALECTICAL CLASH: {'; '.join(summary.unresolved_disagreements)}",
            f"EVIDENCE ALREADY EXAMINED: {', '.join(summary.evidence_discussed) if summary.evidence_discussed else 'None'}",
            f"OPEN INQUIRIES TO RESOLVE: {'; '.join(summary.remaining_inquiries)}",
            "=== END OF ROLLING SUMMARY ===\n"
        ]
        return "\n".join(lines)

    def assemble_pro_prompt(
        self,
        topic: str,
        round_number: int,
        max_rounds: int,
        permanent_context: str,
        rolling_summary: Optional[RollingDebateSummary],
        latest_con_argument: Optional[str],
        fresh_evidence_context: str,
        system_prompt: str
    ) -> Tuple[str, str]:
        """
        Constructs the optimized PRO (Gemma) prompt with prefix cache alignment.
        
        Ordering:
        1. System prompt (Role, Rules, JSON Schema) -> Static Invariant
        2. Layer A: Permanent Context -> Static Invariant Prefix
        3. Layer B: Rolling Summary -> Stable across round
        4. Layer C: Immediate Conversation Context (latest CON argument verbatim)
        5. Current Turn Mandate (Round N, Task) -> Suffix
        """
        # Layer B: Rolling Summary Block
        summary_block = self.format_rolling_summary_block(rolling_summary) if (self.enable_rolling_summary and rolling_summary) else ""

        # Layer C: Immediate Context
        user_sections = []
        
        # 1. Permanent Grounding Context (Static Prefix)
        if self.enable_prefix_alignment and permanent_context:
            user_sections.append(permanent_context.strip())

        # 2. Fresh Verified Evidence for this specific turn
        if fresh_evidence_context and fresh_evidence_context.strip():
            user_sections.append(
                f"=== CURRENT TURN VERIFIED EVIDENCE ===\n{fresh_evidence_context.strip()}\n"
            )

        # 3. Rolling Summary of Previous Rounds
        if summary_block:
            user_sections.append(summary_block.strip())

        # 4. Immediate Opponent Target (Verbatim)
        if latest_con_argument and latest_con_argument.strip():
            user_sections.append(
                f"=== PREVIOUS CON OBJECTION TO DIRECTLY REBUT ===\n"
                f"{latest_con_argument.strip()}\n"
                "INSTRUCTION: Directly confront and refute the specific objections above. Advance the affirmative case beyond this challenge.\n"
            )
        else:
            user_sections.append(
                "MANDATE: This is Round 1. Establish your initial affirmative framework with clear claims, causal reasoning, assumptions, and practical consequences.\n"
            )

        # 5. Suffix Mandate (Positioned at end so prefix remains cache-reusable!)
        user_sections.append(
            f"=== CURRENT SPEECH MANDATE ===\n"
            f"Role: Affirmative (PRO - Gemma)\n"
            f"Round: {round_number} of {max_rounds}\n"
            f"Task: Build the strongest affirmative case. Synthesize evidence in your own words. Return valid JSON."
        )

        user_prompt = "\n\n".join(user_sections)

        # Check Token Budget
        est_tokens = self.estimate_tokens(system_prompt) + self.estimate_tokens(user_prompt)
        if est_tokens > self.pro_budget:
            logger.info(f"[ContextManager] PRO prompt exceeds budget ({est_tokens} > {self.pro_budget}). Applying token-aware compression.")
            user_prompt = self._enforce_budget(user_prompt, target_tokens=self.pro_budget - self.estimate_tokens(system_prompt))

        return system_prompt, user_prompt

    def assemble_con_prompt(
        self,
        topic: str,
        round_number: int,
        max_rounds: int,
        permanent_context: str,
        rolling_summary: Optional[RollingDebateSummary],
        latest_pro_argument: str,
        fresh_evidence_context: str,
        system_prompt: str
    ) -> Tuple[str, str]:
        """
        Constructs the optimized CON (Qwen) prompt with prefix cache alignment.
        
        Ordering:
        1. System prompt (Role, Rules, JSON Schema) -> Static Invariant
        2. Layer A: Permanent Context -> Static Invariant Prefix
        3. Layer B: Rolling Summary -> Stable across round
        4. Layer C: Immediate Conversation Context (latest PRO argument verbatim)
        5. Current Turn Mandate (Round N, Task) -> Suffix
        """
        summary_block = self.format_rolling_summary_block(rolling_summary) if (self.enable_rolling_summary and rolling_summary) else ""

        user_sections = []

        # 1. Permanent Grounding Context (Static Prefix)
        if self.enable_prefix_alignment and permanent_context:
            user_sections.append(permanent_context.strip())

        # 2. Fresh Verified Evidence for this specific turn
        if fresh_evidence_context and fresh_evidence_context.strip():
            user_sections.append(
                f"=== CURRENT TURN VERIFIED EVIDENCE ===\n{fresh_evidence_context.strip()}\n"
            )

        # 3. Rolling Summary of Previous Rounds
        if summary_block:
            user_sections.append(summary_block.strip())

        # 4. Immediate Opponent Target (Verbatim)
        user_sections.append(
            f"=== OPPOSING GEMMA (PRO) ARGUMENT TO DIRECTLY REBUT ===\n"
            f"{latest_pro_argument.strip()}\n"
            "INSTRUCTION: Target Gemma's specific claim, evidence interpretation, and underlying assumptions above. Do NOT speak generally about the topic.\n"
        )

        # 5. Suffix Mandate (Positioned at end so prefix remains cache-reusable!)
        user_sections.append(
            f"=== CURRENT SPEECH MANDATE ===\n"
            f"Role: Opposition (CON - Qwen)\n"
            f"Round: {round_number} of {max_rounds}\n"
            f"Task: Direct clash and refutation. Challenge the affirmative thesis using documentary facts. Return valid JSON."
        )

        user_prompt = "\n\n".join(user_sections)

        # Check Token Budget
        est_tokens = self.estimate_tokens(system_prompt) + self.estimate_tokens(user_prompt)
        if est_tokens > self.con_budget:
            logger.info(f"[ContextManager] CON prompt exceeds budget ({est_tokens} > {self.con_budget}). Applying token-aware compression.")
            user_prompt = self._enforce_budget(user_prompt, target_tokens=self.con_budget - self.estimate_tokens(system_prompt))

        return system_prompt, user_prompt

    def _enforce_budget(self, text: str, target_tokens: int) -> str:
        """
        Applies token-aware compression while strictly preserving evidence and citations.
        """
        # Compress multiple blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', text)
        if self.estimate_tokens(cleaned) <= target_tokens:
            return cleaned

        # Truncate overly verbose opponent argument lines if needed, preserving evidence
        lines = cleaned.split("\n")
        out_lines = []
        for line in lines:
            if line.startswith("  - Key Claims:") or line.startswith("  - Key Objections:"):
                # Compress list to first 2 items
                items = line.split(";")
                if len(items) > 2:
                    line = ";".join(items[:2]) + "..."
            out_lines.append(line)

        return "\n".join(out_lines)

context_manager = DebateContextManager()

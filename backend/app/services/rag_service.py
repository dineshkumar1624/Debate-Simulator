import logging
from typing import List, Dict, Any, Optional
from .embedding_service import embedding_service
from .qdrant_service import qdrant_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, top_k: int = settings.TOP_K_EVIDENCE):
        self.top_k = top_k

    def retrieve_evidence_for_turn(
        self,
        topic: str,
        opponent_argument: Optional[str] = None,
        speaker: str = "PRO",
        document_id: Optional[str] = None,
        source_scope: str = "document",
        round_number: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Retrieves, deduplicates, and formats evidence chunks for an agent's turn.
        
        Strict Scoping Rules:
        - When source_scope == 'document': restricts search strictly to the specified document_id
          and source_type='document'. Never silently queries the web.
        - When source_scope in ['general_topic', 'web']: queries only indexed web sources (source_type='web').
        - When source_scope == 'both': searches across both uploaded document and web sources.
        """
        clean_scope = (source_scope or "document").lower()

        # Strict document-only / image-only isolation check
        if clean_scope in ("document", "image"):
            if not document_id:
                logger.info(f"[RAG] {clean_scope}-grounded debate has no attached document_id. Refusing to search web; returning empty evidence.")
                return []
            target_doc_id = document_id
            # Allow searching both original chunks and structured document knowledge for this document
            target_source_type = None
        elif clean_scope in ("general_topic", "web"):
            target_doc_id = None
            target_source_type = "web"
        else:  # "both"
            target_doc_id = document_id
            target_source_type = None

        # Detect if document is an image
        is_image_doc = False
        doc_name = "Document"
        image_visual_ev = []
        if target_doc_id:
            try:
                from ..database.session import SessionLocal
                from ..models.document import DocumentModel
                with SessionLocal() as db:
                    doc_rec = db.query(DocumentModel).filter(DocumentModel.id == target_doc_id).first()
                    if doc_rec:
                        doc_name = doc_rec.name
                        meta = doc_rec.metadata_json or {}
                        ft = (doc_rec.file_type or "").lower()
                        if meta.get("source_type") == "image" or ft in ("png", "jpg", "jpeg", "webp", "bmp"):
                            is_image_doc = True
                            image_visual_ev = meta.get("visual_evidence") or []
            except Exception as e:
                logger.debug(f"[RAG] Document metadata check note: {e}")

        # 1. Role-tailored query formulation using current debate context
        speaker_upper = (speaker or "PRO").upper()
        if speaker_upper == "PRO":
            if opponent_argument and opponent_argument.strip():
                query = f"{topic}. Affirmative defense, empirical verification, and rejoinder addressing: {opponent_argument[:250]}"
            else:
                query = f"{topic}. Affirmative thesis framework, verified evidentiary findings, supporting empirical data"
        else:  # CON
            if opponent_argument and opponent_argument.strip():
                query = f"{topic}. Counter-examination, empirical blind spots, structural risks refuting affirmative argument: {opponent_argument[:250]}"
            else:
                query = f"{topic}. Critical limitations, methodological flaws, architectural bottlenecks, complexity bounds, trade-offs, empirical failure modes"

        # 2. Embedding using uniform 384-dimensional model
        query_vector = embedding_service.embed_text(query)
        if len(query_vector) != 384:
            logger.error(f"[RAG] Query vector dimension mismatch: {len(query_vector)} != 384. Aborting retrieval.")
            return []

        # 3. Scoped search in Qdrant with expanded candidate pool for web research diversity
        fetch_k = max(self.top_k * 3, 10) if target_source_type == "web" else self.top_k
        raw_hits = qdrant_service.search_evidence(
            query_vector=query_vector,
            document_id=target_doc_id,
            source_type=target_source_type,
            top_k=fetch_k
        )

        # 4. Deduplicate and apply source diversity across distinct URLs/sources
        seen_texts = set()
        deduped = []
        source_counts: Dict[str, int] = {}
        max_per_source = 2 if target_source_type == "web" else self.top_k

        # Primary pass: pick high-scoring chunks while guaranteeing source diversity
        for hit in raw_hits:
            content = hit.get("content", "").strip()
            if not content or content in seen_texts:
                continue
            src_key = hit.get("url") or hit.get("title") or "default"
            if source_counts.get(src_key, 0) < max_per_source:
                seen_texts.add(content)
                source_counts[src_key] = source_counts.get(src_key, 0) + 1
                deduped.append(hit)
                if len(deduped) >= self.top_k:
                    break

        # Secondary pass: if target top_k is not filled, add remaining valid hits
        if len(deduped) < self.top_k:
            for hit in raw_hits:
                content = hit.get("content", "").strip()
                if not content or content in seen_texts:
                    continue
                seen_texts.add(content)
                deduped.append(hit)
                if len(deduped) >= self.top_k:
                    break

        # Supplement with discrete image visual evidence items if this is an image document
        if is_image_doc and image_visual_ev:
            for ev_item in image_visual_ev:
                ev_content = f"[Visual Evidence: {ev_item.get('id')} ({ev_item.get('type')})]\n{ev_item.get('label')}: {ev_item.get('content')}"
                if ev_content not in seen_texts and len(deduped) < self.top_k + 2:
                    seen_texts.add(ev_content)
                    deduped.append({
                        "id": ev_item.get("id"),
                        "evidence_id": ev_item.get("id"),
                        "content": ev_content,
                        "section_title": f"Visual Evidence ({ev_item.get('id')})",
                        "page_number": None,
                        "title": doc_name,
                        "score": 0.95,
                        "is_image": True
                    })

        # 5. Format evidence references
        formatted_evidence = []
        for idx, hit in enumerate(deduped, 1):
            score = hit.get("score", 0.0)
            verdict = "supported" if score > 0.4 else "unverifiable"
            
            if is_image_doc:
                ev_id = hit.get("evidence_id") or hit.get("id") or f"img-ev-{idx}"
                sec_name = hit.get("section_title") or "Visual Analysis"
                source_label = f"Uploaded Image ({doc_name})"
                formatted_evidence.append({
                    "id": ev_id,
                    "evidence_id": ev_id,
                    "claim": f"Visual evidence finding from {sec_name}",
                    "source": source_label,
                    "page": None,
                    "section": sec_name,
                    "url": None,
                    "content": hit.get("content"),
                    "verdict": verdict,
                    "confidenceScore": round(min(max(score * 100, 50.0), 99.0), 1),
                    "is_image": True
                })
            else:
                ev_type = hit.get("evidence_type") or ("web_pdf" if hit.get("source_type") == "web" and hit.get("page_number", 0) > 0 else "document")
                content_type = (
                    "FULL_PDF_TEXT" if ev_type == "web_pdf"
                    else ("FULL_HTML_ARTICLE" if ev_type == "web_html"
                    else ("SEARCH_SNIPPET_ONLY" if ev_type == "search_snippet" else "DOCUMENT"))
                )
                pg = hit.get("page_number")
                pg_str = f" (Page {pg})" if (pg and pg > 0) else ""
                source_title = hit.get("title") or "Document"
                source_label = f"{source_title}{pg_str}" if (pg and pg > 0 and f"Page {pg}" not in source_title) else source_title
                sec_name = hit.get("section_title") or "Analysis"

                formatted_evidence.append({
                    "id": hit.get("id"),
                    "claim": f"Evidentiary finding from {sec_name}{pg_str}",
                    "source": source_label,
                    "page": pg,
                    "section": hit.get("section_title"),
                    "url": hit.get("url") or None,
                    "content": hit.get("content"),
                    "verdict": verdict,
                    "confidenceScore": round(min(max(score * 100, 50.0), 99.0), 1),
                    "is_image": False,
                    "contentType": content_type
                })

        return formatted_evidence

    def format_evidence_context(self, evidence_list: List[Dict[str, Any]]) -> str:
        """
        Constructs bounded context block for prompt injection.
        Explicitly instructs the LLM that excerpts are evidence for reasoning,
        NOT text to be copied verbatim.
        Handles both document and multimodal image evidence context.
        """
        if not evidence_list:
            return (
                "No verified documentary evidence retrieved for this turn. "
                "Ground reasoning on general logic and clearly acknowledge epistemic uncertainty where unverified."
            )

        has_image_evidence = any(ev.get("is_image") for ev in evidence_list)
        if has_image_evidence:
            lines = [
                "=== RETRIEVED VERIFIED IMAGE EVIDENCE ===",
                "GROUNDING MODE: UPLOADED IMAGE EVIDENCE",
                "INSTRUCTIONS FOR IMAGE-BASED DEBATE:",
                "1. Ground your arguments strictly on the visible features, numerical metrics, chart axes, and labels described below.",
                "2. Reference visual evidence by its ID (e.g. [img-ev-1], [img-ev-2]) and descriptive location. Do NOT invent page numbers.",
                "3. Do NOT extrapolate or hallucinate details not directly visible in the image.",
                "4. Explicitly acknowledge any stated epistemic uncertainties or limitations.\n"
            ]
            for idx, ev in enumerate(evidence_list, 1):
                ev_id = ev.get("evidence_id") or ev.get("id") or f"img-ev-{idx}"
                sec = ev.get("section") or "Visual Evidence"
                src = ev.get("source") or "Uploaded Image"
                raw_content = (ev.get("content") or "").strip()
                if len(raw_content) > 300:
                    snippet = raw_content[:290].rsplit(" ", 1)[0] + "..."
                else:
                    snippet = raw_content
                lines.append(f"[{idx}] Visual Item [{ev_id}] ({sec}) — Source: {src}\nObserved Evidence: \"{snippet}\"\n")
            lines.append("=== END OF IMAGE EVIDENCE ===")
            return "\n".join(lines)

        lines = [
            "=== RETRIEVED VERIFIED EVIDENCE ===",
            "INSTRUCTION: Synthesize your argument in your own words. Use these excerpts as evidence to reason about; do NOT copy sentences or paragraphs verbatim.\n"
        ]
        for idx, ev in enumerate(evidence_list, 1):
            source_info = f"Source: {ev.get('source')}"
            if ev.get("page"):
                source_info += f", Page {ev.get('page')}"
            if ev.get("section") and ev.get("section") != ev.get("source"):
                source_info += f", Section: {ev.get('section')}"
            if ev.get("url"):
                source_info += f", URL: {ev.get('url')}"
            if ev.get("contentType"):
                source_info += f" [{ev.get('contentType')}]"
            raw_content = (ev.get("content") or "").strip()
            if len(raw_content) > 280:
                snippet = raw_content[:270].rsplit(" ", 1)[0] + "..."
            else:
                snippet = raw_content
            lines.append(f"[{idx}] {source_info}\nVerified Passage Excerpt: \"{snippet}\"\n")
        lines.append("=== END OF EVIDENCE ===")
        return "\n".join(lines)

rag_service = RAGService()

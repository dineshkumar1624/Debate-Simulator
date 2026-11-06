import os
import re
import io
import uuid
import logging
import unicodedata
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.document import DocumentModel, DocumentChunkModel
from ..core.config import settings
from .embedding_service import embedding_service
from .qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024  # 25 MB

class DocumentProcessingService:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # 1. Normalization
    def normalize_text(self, text: str) -> str:
        """
        Cleans control characters, excessive whitespace, and standardizes punctuation.
        """
        if not text:
            return ""
        # Unicode normalization (NFKD)
        text = unicodedata.normalize("NFKD", text)
        # Strip null bytes and non-printable control characters (preserve newlines and tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Replace non-breaking spaces and standardize line endings
        text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
        # Collapse multiple horizontal whitespaces
        text = re.sub(r"[ \t]+", " ", text)
        # Collapse multiple empty lines
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    # 2. Shared Chunking
    def chunk_text(
        self,
        text: str,
        page_number: int = 1,
        section_title: str = "General"
    ) -> List[Dict[str, Any]]:
        """
        Splits text into overlapping bounded chunks while preserving page & section references.
        """
        normalized = self.normalize_text(text)
        if not normalized:
            return []

        words = normalized.split()
        if len(words) <= self.chunk_size:
            return [{
                "chunk_id": str(uuid.uuid4()),
                "content": normalized,
                "page_number": page_number,
                "section_title": section_title,
                "word_count": len(words)
            }]

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_content = " ".join(words[start:end])
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "content": chunk_content,
                "page_number": page_number,
                "section_title": section_title,
                "word_count": end - start
            })
            if end == len(words):
                break
            start += max(1, self.chunk_size - self.chunk_overlap)

        return chunks

    # 3. PDF Extraction
    def extract_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from PDF page by page.
        Supports multi-page documents, detects scanned, vector-outlined, or rasterized pages,
        and applies high-performance RapidOCR / pypdfium2 extraction where text is sparse.
        """
        pages_content = []
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)
            if num_pages == 0:
                raise ValueError("PDF document contains 0 pages.")

            logger.info(f"[Stage C: PDF Text Extraction] Extracting {num_pages} pages from {os.path.basename(file_path)}")

            # First pass: inspect native text extraction
            native_texts = []
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                native_texts.append(txt.strip())

            total_native_chars = sum(len(t) for t in native_texts)
            logger.info(f"[Stage C] Native PDF extraction yielded {total_native_chars} chars across {num_pages} pages")

            for idx in range(num_pages):
                page_num = idx + 1
                text = native_texts[idx]

                # Scanned, vector-outlined, or image-dominated page detection (< 40 characters)
                if len(text) < 40:
                    logger.info(f"[Stage C: Page {page_num}] Sparse text ({len(text)} chars). Triggering high-accuracy OCR hook...")
                    ocr_text = self._ocr_pdf_page(file_path, idx)
                    if ocr_text:
                        text = (text + "\n" + ocr_text).strip() if text else ocr_text

                pages_content.append({
                    "page_number": page_num,
                    "section_title": f"Page {page_num}",
                    "text": text
                })
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.error(f"Error reading PDF {file_path}: {e}")
            raise ValueError(f"Corrupted or invalid PDF document: {e}")

        total_text = "".join(p["text"].strip() for p in pages_content)
        if not total_text:
            raise ValueError("PDF document contains no extractable text or readable images.")

        logger.info(f"[Stage D: Page Count Verification] Successfully extracted {len(total_text)} total chars across {len(pages_content)}/{num_pages} verified pages")
        return pages_content

    def _ocr_pdf_page(self, file_path: str, page_index: int) -> str:
        """
        High-performance OCR hook for scanned or vector-outlined PDF pages using RapidOCR and pypdfium2.
        Reuses a single RapidOCR engine instance across pages for optimal speed and zero orphan processes.
        """
        # 1. Primary: RapidOCR via pypdfium2
        try:
            import pypdfium2 as pdfium
            import numpy as np

            if not hasattr(self, "_ocr_engine") or self._ocr_engine is None:
                from rapidocr_onnxruntime import RapidOCR
                self._ocr_engine = RapidOCR()

            doc = pdfium.PdfDocument(file_path)
            if page_index < len(doc):
                page = doc[page_index]
                image = page.render(scale=1.2).to_pil()
                result, _ = self._ocr_engine(np.array(image))
                if result:
                    lines = [item[1] for item in result if item and len(item) > 1 and item[1]]
                    ocr_text = "\n".join(lines).strip()
                    if ocr_text:
                        logger.info(f"[RapidOCR] Page {page_index+1}: Extracted {len(ocr_text)} chars")
                        return ocr_text
        except Exception as ocr_err:
            logger.warning(f"RapidOCR on page {page_index+1} failed: {ocr_err}")

        # 2. Secondary fallback: pytesseract if available
        try:
            import pytesseract
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(file_path)
            if page_index < len(doc):
                image = doc[page_index].render(scale=1.2).to_pil()
                ocr_text = pytesseract.image_to_string(image).strip()
                if ocr_text:
                    logger.info(f"[PyTesseract] Page {page_index+1}: Extracted {len(ocr_text)} chars")
                    return ocr_text
        except Exception:
            pass

        return ""

    # 4. Image Extraction & Structural Analysis
    def extract_from_image(self, file_path: str) -> str:
        """
        Conducts image analysis (dimensions, resolution, format, color mode) and extracts text using RapidOCR.
        When Qwen multimodal vision is enabled, generates rich visual descriptions of charts, diagrams, and figures.
        Does not fabricate unreadable content.
        """
        try:
            from PIL import Image
            img = Image.open(file_path)
            img.verify()
            # Reopen after verify() (Pillow requirement)
            img = Image.open(file_path)

            w, h = img.size
            fmt = img.format or "IMAGE"
            mode = img.mode
            mp = (w * h) / 1_000_000.0

            # 1. Attempt optical character recognition via RapidOCR, then pytesseract
            ocr_text = ""
            try:
                import numpy as np
                if not hasattr(self, "_ocr_engine") or self._ocr_engine is None:
                    from rapidocr_onnxruntime import RapidOCR
                    self._ocr_engine = RapidOCR()
                result, _ = self._ocr_engine(np.array(img))
                if result:
                    lines = [item[1] for item in result if item and len(item) > 1 and item[1]]
                    ocr_text = "\n".join(lines).strip()
            except Exception as e:
                logger.debug(f"RapidOCR image fallback note: {e}")

            if not ocr_text:
                try:
                    import pytesseract
                    ocr_text = pytesseract.image_to_string(img).strip()
                except Exception:
                    pass

            # 2. Multimodal Visual Understanding via Qwen Vision Projector (when available and not in mock mode)
            vision_desc = ""
            try:
                from ..llm.model_manager import local_model_manager
                mmproj_path = getattr(settings, "QWEN_MMPROJ_PATH", "")
                if os.path.exists(mmproj_path) and not getattr(local_model_manager, "mock_mode", False):
                    logger.info(f"Triggering Qwen multimodal visual analysis for image: {os.path.basename(file_path)}")
                    vision_desc = local_model_manager.describe_image(file_path)
            except Exception as v_err:
                logger.info(f"Qwen multimodal image analysis skipped or unavailable: {v_err}")

            parts = [f"[Visual Image: {fmt} {w}x{h} ({mp:.2f} Megapixels, mode {mode})]"]
            if vision_desc:
                parts.append(f"Multimodal Visual Comprehension:\n{vision_desc}")
            if ocr_text:
                parts.append(f"Optical Text (OCR):\n{ocr_text}")
            elif not vision_desc:
                parts.append("[No optical text detected via OCR]")

            return "\n\n".join(parts)
        except Exception as e:
            logger.warning(f"Image analysis error on {file_path}: {e}")
            raise ValueError(f"Invalid or corrupted image file: {e}")

    # 5. DOCX Extraction
    def extract_from_docx(self, file_path: str) -> str:
        """
        Extracts paragraphs from DOCX files using standard zipfile XML parsing.
        """
        import zipfile
        import xml.etree.ElementTree as ET
        try:
            with zipfile.ZipFile(file_path) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                paragraphs = []
                for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                    texts = [node.text for node in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
                extracted = "\n\n".join(paragraphs).strip()
                if not extracted:
                    raise ValueError("DOCX document contains no readable paragraph text.")
                return extracted
        except zipfile.BadZipFile as bz:
            raise ValueError(f"Corrupted or invalid DOCX archive: {bz}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.warning(f"DOCX extraction fallback: {e}")
            raise ValueError(f"Failed to parse DOCX document: {e}")

    # 6. Text / Markdown Extraction
    def extract_from_text(self, file_path: str) -> str:
        """
        Extracts plain text with encoding fallback and whitespace validation.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                raise ValueError(f"Unable to decode text document: {e}")

        cleaned = content.strip()
        if not cleaned:
            raise ValueError("Uploaded text file is empty (0 readable characters).")
        return cleaned

    # 7. Direct Raw Text Ingestion
    def ingest_raw_text(
        self,
        db: Session,
        content: str,
        title: str = "Direct Text Input"
    ) -> DocumentModel:
        """
        Direct text ingestion pipeline:
        Raw Text -> Normalization -> Chunking -> Embeddings -> Qdrant -> SQL
        """
        normalized = self.normalize_text(content)
        if not normalized:
            raise ValueError("Text content cannot be empty.")

        doc_id = str(uuid.uuid4())
        content_bytes = len(content.encode("utf-8"))
        size_str = f"{content_bytes / 1024:.1f} KB" if content_bytes > 1024 else f"{content_bytes} B"

        chunks = self.chunk_text(
            text=normalized,
            page_number=1,
            section_title="Direct Input"
        )
        if not chunks:
            raise ValueError("Unable to generate text chunks from the provided content.")

        # Embeddings
        chunk_texts = [c["content"] for c in chunks]
        vectors = embedding_service.embed_documents(chunk_texts)

        # Qdrant Indexing
        payload_chunks = []
        for c in chunks:
            payload_chunks.append({
                "chunk_id": c["chunk_id"],
                "document_id": doc_id,
                "page_number": c["page_number"],
                "section_title": c["section_title"],
                "content": c["content"],
                "title": title,
                "source_type": "document"
            })

        indexing_success = qdrant_service.upsert_chunks(payload_chunks, vectors)
        if not indexing_success:
            logger.error(f"Vector indexing failed for direct text document {doc_id}")
            raise RuntimeError(f"Vector indexing failed for direct text input '{title}'")

        summary = (
            chunks[0]["content"][:280] + "..."
            if len(chunks[0]["content"]) > 280
            else chunks[0]["content"]
        )

        sections_meta = [{
            "id": "sec-1",
            "title": "Direct Input",
            "pageNumber": 1,
            "wordCount": sum(c["word_count"] for c in chunks),
            "claimsCount": max(1, len(chunks)),
            "summary": summary
        }]

        doc_record = DocumentModel(
            id=doc_id,
            name=title,
            file_type="txt",
            file_size=size_str,
            file_size_bytes=content_bytes,
            page_count=1,
            status="ready",
            summary=summary,
            key_claims_count=len(chunks),
            evidence_points_count=len(chunks) * 2,
            debates_count=0,
            metadata_json={
                "file_path": file_path,
                "sections": sections_meta,
                "suggestedQuestions": [
                    f"Does this text provide sufficient empirical evidence to substantiate its claims?",
                    f"What potential limitations or counterarguments apply to '{title}'?",
                    f"How do statutory or constitutional principles apply to this premise?"
                ]
            }
        )
        try:
            db.add(doc_record)
            for idx, c in enumerate(chunks):
                chunk_record = DocumentChunkModel(
                    id=c["chunk_id"],
                    document_id=doc_id,
                    chunk_index=idx,
                    page_number=c["page_number"],
                    section_title=c["section_title"],
                    content=c["content"]
                )
                db.add(chunk_record)

            db.commit()
            db.refresh(doc_record)

            # Whole-document understanding: build hierarchical summaries, concepts, facts & relations
            try:
                from .document_knowledge_service import document_knowledge_service
                document_knowledge_service.build_and_index_knowledge(doc_id, db)
                db.refresh(doc_record)
            except Exception as ke:
                logger.warning(f"Whole-document knowledge extraction encountered non-fatal warning: {ke}")

            return doc_record
        except Exception as e:
            logger.error(f"SQL persistence failed for direct text document {doc_id}. Executing compensating Qdrant deletion: {e}")
            try:
                qdrant_service.delete_document(doc_id)
            except Exception as qe:
                logger.warning(f"Compensating Qdrant deletion encountered error for {doc_id}: {qe}")
            db.rollback()
            raise

    # 8. Full Ingestion & Indexing Pipeline for Uploaded Files
    def ingest_document(
        self,
        db: Session,
        file_path: str,
        original_filename: str,
        file_type: str = "pdf"
    ) -> DocumentModel:
        """
        Full file ingestion pipeline:
        Validation -> Text Extraction -> Normalization -> Chunking -> Embeddings -> Qdrant -> SQL
        """
        if not os.path.exists(file_path):
            raise ValueError(f"Uploaded file does not exist on disk: {file_path}")

        file_size_bytes = os.path.getsize(file_path)
        if file_size_bytes == 0:
            raise ValueError(f"Uploaded file '{original_filename}' is empty (0 bytes).")
        if file_size_bytes > MAX_DOCUMENT_BYTES:
            raise ValueError(f"File '{original_filename}' exceeds the maximum allowed size of 25 MB.")

        file_size_mb = f"{file_size_bytes / (1024 * 1024):.1f} MB" if file_size_bytes > 1024 * 1024 else f"{file_size_bytes / 1024:.1f} KB"
        doc_id = str(uuid.uuid4())
        clean_ext = file_type.lower().lstrip(".")

        # Step 0: Image Ingestion Delegation to Dedicated Multimodal Image Service
        if clean_ext in ["png", "jpg", "jpeg", "webp", "bmp"]:
            logger.info(f"[Stage A & B] Delegating image '{original_filename}' to multimodal image service")
            from .image_service import image_service
            return image_service.ingest_image(
                db=db,
                file_path=file_path,
                original_filename=original_filename,
                file_type=clean_ext
            )

        # Step 1: Extraction by format
        logger.info(f"[Stage A & B: Reception & Storage] Validated '{original_filename}' ({file_size_mb}) at {file_path}")
        extracted_pages = []
        if clean_ext == "pdf":
            extracted_pages = self.extract_from_pdf(file_path)
        elif clean_ext == "docx":
            text = self.extract_from_docx(file_path)
            extracted_pages = [{"page_number": 1, "section_title": "Document Body", "text": text}]
        elif clean_ext in ["png", "jpg", "jpeg", "webp", "bmp"]:
            text = self.extract_from_image(file_path)
            extracted_pages = [{"page_number": 1, "section_title": "Visual Analysis", "text": text}]
        else: # txt, md, etc.
            text = self.extract_from_text(file_path)
            extracted_pages = [{"page_number": 1, "section_title": "Document Body", "text": text}]

        page_count = max(len(extracted_pages), 1)
        logger.info(f"[Stage D: Page Count Verification] {page_count} pages verified for '{original_filename}'")

        # Step 2: Chunking & Section outline
        all_chunks = []
        sections_meta = []
        for p in extracted_pages:
            p_chunks = self.chunk_text(
                text=p["text"],
                page_number=p["page_number"],
                section_title=p["section_title"]
            )
            all_chunks.extend(p_chunks)
            if p_chunks:
                sections_meta.append({
                    "id": f"sec-{p['page_number']}",
                    "title": p["section_title"],
                    "pageNumber": p["page_number"],
                    "wordCount": sum(c["word_count"] for c in p_chunks),
                    "claimsCount": max(1, len(p_chunks)),
                    "summary": p_chunks[0]["content"][:150] + "..."
                })

        if not all_chunks:
            raise ValueError(f"Document '{original_filename}' yielded no usable text chunks.")

        # Step 3: Embeddings
        logger.info(f"[Stage F: Embedding Generation] Generating embeddings for {len(all_chunks)} chunks...")
        chunk_texts = [c["content"] for c in all_chunks]
        vectors = embedding_service.embed_documents(chunk_texts)

        # Step 4: Qdrant Indexing
        logger.info(f"[Stage G: Qdrant Indexing] Upserting {len(all_chunks)} points into Qdrant collection...")
        payload_chunks = []
        for idx, c in enumerate(all_chunks):
            payload_chunks.append({
                "chunk_id": c["chunk_id"],
                "document_id": doc_id,
                "page_number": c["page_number"],
                "section_title": c["section_title"],
                "content": c["content"],
                "title": original_filename,
                "source_type": "document"
            })

        indexing_success = qdrant_service.upsert_chunks(payload_chunks, vectors)
        if not indexing_success:
            logger.error(f"Vector indexing failed for document {doc_id}")
            raise RuntimeError(f"Vector indexing failed for document '{original_filename}'")

        # Step 5: SQL Record Creation
        logger.info(f"[Stage E: SQLite Document Creation] Committing document {doc_id} with {len(all_chunks)} chunks...")
        summary = (
            all_chunks[0]["content"][:280] + "..."
            if len(all_chunks[0]["content"]) > 280
            else all_chunks[0]["content"]
        )

        doc_record = DocumentModel(
            id=doc_id,
            name=original_filename,
            file_type=clean_ext,
            file_size=file_size_mb,
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            status="ready",
            summary=summary,
            key_claims_count=len(all_chunks),
            evidence_points_count=len(all_chunks) * 2,
            debates_count=0,
            metadata_json={
                "file_path": file_path,
                "sections": sections_meta,
                "suggestedQuestions": [
                    f"Does {original_filename} provide sufficient empirical evidence to substantiate its primary assertions?",
                    f"What are the principal methodology limitations identified in {original_filename}?",
                    f"How do statutory or ethical bounds constrain the conclusions of {original_filename}?"
                ]
            }
        )
        try:
            db.add(doc_record)
            for idx, c in enumerate(all_chunks):
                chunk_record = DocumentChunkModel(
                    id=c["chunk_id"],
                    document_id=doc_id,
                    chunk_index=idx,
                    page_number=c["page_number"],
                    section_title=c["section_title"],
                    content=c["content"]
                )
                db.add(chunk_record)

            db.commit()
            db.refresh(doc_record)

            # Whole-document understanding: build hierarchical summaries, concepts, facts & relations
            logger.info(f"[Stage H: Whole-Document Knowledge Generation] Building semantic graph & concepts for {doc_id}...")
            try:
                from .document_knowledge_service import document_knowledge_service
                document_knowledge_service.build_and_index_knowledge(doc_id, db)
                db.refresh(doc_record)
            except Exception as ke:
                logger.warning(f"Whole-document knowledge extraction encountered non-fatal warning: {ke}")

            logger.info(f"[Stage I: Final API Response] Ingestion and indexing 100% complete for {original_filename} ({doc_id})")
            return doc_record
        except Exception as e:
            logger.error(f"SQL persistence failed for document {doc_id}. Executing compensating Qdrant deletion: {e}")
            try:
                qdrant_service.delete_document(doc_id)
            except Exception as qe:
                logger.warning(f"Compensating Qdrant deletion encountered error for {doc_id}: {qe}")
            db.rollback()
            raise

document_service = DocumentProcessingService()

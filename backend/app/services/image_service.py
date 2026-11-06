import os
import re
import io
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from PIL import Image, ImageOps
import numpy as np
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.document import DocumentModel, DocumentChunkModel
from ..schemas.image import (
    OCRLineSchema,
    VisualEvidenceItemSchema,
    ImageDimensionsSchema,
    ImageUnderstandingRepresentation,
)
from .embedding_service import embedding_service
from .qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}
SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
}
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB


class ImageProcessingService:
    """
    Production-grade multimodal image processing, OCR, and visual knowledge representation service.
    
    Guarantees:
    - Verifies image integrity and orientation via Pillow without quality degradation.
    - Extracts optical character recognition data using RapidOCR with bounding boxes and confidence.
    - Conducts multimodal visual understanding using local Qwen2.5-VL with the Q8_0 vision projector.
    - Generates structured, discrete visual evidence items (img-ev-1, img-ev-2, etc.).
    - Never confuses OCR text with visual interpretation.
    - Never fabricates visual details not present in the image.
    - Preserves sequential single-resident inference lock.
    """

    def __init__(self):
        self._ocr_engine = None

    def _get_ocr_engine(self):
        if self._ocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr_engine = RapidOCR()
        return self._ocr_engine

    def validate_and_preprocess(self, file_path: str) -> Tuple[Image.Image, ImageDimensionsSchema]:
        """
        Validates the image file, fixes EXIF orientation, and extracts dimensions and metadata.
        """
        if not os.path.exists(file_path):
            raise ValueError(f"Image file does not exist on disk: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError(f"Uploaded image '{os.path.basename(file_path)}' is empty (0 bytes).")
        if file_size > MAX_IMAGE_BYTES:
            raise ValueError(f"Image exceeds maximum permitted size of 25 MB ({file_size / (1024 * 1024):.2f} MB).")

        ext = os.path.splitext(file_path)[1].lstrip(".").lower()
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"Unsupported image extension '.{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}."
            )

        try:
            # Verify file integrity
            with Image.open(file_path) as test_img:
                test_img.verify()

            # Re-open after verify() (Pillow requirement)
            img = Image.open(file_path)
            # Correct EXIF orientation
            img = ImageOps.exif_transpose(img) or img

            w, h = img.size
            if w < 10 or h < 10:
                raise ValueError(f"Image dimensions ({w}x{h}) are too small for visual analysis.")

            mp = (w * h) / 1_000_000.0
            gcd_val = self._compute_gcd(w, h)
            aspect_ratio = f"{w // gcd_val}:{h // gcd_val}" if gcd_val > 1 else f"{w / h:.2f}:1"

            dim_schema = ImageDimensionsSchema(
                width=w,
                height=h,
                format=(img.format or ext).upper(),
                mode=img.mode,
                megapixels=round(mp, 2),
                aspect_ratio=aspect_ratio,
            )
            return img, dim_schema
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.error(f"Image validation failed for {file_path}: {e}")
            raise ValueError(f"Corrupted or invalid image file: {e}")

    @staticmethod
    def _compute_gcd(a: int, b: int) -> int:
        import math
        return math.gcd(a, b)

    def extract_ocr_data(self, img: Image.Image) -> Tuple[str, List[OCRLineSchema]]:
        """
        Extracts visible text lines, confidence scores, and bounding boxes using RapidOCR.
        """
        ocr_lines: List[OCRLineSchema] = []
        full_text_parts: List[str] = []

        try:
            engine = self._get_ocr_engine()
            # Convert PIL Image to RGB numpy array for RapidOCR
            if img.mode != "RGB":
                rgb_img = img.convert("RGB")
            else:
                rgb_img = img

            np_arr = np.array(rgb_img)
            result, _ = engine(np_arr)

            if result:
                for item in result:
                    if item and len(item) >= 3 and item[1]:
                        box = item[0]  # list of 4 points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                        text = str(item[1]).strip()
                        raw_conf = float(item[2])
                        # Normalize confidence to 0-100 scale
                        conf = round(raw_conf * 100.0 if raw_conf <= 1.0 else raw_conf, 1)

                        if text:
                            # Convert box points to python int list
                            clean_box = [[int(pt[0]), int(pt[1])] for pt in box] if box else None
                            ocr_lines.append(OCRLineSchema(text=text, confidence=conf, box=clean_box))
                            full_text_parts.append(text)

            combined_ocr = "\n".join(full_text_parts).strip()
            logger.info(f"[Stage OCR] Extracted {len(ocr_lines)} text lines ({len(combined_ocr)} chars) from image")
            return combined_ocr, ocr_lines
        except Exception as e:
            logger.warning(f"RapidOCR extraction encountered non-fatal error: {e}")
            return "", []

    def analyze_image_multimodal(
        self,
        file_path: str,
        ocr_text: str = "",
        dimensions: Optional[ImageDimensionsSchema] = None
    ) -> str:
        """
        Executes multimodal visual analysis via local Qwen2.5-VL with the Q8_0 vision projector.
        Guarded by sequential model manager lock.
        """
        from ..llm.model_manager import local_model_manager

        if getattr(local_model_manager, "mock_mode", False):
            return (
                "SUMMARY:\nAnalytical visual infographic displaying workflow stages and quantitative metrics.\n\n"
                "KEY ENTITIES:\n- Workflow Stages\n- Process Metrics\n- Data Visualizations\n\n"
                "VISUAL OBSERVATIONS:\n- Sequential circular stages connected by directional flow arrows\n- Numerical finding boxes below each stage\n\n"
                "NUMERICAL VALUES & METRICS:\n- Explicit metrics recorded per stage\n\n"
                "RELATIONSHIPS & TRENDS:\n- Sequential progression from collection through interpretation.\n\n"
                "DISCRETE VISUAL EVIDENCE ITEMS:\n- Evidence 1: Stage progression and reported quantitative counts.\n\n"
                "EPISTEMIC UNCERTAINTIES & CAVEATS:\n- Underlying experimental methodology not fully detailed in visual summary."
            )

        prompt = (
            "You are an expert multimodal visual analyzer for academic, technical, scientific, and data-driven debate evidence.\n"
            "Analyze this uploaded image with high empirical rigor and objectivity.\n\n"
            "Provide your analysis using EXACTLY the following structured sections:\n\n"
            "SUMMARY:\n"
            "[A concise 2-3 sentence factual overview of what the image portrays]\n\n"
            "KEY ENTITIES:\n"
            "- [Entity / Component / Subject 1]\n"
            "- [Entity / Component / Subject 2]\n\n"
            "VISUAL OBSERVATIONS:\n"
            "- [Exact visual feature, chart axes, legends, shapes, colors, or structural elements]\n\n"
            "NUMERICAL VALUES & METRICS:\n"
            "- [Explicit numbers, percentages, benchmark metrics, scale ranges with units]\n\n"
            "RELATIONSHIPS & TRENDS:\n"
            "- [Visual and structural relationships, comparisons, directional changes, dependencies]\n\n"
            "DISCRETE VISUAL EVIDENCE ITEMS:\n"
            "- [Evidence 1: description and spatial location]\n"
            "- [Evidence 2: description and spatial location]\n\n"
            "EPISTEMIC UNCERTAINTIES & CAVEATS:\n"
            "- [Ambiguous, low-resolution, occluded, or unverified visual elements; state 'None observed' if completely clear]\n\n"
            "Strict Rules:\n"
            "1. Ground your observations strictly on what is directly visible in the image.\n"
            "2. Do not invent, hallucinate, or extrapolate data not present in the image.\n"
            "3. If numerical values are blurry or absent, explicitly state that in uncertainties."
        )

        logger.info(f"[Stage Vision Analysis] Running Qwen multimodal vision analysis on {os.path.basename(file_path)}...")
        raw_analysis = local_model_manager.describe_image(
            image_input=file_path,
            prompt=prompt
        )
        return str(raw_analysis).strip()

    def parse_vision_analysis_to_structured(
        self,
        vision_text: str,
        ocr_text: str,
        ocr_lines: List[OCRLineSchema],
        dimensions: ImageDimensionsSchema,
        filename: str,
        doc_id: str
    ) -> ImageUnderstandingRepresentation:
        """
        Parses raw multimodal vision text and OCR lines into a structured ImageUnderstandingRepresentation
        with discrete visual evidence items.
        """
        sections = {
            "summary": "",
            "key_entities": [],
            "visual_observations": [],
            "numerical_values": [],
            "relationships": [],
            "evidence_items": [],
            "uncertainties": [],
        }

        current_section = None
        for line in vision_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            upper = line_str.upper()
            if "SUMMARY:" in upper:
                current_section = "summary"
                remainder = line_str.split(":", 1)[1].strip()
                if remainder:
                    sections["summary"] = remainder
                continue
            elif "KEY ENTITIES:" in upper:
                current_section = "key_entities"
                continue
            elif "VISUAL OBSERVATIONS:" in upper:
                current_section = "visual_observations"
                continue
            elif "NUMERICAL VALUES" in upper:
                current_section = "numerical_values"
                continue
            elif "RELATIONSHIPS" in upper or "TRENDS:" in upper:
                current_section = "relationships"
                continue
            elif "DISCRETE VISUAL EVIDENCE" in upper:
                current_section = "evidence_items"
                continue
            elif "EPISTEMIC UNCERTAINTIES" in upper or "CAVEATS:" in upper:
                current_section = "uncertainties"
                continue

            # Accumulate into current section
            if current_section == "summary":
                if sections["summary"]:
                    sections["summary"] += " " + line_str
                else:
                    sections["summary"] = line_str
            elif current_section in ("key_entities", "visual_observations", "numerical_values", "relationships", "evidence_items", "uncertainties"):
                clean_item = re.sub(r"^[-*•\d.]+\s*", "", line_str).strip()
                if clean_item and clean_item.lower() not in ("none", "none observed", "none detected"):
                    sections[current_section].append(clean_item)

        summary = sections["summary"].strip() or f"Visual image ({dimensions.format} {dimensions.width}x{dimensions.height}) displaying technical chart elements."

        # Assemble Discrete Visual Evidence Items (img-ev-1, img-ev-2, etc.)
        discrete_items: List[VisualEvidenceItemSchema] = []
        ev_counter = 1

        # 1. Evidence from parsed vision items
        for raw_ev in sections["evidence_items"][:5]:
            label = raw_ev.split(":")[0].strip() if ":" in raw_ev else f"Visual Observation #{ev_counter}"
            content = raw_ev.split(":", 1)[1].strip() if ":" in raw_ev else raw_ev
            discrete_items.append(
                VisualEvidenceItemSchema(
                    id=f"img-ev-{ev_counter}",
                    label=label[:80],
                    type="visible_data",
                    location="visible image area",
                    content=content,
                    confidence=95.0,
                )
            )
            ev_counter += 1

        # 2. Evidence from numerical metrics if not already included
        for num_val in sections["numerical_values"][:4]:
            if not any(num_val in d.content for d in discrete_items):
                discrete_items.append(
                    VisualEvidenceItemSchema(
                        id=f"img-ev-{ev_counter}",
                        label=f"Numerical Finding #{ev_counter}",
                        type="chart_trend",
                        location="data chart",
                        content=num_val,
                        confidence=92.0,
                    )
                )
                ev_counter += 1

        # 3. Evidence from high-confidence OCR text lines
        for ocr_line in ocr_lines[:5]:
            if len(ocr_line.text) > 4 and not any(ocr_line.text in d.content for d in discrete_items):
                loc_desc = "detected text label"
                if ocr_line.box:
                    loc_desc = f"coordinates [{ocr_line.box[0][0]},{ocr_line.box[0][1]}]"
                discrete_items.append(
                    VisualEvidenceItemSchema(
                        id=f"img-ev-{ev_counter}",
                        label=f"Optical Label: '{ocr_line.text[:30]}'",
                        type="ocr_label",
                        location=loc_desc,
                        content=f"Exact visible text: \"{ocr_line.text}\" (OCR confidence: {ocr_line.confidence}%)",
                        confidence=ocr_line.confidence,
                    )
                )
                ev_counter += 1

        # 4. Uncertainty item if reported
        for unc in sections["uncertainties"][:2]:
            discrete_items.append(
                VisualEvidenceItemSchema(
                    id=f"img-ev-{ev_counter}",
                    label="Epistemic Uncertainty / Caveat",
                    type="uncertainty",
                    location="image boundary",
                    content=unc,
                    confidence=70.0,
                )
            )
            ev_counter += 1

        # Fallback if no discrete items parsed
        if not discrete_items:
            discrete_items.append(
                VisualEvidenceItemSchema(
                    id=f"img-ev-1",
                    label="Primary Image Overview",
                    type="visible_data",
                    location="full image",
                    content=summary,
                    confidence=90.0,
                )
            )

        return ImageUnderstandingRepresentation(
            image_id=doc_id,
            filename=filename,
            dimensions=dimensions,
            summary=summary,
            ocr_text=ocr_text,
            ocr_lines=ocr_lines,
            visual_observations=sections["visual_observations"],
            key_entities=sections["key_entities"],
            numerical_values=sections["numerical_values"],
            relationships=sections["relationships"],
            evidence_items=discrete_items,
            uncertainties=sections["uncertainties"],
            file_path=None
        )

    def generate_suggested_propositions(self, rep: ImageUnderstandingRepresentation) -> List[str]:
        """
        Produces context-aware debate propositions grounded strictly on the image's findings.
        """
        props = []
        if rep.numerical_values:
            first_num = rep.numerical_values[0]
            props.append(f"Does this image provide sufficient empirical evidence to substantiate '{first_num}'?")

        if rep.key_entities:
            entity_str = ", ".join(rep.key_entities[:2])
            props.append(f"Does the visual data for {entity_str} substantiate a meaningful improvement or risk?")

        props.append(f"Does this image demonstrate significant performance improvement or valid empirical claims?")
        props.append(f"What methodological limitations or confounding variables are visible in this data presentation?")
        return props[:4]

    def ingest_image(
        self,
        db: Session,
        file_path: str,
        original_filename: str,
        file_type: str = "png"
    ) -> DocumentModel:
        """
        Complete end-to-end image ingestion pipeline:
        1. Validation & Pillow Preprocessing
        2. RapidOCR Text & Box Extraction
        3. Multimodal Qwen Vision Analysis
        4. Structured Image Understanding Representation
        5. Chunking, Vector Embeddings (MiniLM-L6) & Qdrant Upsert
        6. SQLite Database Persistence
        """
        doc_id = str(uuid.uuid4())
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = f"{file_size_bytes / (1024 * 1024):.2f} MB" if file_size_bytes > 1024 * 1024 else f"{file_size_bytes / 1024:.1f} KB"
        clean_ext = file_type.lower().lstrip(".")

        logger.info(f"[Image Pipeline] Step 1: Validating and preprocessing '{original_filename}' ({file_size_mb})")
        pil_img, dimensions = self.validate_and_preprocess(file_path)

        logger.info(f"[Image Pipeline] Step 2: Extracting optical character recognition (OCR) via RapidOCR")
        ocr_text, ocr_lines = self.extract_ocr_data(pil_img)

        logger.info(f"[Image Pipeline] Step 3: Executing Qwen multimodal visual understanding")
        vision_raw = self.analyze_image_multimodal(file_path, ocr_text=ocr_text, dimensions=dimensions)

        logger.info(f"[Image Pipeline] Step 4: Structuring visual knowledge & evidence items")
        representation = self.parse_vision_analysis_to_structured(
            vision_text=vision_raw,
            ocr_text=ocr_text,
            ocr_lines=ocr_lines,
            dimensions=dimensions,
            filename=original_filename,
            doc_id=doc_id
        )
        representation.file_path = file_path
        suggested_questions = self.generate_suggested_propositions(representation)

        # Step 5: Construct Structured Chunks for Vector Indexing
        chunks_payload = []
        # Chunk 0: High-Level Overview & Summary
        chunks_payload.append({
            "chunk_id": str(uuid.uuid4()),
            "content": f"[Visual Image Summary: {original_filename} ({dimensions.format} {dimensions.width}x{dimensions.height})]\n{representation.summary}",
            "section_title": "Visual Image Summary",
            "page_number": 1,
            "word_count": len(representation.summary.split()),
            "evidence_id": "img-summary"
        })

        # Chunk 1: Verbatim OCR Text
        if representation.ocr_text:
            chunks_payload.append({
                "chunk_id": str(uuid.uuid4()),
                "content": f"[Optical Character Recognition (OCR) Text from {original_filename}]\n{representation.ocr_text}",
                "section_title": "Optical Text (OCR)",
                "page_number": 1,
                "word_count": len(representation.ocr_text.split()),
                "evidence_id": "img-ocr"
            })

        # Chunk 2: Numerical Metrics, Relationships & Entities
        num_str = "; ".join(representation.numerical_values) if representation.numerical_values else "No explicit metrics"
        rel_str = "; ".join(representation.relationships) if representation.relationships else "Standard visual layout"
        ent_str = ", ".join(representation.key_entities) if representation.key_entities else "Visual elements"
        obs_text = (
            f"[Visual Entities & Quantitative Findings from {original_filename}]\n"
            f"Entities: {ent_str}\n"
            f"Numerical Metrics: {num_str}\n"
            f"Relationships & Trends: {rel_str}"
        )
        chunks_payload.append({
            "chunk_id": str(uuid.uuid4()),
            "content": obs_text,
            "section_title": "Visual Metrics & Entities",
            "page_number": 1,
            "word_count": len(obs_text.split()),
            "evidence_id": "img-metrics"
        })

        # Chunks 3+: Discrete Visual Evidence Items
        for ev in representation.evidence_items:
            ev_content = f"[Visual Evidence: {ev.id} ({ev.type} at {ev.location})]\n{ev.label}: {ev.content}"
            chunks_payload.append({
                "chunk_id": str(uuid.uuid4()),
                "content": ev_content,
                "section_title": f"Visual Evidence ({ev.id})",
                "page_number": 1,
                "word_count": len(ev_content.split()),
                "evidence_id": ev.id
            })

        # Step 6: Generate Embeddings & Upsert to Qdrant
        logger.info(f"[Image Pipeline] Step 5: Generating vector embeddings for {len(chunks_payload)} visual chunks")
        chunk_texts = [c["content"] for c in chunks_payload]
        vectors = embedding_service.embed_documents(chunk_texts)

        qdrant_items = []
        for c in chunks_payload:
            qdrant_items.append({
                "chunk_id": c["chunk_id"],
                "document_id": doc_id,
                "page_number": 1,
                "section_title": c["section_title"],
                "content": c["content"],
                "title": original_filename,
                "source_type": "image",
                "evidence_id": c.get("evidence_id")
            })

        indexing_success = qdrant_service.upsert_chunks(qdrant_items, vectors)
        if not indexing_success:
            logger.error(f"Vector indexing failed for image document {doc_id}")
            raise RuntimeError(f"Vector indexing failed for image '{original_filename}'")

        # Step 7: Persist to SQLite Database
        logger.info(f"[Image Pipeline] Step 6: Persisting Image Document {doc_id} to database")
        sections_meta = [
            {
                "id": "sec-image-1",
                "title": "Multimodal Visual Analysis & Evidence",
                "pageNumber": 1,
                "wordCount": sum(c["word_count"] for c in chunks_payload),
                "claimsCount": len(representation.evidence_items),
                "summary": representation.summary
            }
        ]

        metadata_dict = {
            "source_type": "image",
            "file_path": file_path,
            "image_metadata": dimensions.model_dump(),
            "image_understanding": representation.model_dump(),
            "visual_evidence": [e.model_dump() for e in representation.evidence_items],
            "ocr_lines": [l.model_dump() for l in representation.ocr_lines],
            "sections": sections_meta,
            "suggestedQuestions": suggested_questions,
        }

        doc_record = DocumentModel(
            id=doc_id,
            name=original_filename,
            file_type=clean_ext,
            file_size=file_size_mb,
            file_size_bytes=file_size_bytes,
            page_count=1,
            status="ready",
            summary=representation.summary,
            key_claims_count=len(representation.visual_observations) or len(representation.evidence_items),
            evidence_points_count=len(representation.evidence_items),
            debates_count=0,
            metadata_json=metadata_dict
        )

        try:
            db.add(doc_record)
            for idx, c in enumerate(chunks_payload):
                chunk_record = DocumentChunkModel(
                    id=c["chunk_id"],
                    document_id=doc_id,
                    chunk_index=idx,
                    page_number=1,
                    section_title=c["section_title"],
                    content=c["content"],
                    metadata_json={"evidence_id": c.get("evidence_id"), "source_type": "image"}
                )
                db.add(chunk_record)

            db.commit()
            db.refresh(doc_record)
            logger.info(f"[Image Pipeline] Successfully ingested and indexed image '{original_filename}' ({doc_id})")
            return doc_record
        except Exception as e:
            logger.error(f"SQL persistence failed for image document {doc_id}. Executing compensating rollback: {e}")
            try:
                qdrant_service.delete_document(doc_id)
            except Exception as qe:
                logger.warning(f"Compensating Qdrant deletion encountered error: {qe}")
            db.rollback()
            raise

image_service = ImageProcessingService()


import os
import io
import shutil
import uuid
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..models.document import DocumentModel, DocumentChunkModel
from ..models.debate import DebateModel
from ..services.document_service import document_service
from ..services.document_knowledge_service import document_knowledge_service
from ..services.qdrant_service import qdrant_service
from ..schemas.document import (
    DocumentMetadataSchema,
    DocumentUploadResponse,
    DirectTextInputRequest,
)
from ..schemas.document_knowledge import (
    DocumentKnowledgeRepresentation,
    DocumentQueryResponseSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "./uploaded_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _find_document_file_path(doc: DocumentModel) -> Optional[str]:
    meta = doc.metadata_json or {}
    if "file_path" in meta and os.path.exists(meta["file_path"]):
        return meta["file_path"]

    # Search in UPLOAD_DIR
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            if fname.endswith(doc.name) or doc.id in fname:
                fp = os.path.join(UPLOAD_DIR, fname)
                if os.path.isfile(fp):
                    return fp
    return None

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "txt", "md",
    "png", "jpg", "jpeg", "webp", "bmp"
}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

def _serialize_document(doc: DocumentModel) -> DocumentMetadataSchema:
    meta = doc.metadata_json or {}
    sections = meta.get("sections", [])
    suggested_q = meta.get("suggestedQuestions", [])
    return DocumentMetadataSchema(
        id=doc.id,
        name=doc.name,
        fileSize=doc.file_size or "0 B",
        fileSizeBytes=doc.file_size_bytes or 0,
        fileType=doc.file_type or "pdf",
        pageCount=doc.page_count or 1,
        uploadedAt=doc.created_at.strftime("%b %d, %Y %I:%M %p") if doc.created_at else "Just now",
        status=doc.status or "ready",
        summary=doc.summary or "",
        keyClaimsCount=doc.key_claims_count or 0,
        evidencePointsCount=doc.evidence_points_count or 0,
        debatesCount=doc.debates_count or 0,
        sections=sections,
        suggestedQuestions=suggested_q
    )

@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest documents (PDF, DOCX, TXT, MD, Images).
    Validates file format, size boundaries, and content integrity.
    """
    fname = file.filename or "uploaded_document.txt"
    ext = fname.split(".")[-1].lower() if "." in fname else ""

    # 1. File type validation
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '.{ext}'. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    unique_name = f"{uuid.uuid4().hex}_{fname}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    try:
        # 2. Stream to disk and enforce size bounds
        total_bytes = 0
        with open(dest_path, "wb") as buffer:
            while chunk := file.file.read(1024 * 64):  # 64 KB chunks
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds maximum allowed size of 25 MB."
                    )
                buffer.write(chunk)

        # 3. Empty file validation
        if total_bytes == 0:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty (0 bytes)."
            )

        # 4. Ingest and vector index
        doc_record = document_service.ingest_document(
            db=db,
            file_path=dest_path,
            original_filename=fname,
            file_type=ext
        )
        return DocumentUploadResponse(
            document=_serialize_document(doc_record),
            message="Document successfully processed and vector indexed"
        )
    except HTTPException:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        raise
    except ValueError as ve:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        logger.warning(f"Validation error during ingestion of {fname}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        logger.error(f"Error during document upload of {fname}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document processing failed: {e}")

@router.post("/text", response_model=DocumentUploadResponse)
def ingest_text_document(
    payload: DirectTextInputRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest direct text input without requiring a file upload.
    Validates content presence, chunks, embeds, and indexes into Qdrant & SQL.
    """
    content = payload.content.strip()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Text content cannot be empty."
        )

    title = (payload.title or "Direct Text Input").strip()
    try:
        doc_record = document_service.ingest_raw_text(
            db=db,
            content=content,
            title=title
        )
        return DocumentUploadResponse(
            document=_serialize_document(doc_record),
            message="Text content successfully processed and vector indexed"
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during direct text ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Direct text ingestion failed: {e}")

@router.get("", response_model=List[DocumentMetadataSchema])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(DocumentModel).order_by(DocumentModel.created_at.desc()).all()
    return [_serialize_document(d) for d in docs]

@router.get("/stats/summary")
def get_documents_stats(db: Session = Depends(get_db)):
    """
    Returns inventory counts of documents, chunks, files, and Qdrant points.
    """
    doc_count = db.query(DocumentModel).count()
    chunk_count = db.query(DocumentChunkModel).count()
    debates_linked = db.query(DebateModel).filter(DebateModel.document_id.isnot(None)).count()
    
    file_count = 0
    total_bytes = 0
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            fp = os.path.join(UPLOAD_DIR, f)
            if os.path.isfile(fp):
                file_count += 1
                total_bytes += os.path.getsize(fp)
                
    qdrant_info = qdrant_service.get_collection_info()
    
    return {
        "documents_count": doc_count,
        "chunks_count": chunk_count,
        "debates_linked_count": debates_linked,
        "uploaded_files_count": file_count,
        "uploaded_files_bytes": total_bytes,
        "uploaded_files_mb": round(total_bytes / (1024 * 1024), 2),
        "qdrant": qdrant_info
    }

@router.delete("")
@router.delete("/clear-all")
def delete_all_documents(db: Session = Depends(get_db)):
    """
    Deletes all uploaded documents, chunks, knowledge representations,
    Qdrant vector points, and uploaded files on disk.
    Unlinks debates referencing documents without deleting debates.
    """
    doc_count_before = db.query(DocumentModel).count()
    chunk_count_before = db.query(DocumentChunkModel).count()
    debates_linked = db.query(DebateModel).filter(DebateModel.document_id.isnot(None)).count()

    # 1. Unlink debates referencing documents
    db.query(DebateModel).filter(DebateModel.document_id.isnot(None)).update(
        {DebateModel.document_id: None},
        synchronize_session=False
    )

    # 2. Delete all document chunks and documents
    db.query(DocumentChunkModel).delete(synchronize_session=False)
    db.query(DocumentModel).delete(synchronize_session=False)
    db.commit()

    # 3. Purge Qdrant points
    qdrant_cleared = qdrant_service.clear_all_points()

    # 4. Remove all files from uploaded_documents
    deleted_files = 0
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            fpath = os.path.join(UPLOAD_DIR, fname)
            try:
                if os.path.isfile(fpath) or os.path.islink(fpath):
                    os.unlink(fpath)
                    deleted_files += 1
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                    deleted_files += 1
            except Exception as fe:
                logger.warning(f"Could not remove file {fpath}: {fe}")

    return {
        "success": True,
        "deleted_documents": doc_count_before,
        "deleted_chunks": chunk_count_before,
        "unlinked_debates": debates_linked,
        "deleted_files": deleted_files,
        "qdrant_purged": qdrant_cleared,
        "message": f"Successfully cleared {doc_count_before} documents, {chunk_count_before} chunks, {deleted_files} files, and purged all vector points."
    }

@router.delete("/{document_id}")
def delete_single_document(document_id: str, db: Session = Depends(get_db)):
    """
    Deletes a single document by ID, its chunks, Qdrant vectors, and disk file.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Unlink debates
    db.query(DebateModel).filter(DebateModel.document_id == document_id).update(
        {DebateModel.document_id: None},
        synchronize_session=False
    )

    # Delete from Qdrant
    qdrant_service.delete_document(document_id)

    # Delete disk file if matches filename pattern
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            if doc.name in fname or document_id in fname:
                try:
                    os.remove(os.path.join(UPLOAD_DIR, fname))
                except Exception:
                    pass

    # Delete chunks and doc
    db.delete(doc)
    db.commit()

    return {"success": True, "deleted_document_id": document_id}

@router.get("/{document_id}", response_model=DocumentMetadataSchema)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize_document(doc)

class DocumentQueryRequest(BaseModel):
    query: str

class DebateGroundingRequest(BaseModel):
    proposition: str

@router.get("/{document_id}/knowledge", response_model=DocumentKnowledgeRepresentation)
def get_document_knowledge(document_id: str, db: Session = Depends(get_db)):
    rep = document_knowledge_service.get_knowledge(document_id, db)
    if not rep:
        raise HTTPException(status_code=404, detail="Document not found or knowledge representation could not be built.")
    return rep

@router.post("/{document_id}/query", response_model=DocumentQueryResponseSchema)
def query_document_endpoint(document_id: str, payload: DocumentQueryRequest, db: Session = Depends(get_db)):
    q = payload.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        return document_knowledge_service.query_document(document_id, q, db)
    except Exception as e:
        logger.error(f"Error querying document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{document_id}/reuse-for-debate")
def reuse_document_for_debate(document_id: str, payload: DebateGroundingRequest, db: Session = Depends(get_db)):
    prop = payload.proposition.strip()
    if not prop:
        raise HTTPException(status_code=400, detail="Proposition cannot be empty.")
    try:
        return document_knowledge_service.reuse_knowledge_for_debate(document_id, prop, db)
    except Exception as e:
        logger.error(f"Error preparing debate grounding for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)):
    """
    Serves the original uploaded PDF, document, or image binary file.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    fpath = _find_document_file_path(doc)
    if not fpath or not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Original document file not found on disk")
    
    ft = (doc.file_type or "pdf").lower()
    if ft == "pdf":
        media_type = "application/pdf"
    elif ft in ("png", "webp", "bmp"):
        media_type = f"image/{ft}"
    elif ft in ("jpg", "jpeg"):
        media_type = "image/jpeg"
    else:
        media_type = "application/octet-stream"
    return FileResponse(fpath, media_type=media_type, filename=doc.name)

@router.get("/{document_id}/image-understanding")
def get_document_image_understanding(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns structured image understanding representation (OCR lines, visual evidence items,
    numerical metrics, relationships, dimensions, and uncertainties).
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    meta = doc.metadata_json or {}
    if meta.get("source_type") != "image" and doc.file_type not in ("png", "jpg", "jpeg", "webp", "bmp"):
        raise HTTPException(status_code=400, detail="Document is not an image")
    
    img_rep = meta.get("image_understanding")
    if not img_rep:
        raise HTTPException(status_code=404, detail="Image understanding representation not found")
        
    return img_rep

@router.get("/{document_id}/pages/{page_number}/render")
def render_document_page(
    document_id: str,
    page_number: int,
    scale: float = Query(2.0, ge=1.0, le=4.0),
    db: Session = Depends(get_db)
):
    """
    Renders the exact original uploaded PDF page at high DPI as a PNG image stream,
    or returns the original image directly if the document is an image.
    Preserves verbatim formatting, tables, figures, equations, and typographical layouts.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fpath = _find_document_file_path(doc)
    if not fpath or not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Original document file not found on disk")

    # If document is an image format, serve original image content
    if doc.file_type in ["png", "jpg", "jpeg", "webp", "bmp"]:
        with open(fpath, "rb") as img_file:
            img_bytes = img_file.read()
        ft = doc.file_type.lower()
        m_type = f"image/{'jpeg' if ft == 'jpg' else ft}"
        return Response(
            content=img_bytes,
            media_type=m_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Document-Page": "1",
                "X-Document-Total-Pages": "1"
            }
        )

    if doc.file_type != "pdf":
        raise HTTPException(status_code=400, detail="Page rendering is supported only for PDF or Image documents")

    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(fpath)
        if page_number < 1 or page_number > len(pdf):
            raise HTTPException(
                status_code=400,
                detail=f"Page number {page_number} is out of bounds (document has {len(pdf)} pages)"
            )

        page = pdf[page_number - 1]
        pil_img = page.render(scale=scale).to_pil()
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Document-Page": str(page_number),
                "X-Document-Total-Pages": str(len(pdf))
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering page {page_number} of doc {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to render PDF page: {e}")

@router.get("/{document_id}/pages/{page_number}/text")
def get_document_page_text(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves the verbatim OCR or native text extracted for a specific document page.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(DocumentChunkModel).filter(
        DocumentChunkModel.document_id == document_id,
        DocumentChunkModel.page_number == page_number
    ).order_by(DocumentChunkModel.chunk_index).all()

    if not chunks:
        if page_number < 1 or page_number > (doc.page_count or 1):
            raise HTTPException(status_code=400, detail=f"Page number {page_number} is out of range")
        return {
            "document_id": document_id,
            "page_number": page_number,
            "section_title": f"Page {page_number}",
            "extracted_text": "",
            "character_count": 0,
            "word_count": 0,
            "chunks_count": 0,
            "message": "No text extracted on this page"
        }

    combined_text = "\n\n".join(c.content for c in chunks)
    return {
        "document_id": document_id,
        "page_number": page_number,
        "section_title": chunks[0].section_title or f"Page {page_number}",
        "extracted_text": combined_text,
        "character_count": len(combined_text),
        "word_count": len(combined_text.split()),
        "chunks_count": len(chunks)
    }

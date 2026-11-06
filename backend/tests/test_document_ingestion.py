import os
import io
import uuid
import pytest
import zipfile
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from app.main import app
from app.services.document_service import document_service
from app.database.session import SessionLocal, Base, engine
from app.models.document import DocumentModel, DocumentChunkModel

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def make_two_page_text_pdf(text1: str, text2: str) -> bytes:
    """
    Constructs a minimal valid 2-page PDF document containing exact text in streams.
    """
    c1 = f"BT /F1 12 Tf 50 700 Td ({text1}) Tj ET".encode("latin-1")
    c2 = f"BT /F1 12 Tf 50 700 Td ({text2}) Tj ET".encode("latin-1")
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 7 0 R >> >> >> endobj
4 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R /Resources << /Font << /F1 7 0 R >> >> >> endobj
5 0 obj << /Length {len(c1)} >> stream
""".encode("latin-1") + c1 + f"""
endstream
endobj
6 0 obj << /Length {len(c2)} >> stream
""".encode("latin-1") + c2 + f"""
endstream
endobj
7 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000120 00000 n 
0000000250 00000 n 
0000000380 00000 n 
0000000480 00000 n 
0000000580 00000 n 
trailer << /Size 8 /Root 1 0 R >>
startxref
680
%%EOF
""".encode("latin-1")
    return pdf

# 1. Normalization & Chunking Unit Tests
def test_normalize_text_unicode_and_whitespace():
    raw = "This is a   test\u00a0with  non-breaking\r\nspaces, \x00control chars, and \n\n\n excessive newlines."
    normalized = document_service.normalize_text(raw)
    assert "\u00a0" not in normalized
    assert "\r" not in normalized
    assert "\x00" not in normalized
    assert "   " not in normalized
    assert "This is a test with non-breaking" in normalized

def test_chunk_text_boundaries_and_metadata():
    text = "Word " * 600  # 600 words, chunk_size=500
    chunks = document_service.chunk_text(text, page_number=2, section_title="Test Section")
    assert len(chunks) >= 2
    for c in chunks:
        assert c["page_number"] == 2
        assert c["section_title"] == "Test Section"
        assert c["word_count"] > 0
        assert "chunk_id" in c

def test_docx_xml_text_extraction(tmp_path):
    docx_file = tmp_path / "sample.docx"
    xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:r><w:t>First Paragraph in DOCX</w:t></w:r></w:p>
        <w:p><w:r><w:t>Second Paragraph in DOCX</w:t></w:r></w:p>
      </w:body>
    </w:document>"""

    with zipfile.ZipFile(docx_file, "w") as z:
        z.writestr("word/document.xml", xml_content)

    extracted = document_service.extract_from_docx(str(docx_file))
    assert "First Paragraph in DOCX" in extracted
    assert "Second Paragraph in DOCX" in extracted

# 2. File Upload Ingestion Tests
def test_full_document_upload_api_and_query(tmp_path):
    txt_file = tmp_path / "debate_brief.txt"
    txt_file.write_text("Artificial intelligence governance requires comprehensive auditing envelopes and human-in-the-loop oversight.", encoding="utf-8")

    with open(txt_file, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("debate_brief.txt", f, "text/plain")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "document" in data
    doc_id = data["document"]["id"]
    assert data["document"]["name"] == "debate_brief.txt"

    get_resp = client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 200
    doc_data = get_resp.json()
    assert doc_data["id"] == doc_id
    assert doc_data["status"] == "ready"

    list_resp = client.get("/api/documents")
    assert list_resp.status_code == 200
    all_ids = [d["id"] for d in list_resp.json()]
    assert doc_id in all_ids

def test_pdf_multipage_upload_and_page_tracking(tmp_path):
    pdf_path = tmp_path / "test_multipage.pdf"
    pdf_content = make_two_page_text_pdf(
        "Page 1 Affirmative empirical analysis of algorithmic liability bounds.",
        "Page 2 Negative counter-examination and systemic risk dissection."
    )
    pdf_path.write_bytes(pdf_content)

    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test_multipage.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 200
    doc = resp.json()["document"]
    assert doc["pageCount"] == 2
    assert len(doc["sections"]) == 2
    assert doc["sections"][0]["pageNumber"] == 1
    assert doc["sections"][1]["pageNumber"] == 2

@pytest.mark.skipif(not HAS_PIL, reason="PIL/Pillow not installed in environment")
def test_image_upload_and_structural_analysis(tmp_path):
    img_path = tmp_path / "chart_evidence.png"
    # Create valid synthetic image using Pillow
    img = Image.new("RGB", (320, 240), color="blue")
    img.save(img_path, format="PNG")

    with open(img_path, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("chart_evidence.png", f, "image/png")}
        )
    assert resp.status_code == 200
    doc = resp.json()["document"]
    assert doc["fileType"] == "png"
    assert doc["status"] == "ready"
    assert "320x240" in doc["summary"] or "PNG" in doc["summary"]

# 3. Direct Text Ingestion Tests
def test_direct_text_input_api():
    payload = {
        "title": "Adversarial Policy Framework",
        "content": "Formal verification constraint envelopes prevent catastrophic safety violations in algorithmic decision systems."
    }
    resp = client.post("/api/documents/text", json=payload)
    assert resp.status_code == 200
    doc = resp.json()["document"]
    assert doc["name"] == "Adversarial Policy Framework"
    assert doc["fileType"] == "txt"
    assert doc["status"] == "ready"
    assert doc["keyClaimsCount"] >= 1

    # Verify SQL persistence
    with SessionLocal() as db:
        saved = db.query(DocumentModel).filter(DocumentModel.id == doc["id"]).first()
        assert saved is not None
        assert len(saved.chunks) >= 1

def test_direct_text_empty_content_rejected():
    payload = {
        "title": "Empty Text",
        "content": "   \n\t   "
    }
    resp = client.post("/api/documents/text", json=payload)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

# 4. Input Validation & Error Handling Tests
def test_unsupported_file_format_rejected(tmp_path):
    bin_file = tmp_path / "payload.exe"
    bin_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00")

    with open(bin_file, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("payload.exe", f, "application/octet-stream")}
        )
    assert resp.status_code == 400
    assert "unsupported file format" in resp.json()["detail"].lower()

def test_empty_file_rejected(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")

    with open(empty_file, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("empty.txt", f, "text/plain")}
        )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

def test_corrupted_pdf_rejected(tmp_path):
    corrupt_pdf = tmp_path / "broken.pdf"
    corrupt_pdf.write_bytes(b"Not a valid PDF header at all. Random junk bytes.")

    with open(corrupt_pdf, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("broken.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 400
    assert "corrupted" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()

def test_corrupted_docx_rejected(tmp_path):
    corrupt_docx = tmp_path / "broken.docx"
    corrupt_docx.write_bytes(b"This is not a zip archive.")

    with open(corrupt_docx, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("broken.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert resp.status_code == 400
    assert "docx" in resp.json()["detail"].lower()

def test_corrupted_image_rejected(tmp_path):
    corrupt_img = tmp_path / "broken.png"
    corrupt_img.write_bytes(b"PNG header missing, corrupted raw binary string.")

    with open(corrupt_img, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("broken.png", f, "image/png")}
        )
    assert resp.status_code == 400
    assert "image" in resp.json()["detail"].lower()

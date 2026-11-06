import os
import uuid
import pytest
from app.services.embedding_service import embedding_service
from app.services.qdrant_service import qdrant_service
from app.services.document_service import document_service
from app.services.research_service import research_service
from app.services.rag_service import rag_service
from app.database.session import SessionLocal, Base, engine

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

# 1. Embedding Dimension & Uniform Model Tests
def test_embedding_service_dimension_and_uniformity():
    """
    Confirms embedding dimension is strictly 384 and that embed_text and embed_documents
    use the exact same model and produce normalized vectors.
    """
    assert embedding_service.dimension == 384

    single_vec = embedding_service.embed_text("Empirical testing of algorithmic consistency.")
    assert isinstance(single_vec, list)
    assert len(single_vec) == 384

    batch_vecs = embedding_service.embed_documents([
        "First document proposition.",
        "Second document counterargument."
    ])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 384
    assert len(batch_vecs[1]) == 384

    # Verify vector normalization (norm ~ 1.0)
    norm = sum(x * x for x in single_vec) ** 0.5
    assert abs(norm - 1.0) < 0.05

def test_text_normalization():
    raw_text = "   Empirical  evidence\u00a0on liability.\r\n\r\n\r\nSection   3.  "
    normalized = document_service.normalize_text(raw_text)
    assert "\u00a0" not in normalized
    assert "  " not in normalized
    assert normalized == "Empirical evidence on liability.\n\nSection 3."

def test_chunking_with_metadata():
    text = "Word " * 600
    chunks = document_service.chunk_text(text, page_number=3, section_title="Analysis")
    assert len(chunks) >= 2
    for c in chunks:
        assert c["page_number"] == 3
        assert c["section_title"] == "Analysis"
        assert c["word_count"] <= 500

# 2. Qdrant Collection Validation & Dimension Checks
def test_qdrant_collection_configuration_and_dimension_validation():
    """
    Validates that Qdrant collection configuration is verified and dimension mismatch raises ValueError.
    """
    assert qdrant_service.validate_collection_configuration() is True

    # Attempting to upsert a vector of invalid dimension (e.g., 128 instead of 384)
    invalid_chunks = [{
        "chunk_id": str(uuid.uuid4()),
        "document_id": "test_invalid_dim",
        "content": "Invalid vector length test"
    }]
    invalid_vectors = [[0.1] * 128]

    with pytest.raises(ValueError) as exc_info:
        qdrant_service.upsert_chunks(invalid_chunks, invalid_vectors)
    assert "invalid dimension" in str(exc_info.value).lower()

# 3. Rich Metadata Storage & Scoped Retrieval
def test_qdrant_rich_metadata_storage_and_retrieval():
    doc_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    url = "https://law-review.org/article/ai-governance-2026"

    chunks = [{
        "chunk_id": chunk_id,
        "document_id": doc_id,
        "page_number": 7,
        "section_title": "Judicial Liability",
        "content": "Synthetic judicial panels exhibited 32% lower inter-circuit sentencing variance.",
        "source_type": "document",
        "url": url,
        "title": "AI in High-Stakes Law",
        "word_count": 9
    }]
    vecs = embedding_service.embed_documents([chunks[0]["content"]])
    success = qdrant_service.upsert_chunks(chunks, vecs)
    assert success is True

    query_vec = embedding_service.embed_text("sentencing variance and synthetic panels")
    hits = qdrant_service.search_evidence(query_vec, document_id=doc_id, top_k=3)
    assert len(hits) > 0

    hit = hits[0]
    assert hit["document_id"] == doc_id
    assert hit["page_number"] == 7
    assert hit["section_title"] == "Judicial Liability"
    assert hit["source_type"] == "document"
    assert hit["url"] == url
    assert hit["title"] == "AI in High-Stakes Law"
    assert "sentencing variance" in hit["content"]

# 4. Strict Scoping Isolation: Document-Only vs Web Research
def test_strict_document_only_debate_refuses_web_search():
    """
    Verifies that a document-only debate strictly restricts search to the target document
    and NEVER silently falls back to or leaks web research chunks.
    """
    isolated_doc_id = str(uuid.uuid4())
    web_doc_id = "general_topic"

    # Ingest a document chunk
    doc_chunks = [{
        "chunk_id": str(uuid.uuid4()),
        "document_id": isolated_doc_id,
        "page_number": 1,
        "section_title": "Private Brief",
        "content": "Proprietary internal benchmark: algorithmic decisions reduced human error by 45%.",
        "source_type": "document",
        "title": "Private Company Brief"
    }]
    qdrant_service.upsert_chunks(doc_chunks, embedding_service.embed_documents([doc_chunks[0]["content"]]))

    # Ingest a web research chunk
    web_chunks = [{
        "chunk_id": str(uuid.uuid4()),
        "document_id": web_doc_id,
        "page_number": 1,
        "section_title": "Web Source",
        "content": "Global public forum consensus indicates widespread skepticism of autonomous systems.",
        "source_type": "web",
        "url": "https://public-forum.org/consensus",
        "title": "Public Opinion Review"
    }]
    qdrant_service.upsert_chunks(web_chunks, embedding_service.embed_documents([web_chunks[0]["content"]]))

    # 1. Document-only query with target document_id
    doc_results = rag_service.retrieve_evidence_for_turn(
        topic="Do autonomous algorithms reduce human error?",
        speaker="PRO",
        document_id=isolated_doc_id,
        source_scope="document"
    )
    assert len(doc_results) > 0
    for r in doc_results:
        assert r["url"] is None or "public-forum" not in r["url"]
        assert "Proprietary internal benchmark" in r["content"]

    # 2. Document-only query with missing document_id returns [] (never searches web)
    empty_results = rag_service.retrieve_evidence_for_turn(
        topic="Do autonomous algorithms reduce human error?",
        speaker="PRO",
        document_id=None,
        source_scope="document"
    )
    assert empty_results == []

    # 3. Web research query isolates from private documents
    web_results = rag_service.retrieve_evidence_for_turn(
        topic="Global public forum consensus on autonomous systems",
        speaker="CON",
        document_id=None,
        source_scope="general_topic"
    )
    assert len(web_results) > 0
    for r in web_results:
        # Guarantee private document content is strictly isolated
        assert "Proprietary internal benchmark" not in r["content"]
    assert any("public forum" in r["content"].lower() for r in web_results)

# 5. Role-Tailored Retrieval for PRO and CON
def test_rag_role_tailored_retrieval_pro_and_con():
    doc_id = str(uuid.uuid4())
    chunks = [
        {
            "chunk_id": str(uuid.uuid4()),
            "document_id": doc_id,
            "page_number": 2,
            "section_title": "Empirical Verification",
            "content": "Verification proofs mathematically guarantee the absence of race conditions in safety bounds.",
            "source_type": "document",
            "title": "Formal Safety Verification"
        },
        {
            "chunk_id": str(uuid.uuid4()),
            "document_id": doc_id,
            "page_number": 5,
            "section_title": "Risk Analysis",
            "content": "Severe distribution shift can invalidate formal verification invariant assumptions.",
            "source_type": "document",
            "title": "Formal Safety Verification"
        }
    ]
    vecs = embedding_service.embed_documents([c["content"] for c in chunks])
    qdrant_service.upsert_chunks(chunks, vecs)

    # PRO retrieval targeting affirmative defense
    pro_evidence = rag_service.retrieve_evidence_for_turn(
        topic="Formal verification in autonomous software",
        opponent_argument="Distribution shifts invalidate safety assumptions.",
        speaker="PRO",
        document_id=doc_id,
        source_scope="document"
    )
    assert len(pro_evidence) > 0
    assert any("verification proofs" in e["content"].lower() for e in pro_evidence)

    # CON retrieval targeting critique and limitations
    con_evidence = rag_service.retrieve_evidence_for_turn(
        topic="Formal verification in autonomous software",
        opponent_argument="Mathematical proofs guarantee absolute safety.",
        speaker="CON",
        document_id=doc_id,
        source_scope="document"
    )
    assert len(con_evidence) > 0
    assert any("distribution shift" in e["content"].lower() for e in con_evidence)

# 6. Non-Fabrication on Empty Retrieval
def test_empty_retrieval_zero_fabrication():
    empty_context = rag_service.format_evidence_context([])
    assert "No verified documentary evidence retrieved" in empty_context
    assert "clearly acknowledge epistemic uncertainty" in empty_context
    assert "http" not in empty_context
    assert "Source:" not in empty_context

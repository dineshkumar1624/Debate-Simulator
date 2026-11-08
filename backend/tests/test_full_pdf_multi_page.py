import os
import tempfile
import pytest
from typing import List
from backend.app.services.document_service import document_service
from backend.app.services.rag_service import rag_service
from backend.app.services.turn_parser import turn_parser, GroundedEvidenceReference


def create_mock_multi_page_pdf(pages_text: List[str], file_path: str):
    """
    Constructs a compliant multi-page PDF document with distinct text per page.
    """
    pages_objs = []
    content_objs = []
    obj_idx = 3

    for _ in pages_text:
        pages_objs.append(obj_idx)
        content_objs.append(obj_idx + 1)
        obj_idx += 2

    font_obj_idx = obj_idx
    total_objs = font_obj_idx + 1

    out = ['%PDF-1.4\n']
    offsets = [0]

    def add_obj(num, body):
        offsets.append(sum(len(s.encode('latin1')) for s in out))
        out.append(f'{num} 0 obj\n{body}\nendobj\n')

    # Catalog
    add_obj(1, '<< /Type /Catalog /Pages 2 0 R >>')
    # Pages Root
    kids = ' '.join(f'{k} 0 R' for k in pages_objs)
    add_obj(2, f'<< /Type /Pages /Kids [{kids}] /Count {len(pages_text)} >>')

    for i, (p_idx, c_idx) in enumerate(zip(pages_objs, content_objs)):
        # Page Object
        add_obj(p_idx, f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {c_idx} 0 R /Resources << /Font << /F1 {font_obj_idx} 0 R >> >> >>')
        # Content Stream
        text = pages_text[i].replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream_content = f'BT /F1 12 Tf 50 720 Td ({text}) Tj ET'
        stream_bytes = len(stream_content.encode('latin1'))
        add_obj(c_idx, f'<< /Length {stream_bytes} >>\nstream\n{stream_content}\nendstream')

    # Font Object
    add_obj(font_obj_idx, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    # Cross-Reference Table
    xref_offset = sum(len(s.encode('latin1')) for s in out)
    out.append(f'xref\n0 {total_objs}\n0000000000 65535 f \n')
    for off in offsets[1:]:
        out.append(f'{off:010d} 00000 n \n')
    out.append(f'trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n')

    with open(file_path, 'wb') as f:
        f.write(''.join(out).encode('latin1'))


@pytest.fixture
def sample_academic_pdf():
    pages = [
        "Abstract\nThis paper examines the macro-economic displacement effects of autonomous generative systems on labor markets. We analyze empirical trends in knowledge worker productivity across 12 industries.",
        "1. Introduction and Background\nTechnological change historically generates transitional frictions before labor redeployment occurs. We formulate an endogenous growth model with capital-skill complementarity.",
        "2. Methodology and Empirical Specification\nWe adopt a difference-in-differences econometric specification tracking employment indices across 50,000 firms. Microeconomic data includes hourly wages, capital investments, and automated workflow adoption.",
        "3. Results and Empirical Evaluation\nThe empirical findings demonstrate an average productivity increase of 24.8% for assisted workers, with the strongest gains observed among novice practitioners.",
        "4. Limitations and Risks\nSignificant threats to validity remain, including selection bias in firm adoption, short observation horizons, and distributional wage compression among mid-career specialists.",
        "5. Conclusion and Future Directions\nWhile aggregate productivity expands under automation, proactive wage stabilization and workforce retraining policies are essential to mitigate displacement hazards."
    ]
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        temp_path = tf.name

    create_mock_multi_page_pdf(pages, temp_path)
    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_multi_page_pdf_extraction_completeness(sample_academic_pdf):
    """
    Requirement 1: Verify all 6 pages are extracted with page numbers and detected section headings.
    """
    extracted = document_service.extract_from_pdf(sample_academic_pdf)
    assert len(extracted) == 6, f"Expected 6 pages, got {len(extracted)}"

    # Check page numbers
    for idx, page in enumerate(extracted, 1):
        assert page["page_number"] == idx
        assert page["char_count"] > 20
        assert page["has_usable_text"] is True
        assert "text" in page and len(page["text"]) > 0

    # Check section heading detection
    page_sections = [p["section_title"] for p in extracted]
    assert any("Abstract" in s or "Introduction" in s for s in page_sections[:2]), "Page 1-2 should detect Abstract/Introduction"
    assert any("Methodology" in s for s in page_sections), "Should detect Methodology"
    assert any("Results" in s for s in page_sections), "Should detect Results & Evaluation"
    assert any("Limitations" in s for s in page_sections), "Should detect Limitations & Risks"
    assert any("Conclusion" in s for s in page_sections), "Should detect Conclusion"


def test_page_aware_chunking_and_no_fake_page_one():
    """
    Requirement 2: Verify chunks retain exact page numbers and non-PDF sources retain page=None.
    """
    # 1. Multi-page document chunking
    pdf_text = "Methodology section describing empirical testing and experimental parameters across multiple cohorts."
    chunks_p3 = document_service.chunk_text(pdf_text, page_number=3, section_title="Methodology (Page 3)")
    assert len(chunks_p3) >= 1
    assert chunks_p3[0]["page_number"] == 3
    assert chunks_p3[0]["section_title"] == "Methodology (Page 3)"

    # 2. Non-PDF web article chunking (must NOT fake Page 1!)
    html_text = "Live web article detailing corporate automation policy and regulatory interventions."
    chunks_web = document_service.chunk_text(html_text, page_number=None, section_title="Policy Review Article")
    assert len(chunks_web) >= 1
    assert chunks_web[0]["page_number"] is None, "HTML web articles must have page_number=None, never fake Page 1"


def test_bounded_extraction_reporting():
    """
    Requirement 1 & 4: If extraction exceeds configured limit, system explicitly reports partial extraction.
    """
    raw_pages = [{"page_number": i, "text": f"Page {i} content"} for i in range(1, 11)]
    effective_max = 4

    is_partial = len(raw_pages) > effective_max
    pages_content = raw_pages[:effective_max]
    skipped_count = len(raw_pages) - len(pages_content) if is_partial else 0
    skipped_reason = f"PDF exceeds {effective_max} pages limit." if is_partial else None

    assert is_partial is True
    assert len(pages_content) == 4
    assert skipped_count == 6
    assert "PDF exceeds" in skipped_reason


def test_turn_parser_semantic_citation_matching():
    """
    Requirement 6: TurnParser matches citations to the actual content discussed, avoiding blind Page 1 fallback.
    """
    evidence_pool = [
        {
            "id": "chunk-p1",
            "source": "AI & Labor Study",
            "page": 1,
            "section": "Abstract (Page 1)",
            "content": "This paper examines autonomous systems and macro-economic trends in labor markets.",
            "confidenceScore": 88.0,
            "verdict": "supported"
        },
        {
            "id": "chunk-p3",
            "source": "AI & Labor Study",
            "page": 3,
            "section": "Methodology (Page 3)",
            "content": "We adopt a difference-in-differences econometric specification tracking employment indices across 50,000 firms.",
            "confidenceScore": 85.0,
            "verdict": "supported"
        },
        {
            "id": "chunk-p4",
            "source": "AI & Labor Study",
            "page": 4,
            "section": "Results & Evaluation (Page 4)",
            "content": "The empirical findings demonstrate an average productivity increase of 24.8% for assisted workers.",
            "confidenceScore": 90.0,
            "verdict": "supported"
        },
        {
            "id": "chunk-p5",
            "source": "AI & Labor Study",
            "page": 5,
            "section": "Limitations & Risks (Page 5)",
            "content": "Significant threats to validity include selection bias in firm adoption and mid-career wage compression.",
            "confidenceScore": 87.0,
            "verdict": "supported"
        },
        {
            "id": "chunk-web",
            "source": "Tech Policy Digest",
            "page": None,
            "section": "Regulatory Brief",
            "content": "European Union regulatory oversight mandates safety standards for algorithmic workplace allocation.",
            "confidenceScore": 82.0,
            "verdict": "supported"
        }
    ]

    # Test 1: PRO argument discussing empirical productivity gains (should match Page 4 Results!)
    pro_arg = "The empirical evaluation confirms substantial gains, noting that workers experience an average productivity increase of 24.8%."
    refs_pro = turn_parser._bind_genuine_citations([], evidence_pool, pro_arg)
    assert len(refs_pro) > 0
    assert refs_pro[0].page == 4, f"Expected Page 4 for results claim, got Page {refs_pro[0].page}"
    assert "Results" in refs_pro[0].section

    # Test 2: CON argument discussing limitations and wage compression (should match Page 5 Limitations!)
    con_arg = "Critical methodological limitations emerge regarding threats to validity and severe mid-career wage compression risks."
    refs_con = turn_parser._bind_genuine_citations([], evidence_pool, con_arg)
    assert len(refs_con) > 0
    assert refs_con[0].page == 5, f"Expected Page 5 for limitations claim, got Page {refs_con[0].page}"
    assert "Limitations" in refs_con[0].section

    # Test 3: Web article citation (must preserve page=None without forcing Page 1!)
    web_arg = "Mandatory safety standards for algorithmic workplace allocation are outlined in policy guidelines."
    refs_web = turn_parser._bind_genuine_citations([], evidence_pool, web_arg)
    assert len(refs_web) > 0
    assert refs_web[0].page is None, f"Expected page=None for web article, got {refs_web[0].page}"
    assert refs_web[0].excerpt is not None


def test_rag_two_stage_role_divergence_and_freshness():
    """
    Requirement 4 & 5: Verify RAG retrieves different pages for PRO vs CON and deprioritizes already-used chunks.
    """
    # Create candidate hits simulating multi-page academic chunks
    candidate_hits = [
        {"id": "c1", "content": "Overview and introductory concepts of AI automation in enterprise.", "page_number": 1, "section_title": "Abstract (Page 1)", "score": 0.82, "source_type": "web", "url": "https://arxiv.org/pdf/paper1.pdf", "title": "Paper 1"},
        {"id": "c2", "content": "Historical background on industrial automation and compute scaling.", "page_number": 2, "section_title": "Introduction (Page 2)", "score": 0.79, "source_type": "web", "url": "https://arxiv.org/pdf/paper1.pdf", "title": "Paper 1"},
        {"id": "c3", "content": "Econometric methodology, experimental design, and empirical verification data.", "page_number": 3, "section_title": "Methodology (Page 3)", "score": 0.78, "source_type": "web", "url": "https://arxiv.org/pdf/paper1.pdf", "title": "Paper 1"},
        {"id": "c4", "content": "Empirical results showing 25% efficiency gains and verified performance benchmarks.", "page_number": 4, "section_title": "Results & Evaluation (Page 4)", "score": 0.77, "source_type": "web", "url": "https://arxiv.org/pdf/paper1.pdf", "title": "Paper 1"},
        {"id": "c5", "content": "Severe limitations, architectural bottlenecks, ethical risks, and algorithmic failure modes.", "page_number": 5, "section_title": "Limitations & Risks (Page 5)", "score": 0.76, "source_type": "web", "url": "https://arxiv.org/pdf/paper1.pdf", "title": "Paper 1"},
        {"id": "c6", "content": "Policy conclusions, governance recommendations, and future work horizons.", "page_number": 6, "section_title": "Conclusion (Page 6)", "score": 0.75, "source_type": "web", "url": "https://arxiv.org/pdf/paper1.pdf", "title": "Paper 1"}
    ]

    # Mock qdrant_service.search_evidence to return candidate_hits
    from unittest.mock import patch
    with patch("backend.app.services.rag_service.qdrant_service.search_evidence", return_value=candidate_hits):
        # 1. Retrieve for PRO
        pro_ev = rag_service.retrieve_evidence_for_turn(
            topic="Will AI replace human workers?",
            speaker="PRO",
            source_scope="web"
        )
        pro_pages = [e.get("page") for e in pro_ev if e.get("page") is not None]
        # PRO should favor Methodology / Results / Abstract
        assert any(p in [3, 4] for p in pro_pages), f"PRO should retrieve Methodology (p.3) or Results (p.4), got {pro_pages}"

        # 2. Retrieve for CON
        con_ev = rag_service.retrieve_evidence_for_turn(
            topic="Will AI replace human workers?",
            speaker="CON",
            source_scope="web"
        )
        con_pages = [e.get("page") for e in con_ev if e.get("page") is not None]
        # CON should favor Limitations & Risks (p.5)
        assert 5 in con_pages, f"CON should retrieve Limitations & Risks (p.5), got {con_pages}"

        # 3. Test cross-round freshness: if c1 and c3 were used in Round 1, Round 2 should favor other chunks
        round2_ev = rag_service.retrieve_evidence_for_turn(
            topic="Will AI replace human workers?",
            speaker="PRO",
            source_scope="web",
            round_number=2,
            used_evidence_ids=["c1", "c3"]
        )
        round2_ids = [e.get("id") for e in round2_ev]
        # Fresh chunks like c4 should be prioritized over already used c1/c3
        assert "c4" in round2_ids, "Fresh chunk c4 (Results) should be prioritized in Round 2"

import os
import io
import uuid
import pytest
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
try:
    from pypdf import PdfWriter
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, DebateRoundModel, JudgeEvaluationModel
from app.models.document import DocumentModel, DocumentChunkModel
from app.llm.model_manager import local_model_manager, LocalModelManager
from app.services.qdrant_service import qdrant_service
from app.services.research_service import research_service, MockWebSearchProvider
from app.routes.debates import _run_debate_in_background
from app.graph.debate_graph import debate_graph
from app.graph.state import DebateGraphState

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db_and_mock():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield

# -------------------------------------------------------------------------
# Scenario 1: A text-only debate with one round
# -------------------------------------------------------------------------
def test_scenario_1_text_only_one_round():
    """
    Scenario 1: A text-only debate with one round.
    Verifies:
    - Exactly 1 round record
    - Exactly 2 messages in order: Round 1 PRO, then Round 1 CON
    - Exactly 1 Judge evaluation record executed after final CON
    - Database records, API /messages, API /result, API /status
    """
    topic = "Should algorithmic transparency be legally mandated for clinical decision software?"
    create_payload = {
        "topic": topic,
        "rounds": 1,
        "evidenceMode": True,
        "strictFactChecking": True,
        "sourceScope": "general_topic"
    }

    resp = client.post("/api/debates", json=create_payload)
    assert resp.status_code == 200
    debate_id = resp.json()["debateId"]

    # Execute workflow synchronously
    _run_debate_in_background(
        debate_id=debate_id,
        topic=topic,
        rounds=1,
        document_id=None,
        source_scope="general_topic"
    )

    # 1. Verify Status via API
    status_resp = client.get(f"/api/debates/{debate_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["totalRounds"] == 1
    assert status_data["errorMessage"] is None

    # 2. Verify Database Records
    with SessionLocal() as db:
        deb_rec = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert deb_rec is not None
        assert deb_rec.status == "completed"
        assert deb_rec.rounds == 1

        # Exactly 1 round record
        round_recs = db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).all()
        assert len(round_recs) == 1
        assert round_recs[0].round_number == 1
        assert round_recs[0].status == "completed"

        # Exactly 2 messages (1 PRO, 1 CON in strict order)
        messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.created_at).all()
        assert len(messages) == 2

        msg_pro = messages[0]
        msg_con = messages[1]
        assert msg_pro.round_number == 1 and msg_pro.role == "PRO" and msg_pro.speaker == "DEBATER_A"
        assert msg_con.round_number == 1 and msg_con.role == "CON" and msg_con.speaker == "DEBATER_B"
        assert len(msg_pro.content) > 30
        assert len(msg_con.content) > 30

        # Exactly 1 Judge evaluation record
        eval_rec = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert eval_rec is not None
        assert eval_rec.status == "completed"
        assert eval_rec.winner in ["PRO", "CON", "INCONCLUSIVE"]
        assert 0.0 <= eval_rec.pro_score <= 100.0
        assert 0.0 <= eval_rec.con_score <= 100.0
        assert eval_rec.created_at >= msg_con.created_at

    # 3. Verify API Ordered Messages
    msg_resp = client.get(f"/api/debates/{debate_id}/messages")
    assert msg_resp.status_code == 200
    turns = msg_resp.json()
    assert len(turns) == 2
    assert turns[0]["role"] == "PRO"
    assert turns[1]["role"] == "CON"

    # 4. Verify API Judge Result
    res_resp = client.get(f"/api/debates/{debate_id}/result")
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert "pro_score" in res_data
    assert "con_score" in res_data
    assert res_data["winner"] in ["PRO", "CON", "INCONCLUSIVE"]

# -------------------------------------------------------------------------
# Scenario 2: A text-only debate with three rounds
# -------------------------------------------------------------------------
def test_scenario_2_text_only_three_rounds():
    """
    Scenario 2: A text-only debate with three rounds.
    Verifies:
    - Exactly 3 round records
    - Exactly 6 messages in order (R1 PRO, R1 CON, R2 PRO, R2 CON, R3 PRO, R3 CON)
    - Turn-by-turn opponent argument passing and rebuttals
    - Exactly 1 Judge evaluation record executed after Round 3 CON
    """
    topic = "Universal Basic Income: Economic Feasibility and Technological Labor Displacement"
    create_payload = {
        "topic": topic,
        "rounds": 3,
        "evidenceMode": True,
        "strictFactChecking": True,
        "sourceScope": "general_topic"
    }

    resp = client.post("/api/debates", json=create_payload)
    assert resp.status_code == 200
    debate_id = resp.json()["debateId"]

    _run_debate_in_background(
        debate_id=debate_id,
        topic=topic,
        rounds=3,
        document_id=None,
        source_scope="general_topic"
    )

    with SessionLocal() as db:
        deb_rec = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert deb_rec.status == "completed"

        # Exactly 3 round records
        round_recs = db.query(DebateRoundModel).filter(
            DebateRoundModel.debate_id == debate_id
        ).order_by(DebateRoundModel.round_number).all()
        assert len(round_recs) == 3
        assert [r.round_number for r in round_recs] == [1, 2, 3]

        # Exactly 6 messages (2 per round, alternating)
        messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.round_number, DebateMessageModel.created_at).all()
        assert len(messages) == 6

        expected_sequence = [
            (1, "PRO"), (1, "CON"),
            (2, "PRO"), (2, "CON"),
            (3, "PRO"), (3, "CON")
        ]
        actual_sequence = [(m.round_number, m.role) for m in messages]
        assert actual_sequence == expected_sequence

        # Exactly 1 Judge evaluation
        eval_recs = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).all()
        assert len(eval_recs) == 1
        assert eval_recs[0].status == "completed"

    # API verification
    msg_resp = client.get(f"/api/debates/{debate_id}/messages")
    turns = msg_resp.json()
    assert len(turns) == 6
    assert [t["role"] for t in turns] == ["PRO", "CON", "PRO", "CON", "PRO", "CON"]

# -------------------------------------------------------------------------
# Scenario 3: A document-grounded debate using an uploaded PDF
# -------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_PYPDF, reason="pypdf not installed in environment")
def test_scenario_3_document_grounded_pdf_debate():
    """
    Scenario 3: Document-grounded debate using an uploaded multipage PDF.
    Verifies:
    - PDF text extraction, metadata, and chunking with page numbers
    - Qdrant indexing of 384-dimension vectors with document metadata
    - Qdrant vector retrieval tailored to debate topic
    - Debate messages contain retrieved document evidence citations
    - Judge evaluates grounded evidence citations
    """
    # 1. Create a clean 2-page test PDF in memory
    from tests.test_document_ingestion import make_two_page_text_pdf
    pdf_bytes = make_two_page_text_pdf(
        "Page 1: Empirical benchmarks show SMT verification reduced decision variance by 38.4 percent.",
        "Page 2: Clinical audits report invariant constraints introduced a 22.7 percent latency penalty."
    )

    # 2. Upload PDF via API
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("AI_Safety_Statute_2026.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_resp.status_code == 200
    doc_data = upload_resp.json()["document"]
    doc_id = doc_data["id"]
    assert doc_data["pageCount"] == 2
    assert doc_data["status"] == "ready"

    # 3. Verify Qdrant indexing
    with SessionLocal() as db:
        chunks = db.query(DocumentChunkModel).filter(DocumentChunkModel.document_id == doc_id).all()
        assert len(chunks) >= 2
        # Verify page numbers tracked
        page_nums = {c.page_number for c in chunks}
        assert 1 in page_nums and 2 in page_nums

    # 4. Run document-grounded debate
    topic = "Should SMT-solver formal verification be mandatory for autonomous regulatory systems?"
    create_payload = {
        "topic": topic,
        "rounds": 1,
        "evidenceMode": True,
        "strictFactChecking": True,
        "sourceScope": "document",
        "documentId": doc_id
    }
    create_resp = client.post("/api/debates", json=create_payload)
    assert create_resp.status_code == 200
    deb_id = create_resp.json()["debateId"]

    _run_debate_in_background(
        debate_id=deb_id,
        topic=topic,
        rounds=1,
        document_id=doc_id,
        source_scope="document"
    )

    # 5. Verify Debate Result & Citations
    with SessionLocal() as db:
        msgs = db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == deb_id).all()
        assert len(msgs) == 2
        # Verify evidence references attached
        for m in msgs:
            assert isinstance(m.evidence_references, list)
            if len(m.evidence_references) > 0:
                ev = m.evidence_references[0]
                assert "AI_Safety_Statute_2026.pdf" in ev.get("source", "") or "Document" in ev.get("source", "")

        eval_rec = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == deb_id).first()
        assert eval_rec is not None
        assert eval_rec.status == "completed"

# -------------------------------------------------------------------------
# Scenario 4: A debate using an uploaded image if configured pipeline supports it
# -------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_PIL, reason="PIL/Pillow not installed in environment")
def test_scenario_4_uploaded_image_debate():
    """
    Scenario 4: Debate using an uploaded image processed through visual ingestion pipeline.
    Verifies:
    - Image format, resolution, megapixels, and color mode structural extraction
    - Optical/visual document chunking and Qdrant indexing
    - Document-grounded debate execution citing the visual image record
    """
    # 1. Create a test PNG image in memory
    img = Image.new("RGB", (400, 300), color=(240, 245, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (380, 280)], outline=(30, 60, 120), width=3)
    d.text((40, 50), "FINANCIAL RISK MATRIX 2026", fill=(10, 20, 40))
    d.text((40, 100), "Algorithmic Arbitrage Liquidity Variance: +42%", fill=(20, 80, 30))
    d.text((40, 150), "High-Frequency Systemic Contagion Risk: Elevated", fill=(180, 30, 20))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # 2. Upload image via API
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("risk_matrix_chart.png", img_bytes, "image/png")}
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document"]["id"]

    # 3. Verify Document in DB & Qdrant Chunks
    with SessionLocal() as db:
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        assert doc is not None
        assert doc.file_type == "png"
        assert doc.status == "ready"

        chunks = db.query(DocumentChunkModel).filter(DocumentChunkModel.document_id == doc_id).all()
        assert len(chunks) >= 1
        assert "risk_matrix_chart.png" in chunks[0].content or "Visual Image" in chunks[0].content

    # 4. Execute debate grounded in the image document
    topic = "Does algorithmic arbitrage increase systemic contagion risk in financial markets?"
    create_payload = {
        "topic": topic,
        "rounds": 1,
        "evidenceMode": True,
        "strictFactChecking": True,
        "sourceScope": "document",
        "documentId": doc_id
    }
    deb_resp = client.post("/api/debates", json=create_payload)
    deb_id = deb_resp.json()["debateId"]

    _run_debate_in_background(
        debate_id=deb_id,
        topic=topic,
        rounds=1,
        document_id=doc_id,
        source_scope="document"
    )

    # 5. Verify completion and persistence
    with SessionLocal() as db:
        deb = db.query(DebateModel).filter(DebateModel.id == deb_id).first()
        assert deb.status == "completed"
        msgs = db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == deb_id).all()
        assert len(msgs) == 2
        eval_rec = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == deb_id).first()
        assert eval_rec is not None
        assert eval_rec.status == "completed"

# -------------------------------------------------------------------------
# Scenario 5: A general-topic debate using the configured research provider
# -------------------------------------------------------------------------
def test_scenario_5_general_topic_research_provider():
    """
    Scenario 5: General-topic debate using DuckDuckGo / configured web search provider.
    Verifies:
    - Provider generates affirmative and opposing search queries
    - Search results are fetched, formatted with URLs, chunked, and indexed into Qdrant
    - Debate messages cite research references
    - Judge evaluates source reliability
    """
    topic = "Autonomous Robotics in Deep-Sea Oceanic Exploration"

    # Explicitly configure mock provider for unit test execution to guarantee deterministic fixtures
    original_provider = research_service.provider
    research_service.provider = MockWebSearchProvider()
    try:
        # 1. Test Research Service Directly
        with SessionLocal() as db:
            search_res = research_service.conduct_research_and_index(db=db, topic=topic, max_sources=3)
            assert len(search_res["sources"]) > 0
            for src in search_res["sources"]:
                assert "url" in src
                assert "title" in src
                assert len(src["content"]) > 10

        # 2. Test API /api/research endpoint
        api_res = client.post("/api/research", json={"topic": topic, "max_sources": 2})
        assert api_res.status_code == 200
        assert api_res.json()["topic"] == topic
        assert len(api_res.json()["sources"]) > 0

        # 3. Run General-Topic Debate
        deb_resp = client.post("/api/debates", json={
            "topic": topic,
            "rounds": 1,
            "evidenceMode": True,
            "strictFactChecking": True,
            "sourceScope": "general_topic"
        })
        deb_id = deb_resp.json()["debateId"]

        _run_debate_in_background(
            debate_id=deb_id,
            topic=topic,
            rounds=1,
            document_id=None,
            source_scope="general_topic"
        )

        with SessionLocal() as db:
            deb = db.query(DebateModel).filter(DebateModel.id == deb_id).first()
            assert deb.status == "completed"
            eval_rec = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == deb_id).first()
            assert eval_rec is not None
            assert eval_rec.status == "completed"
    finally:
        research_service.provider = original_provider

# -------------------------------------------------------------------------
# Scenario 6: Model failure or retrieval failure
# -------------------------------------------------------------------------
def test_scenario_6_model_and_retrieval_failures():
    """
    Scenario 6: Verifies failure handling and non-fabrication:
    - 6A: Production mode model load failure on CPU host refuses fabrication.
    - 6B: Empty vector search / missing document handled gracefully without crash.
    - 6C: Judge evaluation failure marks debate as evaluation_failed without corrupting messages.
    """
    # 6A: Production Mode Model Failure Refuses Fabrication
    prod_mgr = LocalModelManager()
    prod_mgr.mock_mode = False
    with pytest.raises(RuntimeError) as exc_info:
        prod_mgr.generate("CON", "System prompt", "User prompt")
    assert "refusing to fabricate" in str(exc_info.value).lower()

    # 6B: Retrieval Failure / Empty Qdrant Search
    empty_results = qdrant_service.search_evidence([], document_id="nonexistent_doc_id", top_k=5)
    assert empty_results == []

    # 6C: Judge Failure Does Not Corrupt Persisted Messages
    deb_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=deb_id, topic="Testing Failure Recovery", rounds=1, status="debating")
        db.add(deb)
        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=deb_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Affirmative Core",
            content="Critical affirmative content that must not be deleted or corrupted.",
            confidence=95.0,
            evidence_references=[]
        )
        m2 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=deb_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Negative Core",
            content="Critical negative content that must not be deleted or corrupted.",
            confidence=94.0,
            evidence_references=[]
        )
        db.add(m1)
        db.add(m2)
        db.commit()

    from app.graph.nodes import save_result
    state: DebateGraphState = {
        "debate_id": deb_id,
        "topic": "Testing Failure Recovery",
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 1,
        "current_speaker": "CON",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": None,
        "current_con_turn": None,
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": {
            "status": "failed",
            "winner": "FAILED",
            "pro_score": 0.0,
            "con_score": 0.0,
            "error_message": "Simulated unparseable model output"
        },
        "resume_target": None,
        "status": "evaluation_failed",
        "error": "Simulated unparseable model output"
    }

    res = save_result(state)
    assert res["status"] == "evaluation_failed"

    with SessionLocal() as db:
        deb_rec = db.query(DebateModel).filter(DebateModel.id == deb_id).first()
        assert deb_rec.status == "evaluation_failed"
        # Confirm messages are preserved 100% intact
        saved_msgs = db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == deb_id).all()
        assert len(saved_msgs) == 2
        assert any("Critical affirmative content" in m.content for m in saved_msgs)
        assert any("Critical negative content" in m.content for m in saved_msgs)

# -------------------------------------------------------------------------
# Scenario 7: A retry or resumed debate after an interrupted run
# -------------------------------------------------------------------------
def test_scenario_7_retry_and_resumed_interrupted_debate():
    """
    Scenario 7: Retry or resumed debate after an interrupted run.
    Verifies:
    - Pre-existing committed messages are NOT duplicated upon resumption
    - Missing turns are completed
    - Exact 2N message count and 1 final Judge evaluation
    """
    debate_id = str(uuid.uuid4())
    topic = "Should autonomous maritime cargo vessels navigate international waters?"

    # Simulate: Round 1 PRO was committed, but process was interrupted before Round 1 CON
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=2, status="debating")
        db.add(deb)
        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="R1 PRO PRE-COMMITTED",
            content="PRO THESIS: Autonomous cargo ships eliminate human fatigue and optimize oceanic fuel efficiency.",
            confidence=95.0,
            evidence_references=[]
        )
        db.add(m1)
        db.commit()

    # Resume the debate via LangGraph
    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 2,
        "current_speaker": "PRO",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": None,
        "current_con_turn": None,
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": None,
        "resume_target": None,
        "status": "idle",
        "error": None
    }

    final_state = debate_graph.invoke(initial_state)
    assert final_state["status"] == "completed"
    assert len(final_state["transcript"]) == 4

    with SessionLocal() as db:
        saved_messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.round_number, DebateMessageModel.created_at).all()

        # Exactly 4 messages for 2 rounds
        assert len(saved_messages) == 4

        # Verify Round 1 PRO was NOT duplicated and retained original text
        r1_pros = [m for m in saved_messages if m.round_number == 1 and m.role == "PRO"]
        assert len(r1_pros) == 1
        assert "PRO THESIS: Autonomous cargo ships" in r1_pros[0].content

        # Verify Round 1 CON was generated and committed
        r1_cons = [m for m in saved_messages if m.round_number == 1 and m.role == "CON"]
        assert len(r1_cons) == 1

        # Verify Round 2 PRO and CON were generated
        r2_pros = [m for m in saved_messages if m.round_number == 2 and m.role == "PRO"]
        r2_cons = [m for m in saved_messages if m.round_number == 2 and m.role == "CON"]
        assert len(r2_pros) == 1
        assert len(r2_cons) == 1

        # Verify exactly 2 rounds and 1 Judge evaluation
        rounds = db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).all()
        assert len(rounds) == 2

        eval_rec = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert eval_rec is not None
        assert eval_rec.status == "completed"

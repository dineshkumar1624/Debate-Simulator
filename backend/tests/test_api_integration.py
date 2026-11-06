import uuid
import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.llm.model_manager import local_model_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db_and_mock():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield

def test_api_health_endpoints():
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert res2.json()["service"] == "AI Debate Simulator"

def test_api_research_endpoint():
    payload = {
        "topic": "Should autonomous vehicles be permitted without commercial driver licenses?",
        "max_sources": 3
    }
    resp = client.post("/api/research", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == payload["topic"]
    assert "sources" in data
    assert "indexedChunks" in data
    assert "message" in data
    if len(data["sources"]) > 0:
        assert data["indexedChunks"] > 0
        assert "evidence" in data["message"].lower() or "indexed" in data["message"].lower()
    else:
        assert data["indexedChunks"] == 0
        assert "unavailable" in data["message"].lower() or "no verified" in data["message"].lower()
    # Confirm no synthetic fallback URLs are present
    for src in data["sources"]:
        assert "policy-archive.org" not in src["url"]
        assert "critique-quarterly.org" not in src["url"]

def test_api_debate_lifecycle_and_polling():
    create_payload = {
        "topic": "Universal Basic Income: Economic Feasibility and Labor Impact",
        "rounds": 1,
        "evidenceMode": True,
        "strictFactChecking": True,
        "sourceScope": "general_topic"
    }

    create_resp = client.post("/api/debates", json=create_payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert "debateId" in created
    debate_id = created["debateId"]
    assert created["status"] == "debating"

    # Status polling endpoint
    status_resp = client.get(f"/api/debates/{debate_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["debateId"] == debate_id
    assert status_data["totalRounds"] == 1

    # Full debate retrieval
    get_resp = client.get(f"/api/debates/{debate_id}")
    assert get_resp.status_code == 200
    deb_data = get_resp.json()
    assert deb_data["id"] == debate_id
    assert deb_data["topic"] == create_payload["topic"]
    assert "rounds" in deb_data

    # List debates
    list_resp = client.get("/api/debates")
    assert list_resp.status_code == 200
    deb_ids = [d["id"] for d in list_resp.json()]
    assert debate_id in deb_ids

def test_api_not_found_standard_errors():
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/debates/{fake_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Debate not found"

    resp2 = client.get(f"/api/debates/{fake_id}/messages")
    assert resp2.status_code == 404
    assert resp2.json()["detail"] == "Debate not found"

def test_api_debate_execution_messages_and_judge_result():
    from app.routes.debates import _run_debate_in_background
    create_payload = {
        "topic": "Should algorithmic auditing be legally mandated for financial algorithms?",
        "rounds": 1,
        "evidenceMode": True,
        "strictFactChecking": True,
        "sourceScope": "general_topic"
    }
    create_resp = client.post("/api/debates", json=create_payload)
    assert create_resp.status_code == 200
    deb_id = create_resp.json()["debateId"]

    # Run the background workflow synchronously for test verification
    _run_debate_in_background(
        debate_id=deb_id,
        topic=create_payload["topic"],
        rounds=1,
        document_id=None,
        source_scope="general_topic"
    )

    # 1. Verify status is completed
    st = client.get(f"/api/debates/{deb_id}/status")
    assert st.status_code == 200
    assert st.json()["status"] == "completed"

    # 2. Verify ordered messages (exactly 2 for 1 round: PRO then CON)
    msg_resp = client.get(f"/api/debates/{deb_id}/messages")
    assert msg_resp.status_code == 200
    turns = msg_resp.json()
    assert len(turns) == 2
    assert turns[0]["role"] == "PRO"
    assert turns[1]["role"] == "CON"

    # 3. Verify final Judge result
    res_resp = client.get(f"/api/debates/{deb_id}/result")
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert "pro_score" in res_data
    assert "con_score" in res_data
    assert res_data["winner"] in ["PRO", "CON", "INCONCLUSIVE"]

    # 4. Verify synthesis
    syn_resp = client.get(f"/api/debates/{deb_id}/synthesis")
    assert syn_resp.status_code == 200
    syn_data = syn_resp.json()
    assert "summary" in syn_data
    assert "balancedVerdict" in syn_data

def test_api_duplicate_start_prevention():
    from app.models.debate import DebateModel
    create_payload = {
        "topic": "Concurrency and duplicate start prevention test",
        "rounds": 1,
        "evidenceMode": True,
        "sourceScope": "general_topic"
    }
    create_resp = client.post("/api/debates", json=create_payload)
    deb_id = create_resp.json()["debateId"]

    # Explicitly ensure status is 'debating' to simulate in-flight execution
    with SessionLocal() as db:
        deb = db.query(DebateModel).filter(DebateModel.id == deb_id).first()
        if deb:
            deb.status = "debating"
            db.commit()

    # Attempt duplicate start while already debating
    retry_resp = client.post(f"/api/debates/{deb_id}/start")
    assert retry_resp.status_code == 200
    data = retry_resp.json()
    assert data["status"] == "debating"
    assert "already in progress" in data["message"].lower()

def test_api_document_upload_and_tracking():
    text_payload = {
        "title": "Quantum Algorithm Governance Framework",
        "content": "Quantum algorithms require specialized encryption defenses against Shor's algorithm."
    }
    doc_resp = client.post("/api/documents/text", json=text_payload)
    assert doc_resp.status_code == 200
    doc_data = doc_resp.json()["document"]
    doc_id = doc_data["id"]
    assert doc_data["name"] == text_payload["title"]

    # Verify retrieval
    get_doc = client.get(f"/api/documents/{doc_id}")
    assert get_doc.status_code == 200
    assert get_doc.json()["id"] == doc_id
    assert get_doc.json()["name"] == text_payload["title"]

def test_api_file_upload_multipart_and_validations(tmp_path):
    # 1. Valid file upload via multipart form-data
    test_content = b"Renewable energy grids require battery storage and transmission investments."
    files = {"file": ("energy_policy.txt", test_content, "text/plain")}
    resp = client.post("/api/documents/upload", files=files)
    assert resp.status_code == 200
    uploaded_doc = resp.json()["document"]
    assert uploaded_doc["name"] == "energy_policy.txt"
    assert uploaded_doc["fileType"] == "txt"

    # 2. Unsupported extension rejection (HTTP 400)
    bad_files = {"file": ("malicious.exe", b"binary content", "application/octet-stream")}
    bad_resp = client.post("/api/documents/upload", files=bad_files)
    assert bad_resp.status_code == 400
    assert "unsupported file format" in bad_resp.json()["detail"].lower()

    # 3. Empty file rejection (HTTP 400)
    empty_files = {"file": ("empty.txt", b"", "text/plain")}
    empty_resp = client.post("/api/documents/upload", files=empty_files)
    assert empty_resp.status_code == 400
    assert "empty" in empty_resp.json()["detail"].lower()


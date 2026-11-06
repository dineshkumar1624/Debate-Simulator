import uuid
import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, JudgeEvaluationModel
from app.llm.model_manager import local_model_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield

def test_api_create_and_query_debate():
    # 1. Create debate
    resp = client.post("/api/debates", json={
        "topic": "Should autonomous algorithms decide sentencing?",
        "rounds": 1,
        "evidenceMode": True
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "debateId" in data
    debate_id = data["debateId"]

    # 2. Get status
    status_resp = client.get(f"/api/debates/{debate_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["debateId"] == debate_id
    assert status_data["totalRounds"] == 1

    # 3. Get full session
    session_resp = client.get(f"/api/debates/{debate_id}")
    assert session_resp.status_code == 200
    session_data = session_resp.json()
    assert session_data["id"] == debate_id
    assert session_data["topic"] == "Should autonomous algorithms decide sentencing?"

def test_message_ordering_persistence():
    debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic="Persistence Order Test", rounds=1, status="completed")
        db.add(deb)
        
        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Pro Arg",
            content="Content 1"
        )
        m2 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Con Arg",
            content="Content 2"
        )
        db.add(m1)
        db.add(m2)
        db.commit()

    resp = client.get(f"/api/debates/{debate_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "PRO"
    assert messages[1]["role"] == "CON"

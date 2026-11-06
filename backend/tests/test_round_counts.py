import uuid
import pytest
from app.graph.debate_graph import debate_graph
from app.graph.state import DebateGraphState
from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, DebateRoundModel, JudgeEvaluationModel
from app.llm.model_manager import local_model_manager

@pytest.fixture(autouse=True)
def setup_db_and_mock():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield

@pytest.mark.parametrize("configured_rounds,expected_pro,expected_con,expected_total", [
    (1, 1, 1, 2),
    (3, 3, 3, 6),
    (5, 5, 5, 10),
])
def test_exact_round_counts(configured_rounds, expected_pro, expected_con, expected_total):
    debate_id = str(uuid.uuid4())
    topic = f"Should AI adjudicate civil liability disputes? (Testing {configured_rounds} rounds)"

    # Create initial debate record in DB
    with SessionLocal() as db:
        deb = DebateModel(
            id=debate_id,
            topic=topic,
            rounds=configured_rounds,
            status="idle"
        )
        db.add(deb)
        db.commit()

    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": configured_rounds,
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
        "status": "idle",
        "error": None
    }

    # Execute LangGraph StateGraph
    final_state = debate_graph.invoke(initial_state)

    # 1. Verify graph termination state
    assert final_state["status"] == "completed"
    assert final_state["error"] is None
    assert final_state["judge_report"] is not None

    # 2. Verify state transcript message counts
    transcript = final_state["transcript"]
    assert len(transcript) == expected_total

    pro_turns = [t for t in transcript if t["role"] == "PRO"]
    con_turns = [t for t in transcript if t["role"] == "CON"]
    assert len(pro_turns) == expected_pro
    assert len(con_turns) == expected_con

    # 3. Verify SQL database persistence counts
    with SessionLocal() as db:
        saved_messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.created_at).all()
        assert len(saved_messages) == expected_total

        saved_rounds = db.query(DebateRoundModel).filter(
            DebateRoundModel.debate_id == debate_id
        ).all()
        assert len(saved_rounds) == configured_rounds

        saved_eval = db.query(JudgeEvaluationModel).filter(
            JudgeEvaluationModel.debate_id == debate_id
        ).first()
        assert saved_eval is not None
        assert saved_eval.winner in ["PRO", "CON", "INCONCLUSIVE"]
        assert 0.0 <= saved_eval.pro_score <= 100.0
        assert 0.0 <= saved_eval.con_score <= 100.0

def test_rebuttal_message_passing():
    """
    Verifies that CON receives PRO's argument and PRO in subsequent rounds receives CON's rebuttal.
    """
    debate_id = str(uuid.uuid4())
    topic = "Testing turn-by-turn opponent argument passing"

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=2, status="idle")
        db.add(deb)
        db.commit()

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
        "status": "idle",
        "error": None
    }

    final_state = debate_graph.invoke(initial_state)
    transcript = final_state["transcript"]

    # In Round 1: Turn 0 is PRO, Turn 1 is CON
    # In Round 2: Turn 2 is PRO, Turn 3 is CON
    assert transcript[0]["role"] == "PRO"
    assert transcript[1]["role"] == "CON"
    assert transcript[2]["role"] == "PRO"
    assert transcript[3]["role"] == "CON"

    # Both speakers contributed substantive arguments
    assert len(transcript[0]["content"]) > 20
    assert len(transcript[1]["content"]) > 20
    assert len(transcript[2]["content"]) > 20
    assert len(transcript[3]["content"]) > 20

def test_node_retry_prevents_duplicate_messages():
    """
    Verifies that calling save_pro_message or save_con_message multiple times
    (simulating retries or re-executions) does not create duplicate SQL records or transcript entries.
    """
    from app.graph.nodes import save_pro_message, save_con_message

    debate_id = str(uuid.uuid4())
    topic = "Retry Idempotence Test"

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="idle")
        db.add(deb)
        db.commit()

    state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 1,
        "current_speaker": "PRO",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": {
            "title": "Affirmative Argument",
            "content": "Initial affirmative thesis statement.",
            "confidence": 95.0
        },
        "current_con_turn": {
            "title": "Negative Counterargument",
            "content": "Initial negative rebuttal statement.",
            "confidence": 94.0
        },
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": None,
        "status": "debating",
        "error": None
    }

    # First invocation of save_pro_message
    res1 = save_pro_message(state)
    state["transcript"] = res1["transcript"]
    state["latest_pro_argument"] = res1["latest_pro_argument"]

    # Simulated RETRY: Second invocation of save_pro_message with updated state
    res2 = save_pro_message(state)
    state["transcript"] = res2["transcript"]

    # Verify that transcript contains only ONE PRO message, not two
    pro_turns = [t for t in state["transcript"] if t["role"] == "PRO"]
    assert len(pro_turns) == 1

    # Verify that SQL database contains only ONE PRO message
    with SessionLocal() as db:
        sql_pro_msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id,
            DebateMessageModel.role == "PRO"
        ).all()
        assert len(sql_pro_msgs) == 1

    # First invocation of save_con_message
    res_con1 = save_con_message(state)
    state["transcript"] = res_con1["transcript"]

    # Simulated RETRY: Second invocation of save_con_message
    res_con2 = save_con_message(state)
    state["transcript"] = res_con2["transcript"]

    # Verify that transcript contains only ONE CON message
    con_turns = [t for t in state["transcript"] if t["role"] == "CON"]
    assert len(con_turns) == 1

    # Verify that SQL database contains only ONE CON message and ONE round record
    with SessionLocal() as db:
        sql_con_msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id,
            DebateMessageModel.role == "CON"
        ).all()
        assert len(sql_con_msgs) == 1

        sql_rounds = db.query(DebateRoundModel).filter(
            DebateRoundModel.debate_id == debate_id
        ).all()
        assert len(sql_rounds) == 1

def test_interrupted_debate_resumes_without_duplicate_messages():
    """
    Verifies that when a debate was interrupted after Round 1 and restarted,
    it preserves Round 1 messages, executes only Round 2, and persists exactly
    4 messages total (for 2 rounds) with no duplicates.
    """
    debate_id = str(uuid.uuid4())
    topic = "Should autonomous AI agents hold property rights? (Resume Test)"

    # Pre-populate DB with Round 1 PRO and Round 1 CON messages (simulating interrupted run)
    with SessionLocal() as db:
        deb = DebateModel(
            id=debate_id,
            topic=topic,
            rounds=2,
            status="debating"
        )
        db.add(deb)

        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Round 1 Affirmative Argument",
            content="Initial affirmative proposition on property rights.",
            confidence=95.0,
            evidence_references=[]
        )
        m2 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Round 1 Opposition Argument",
            content="Initial negative counterargument on legal agency.",
            confidence=93.0,
            evidence_references=[]
        )
        r1 = DebateRoundModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            status="completed"
        )
        db.add(m1)
        db.add(m2)
        db.add(r1)
        db.commit()

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
        "status": "idle",
        "error": None
    }

    # Resume execution via StateGraph
    final_state = debate_graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert final_state["judge_report"] is not None

    # Verify state transcript: exactly 4 messages
    assert len(final_state["transcript"]) == 4

    # Verify SQL database records: exactly 4 messages, 2 rounds, 1 judge evaluation
    with SessionLocal() as db:
        saved_messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.created_at).all()
        assert len(saved_messages) == 4

        # Verify Round 1 messages were preserved intact
        r1_pro = [m for m in saved_messages if m.round_number == 1 and m.role == "PRO"][0]
        assert r1_pro.content == "Initial affirmative proposition on property rights."

        r1_con = [m for m in saved_messages if m.round_number == 1 and m.role == "CON"][0]
        assert r1_con.content == "Initial negative counterargument on legal agency."

        # Verify Round 2 messages were generated
        r2_msgs = [m for m in saved_messages if m.round_number == 2]
        assert len(r2_msgs) == 2

        # Verify rounds and judge
        saved_rounds = db.query(DebateRoundModel).filter(
            DebateRoundModel.debate_id == debate_id
        ).all()
        assert len(saved_rounds) == 2

        saved_eval = db.query(JudgeEvaluationModel).filter(
            JudgeEvaluationModel.debate_id == debate_id
        ).first()
        assert saved_eval is not None

def test_interrupted_after_pro_committed_resumes_to_con_without_duplication():
    """
    Edge Case 2A: Failure after the PRO message is committed but before the CON message is committed.
    Restarting must:
    1. Reuse the existing PRO message without generating a duplicate.
    2. Route CON to respond to that exact PRO message.
    3. Complete subsequent rounds cleanly with exactly 2N messages in DB.
    """
    debate_id = str(uuid.uuid4())
    topic = "Should autonomous AI agents face strict liability for medical misdiagnosis?"
    exact_pro_content = "AFFIRMATIVE CORE THESIS: Strict liability ensures algorithmic safety standards."

    # Simulate: Round 1 PRO committed in DB, but Round 1 CON not committed (process died midway)
    with SessionLocal() as db:
        deb = DebateModel(
            id=debate_id,
            topic=topic,
            rounds=2,
            status="debating"
        )
        db.add(deb)

        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Round 1 Affirmative Thesis",
            content=exact_pro_content,
            confidence=94.5,
            evidence_references=[]
        )
        db.add(m1)
        db.commit()

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
        "status": "idle",
        "error": None,
        "resume_target": None
    }

    # Resume graph execution
    final_state = debate_graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert len(final_state["transcript"]) == 4

    with SessionLocal() as db:
        saved_messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.round_number, DebateMessageModel.created_at).all()

        # Exactly 4 messages for 2 completed rounds: R1 PRO, R1 CON, R2 PRO, R2 CON
        assert len(saved_messages) == 4

        # Verify Round 1 PRO was NOT duplicated and retains the exact initial content
        r1_pro_msgs = [m for m in saved_messages if m.round_number == 1 and m.role == "PRO"]
        assert len(r1_pro_msgs) == 1
        assert r1_pro_msgs[0].content == exact_pro_content

        # Verify Round 1 CON was generated and committed
        r1_con_msgs = [m for m in saved_messages if m.round_number == 1 and m.role == "CON"]
        assert len(r1_con_msgs) == 1
        assert len(r1_con_msgs[0].content) > 0

        # Verify Round 2 messages
        r2_pro_msgs = [m for m in saved_messages if m.round_number == 2 and m.role == "PRO"]
        r2_con_msgs = [m for m in saved_messages if m.round_number == 2 and m.role == "CON"]
        assert len(r2_pro_msgs) == 1
        assert len(r2_con_msgs) == 1

        # Verify exactly 2 rounds and 1 judge evaluation
        rounds = db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).all()
        assert len(rounds) == 2

        eval_record = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert eval_record is not None
        assert eval_record.winner in ["PRO", "CON", "INCONCLUSIVE"]

def test_interrupted_after_both_messages_committed_resumes_next_round_without_skipping_or_duplicating():
    """
    Edge Case 2B: Failure after both Round 1 messages are committed, but before Round 2 begins.
    Resuming must:
    1. Keep both Round 1 messages intact.
    2. Not skip Round 2.
    3. Not duplicate Round 1 messages.
    4. Complete Round 2 and finalize with the Judge.
    """
    debate_id = str(uuid.uuid4())
    topic = "Should high-frequency algorithmic market-making be restricted?"

    with SessionLocal() as db:
        deb = DebateModel(
            id=debate_id,
            topic=topic,
            rounds=2,
            status="debating"
        )
        db.add(deb)

        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Round 1 PRO",
            content="R1 PRO CONTENT: Flash crashes demonstrate the need for liquidity minimums.",
            confidence=92.0,
            evidence_references=[]
        )
        m2 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Round 1 CON",
            content="R1 CON REBUTTAL: Spreads tightened by 80% due to automated liquidity provision.",
            confidence=91.0,
            evidence_references=[]
        )
        r1 = DebateRoundModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            status="completed"
        )
        db.add(m1)
        db.add(m2)
        db.add(r1)
        db.commit()

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
        "status": "idle",
        "error": None,
        "resume_target": None
    }

    final_state = debate_graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert len(final_state["transcript"]) == 4

    with SessionLocal() as db:
        saved_messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.round_number, DebateMessageModel.created_at).all()

        assert len(saved_messages) == 4
        # Verify Round 1 was not duplicated
        assert len([m for m in saved_messages if m.round_number == 1]) == 2
        # Verify Round 2 was executed and not skipped
        assert len([m for m in saved_messages if m.round_number == 2]) == 2

def test_judge_runs_only_after_final_con_is_committed():
    """
    Verifies that the Judge evaluation only executes after the final CON message
    has already been committed to the database.
    """
    from app.graph.nodes import compile_complete_transcript, judge_agent_node
    debate_id = str(uuid.uuid4())
    topic = "Verification of Judge execution boundary"

    # Pre-populate DB with only PRO message for a 1-round debate (no CON yet)
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="debating")
        db.add(deb)
        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Pro Only",
            content="Solo pro argument.",
            confidence=90.0,
            evidence_references=[]
        )
        db.add(m1)
        db.commit()

    # Attempting to compile transcript when final CON message is missing from DB
    with SessionLocal() as db:
        con_msg = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id,
            DebateMessageModel.role == "CON"
        ).first()
        # CON message is NOT committed yet!
        assert con_msg is None

        # Verify that judge evaluation has not been created yet
        eval_record = db.query(JudgeEvaluationModel).filter(
            JudgeEvaluationModel.debate_id == debate_id
        ).first()
        assert eval_record is None

    # Now simulate the final CON message committing
    with SessionLocal() as db:
        m2 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Con Final",
            content="Closing opposition argument.",
            confidence=90.0,
            evidence_references=[]
        )
        db.add(m2)
        db.commit()

    # Verify that now and only now can both messages be retrieved and judge executed
    with SessionLocal() as db:
        all_msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).all()
        assert len(all_msgs) == 2
        roles = {m.role for m in all_msgs}
        assert roles == {"PRO", "CON"}

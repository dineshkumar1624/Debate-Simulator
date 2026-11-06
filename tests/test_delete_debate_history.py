import unittest
import urllib.request
import urllib.parse
import json
import sqlite3
import uuid
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api"

class TestDeleteDebateHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            req = urllib.request.urlopen(f"{BASE_URL}/health", timeout=5)
            assert req.status == 200
        except Exception as e:
            raise RuntimeError(f"Backend not responding at {BASE_URL}: {e}")

    def _insert_dummy_debate(self, topic: str, doc_id: str = None) -> str:
        debate_id = f"test-del-{uuid.uuid4().hex[:8]}"
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Insert debate
        cur.execute(
            """
            INSERT INTO debates (id, topic, status, rounds, created_at, updated_at, document_id)
            VALUES (?, ?, 'completed', 1, ?, ?, ?)
            """,
            (debate_id, topic, now, now, doc_id)
        )

        # Insert round
        round_id = f"round-{uuid.uuid4().hex[:8]}"
        cur.execute(
            """
            INSERT INTO debate_rounds (id, debate_id, round_number, status, created_at)
            VALUES (?, ?, 1, 'completed', ?)
            """,
            (round_id, debate_id, now)
        )

        # Insert message
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        cur.execute(
            """
            INSERT INTO debate_messages (id, debate_id, round_number, speaker, role, content, confidence, created_at)
            VALUES (?, ?, 1, 'DEBATER_A', 'PRO', 'Test claim content', 95.0, ?)
            """,
            (msg_id, debate_id, now)
        )

        # Insert evaluation
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"
        cur.execute(
            """
            INSERT INTO judge_evaluations (id, debate_id, pro_score, con_score, winner, status, created_at)
            VALUES (?, ?, 85.0, 75.0, 'PRO', 'completed', ?)
            """,
            (eval_id, debate_id, now)
        )

        conn.commit()
        conn.close()
        return debate_id

    def test_01_delete_single_attempt_by_id(self):
        """1. Verify DELETE /api/history/{debateId} deletes single debate attempt and its children."""
        test_topic = f"Temporary test debate attempt for deletion {uuid.uuid4().hex[:6]}"
        debate_id = self._insert_dummy_debate(test_topic)

        # Verify it exists in DB
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        self.assertEqual(cur.execute("SELECT count(*) FROM debates WHERE id = ?", (debate_id,)).fetchone()[0], 1)
        self.assertEqual(cur.execute("SELECT count(*) FROM judge_evaluations WHERE debate_id = ?", (debate_id,)).fetchone()[0], 1)
        conn.close()

        # Send DELETE request
        req = urllib.request.Request(f"{BASE_URL}/history/{debate_id}", method="DELETE")
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["deletedId"], debate_id)

        # Verify deleted from DB and child records cascaded
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        self.assertEqual(cur.execute("SELECT count(*) FROM debates WHERE id = ?", (debate_id,)).fetchone()[0], 0)
        self.assertEqual(cur.execute("SELECT count(*) FROM debate_rounds WHERE debate_id = ?", (debate_id,)).fetchone()[0], 0)
        self.assertEqual(cur.execute("SELECT count(*) FROM debate_messages WHERE debate_id = ?", (debate_id,)).fetchone()[0], 0)
        self.assertEqual(cur.execute("SELECT count(*) FROM judge_evaluations WHERE debate_id = ?", (debate_id,)).fetchone()[0], 0)
        conn.close()
        print(f"PASS [Test 1]: Successfully deleted attempt {debate_id} with full cascade")

    def test_02_delete_attempt_not_found(self):
        """2. Verify DELETE /api/history/{debateId} returns 404 for non-existent ID."""
        req = urllib.request.Request(f"{BASE_URL}/history/non-existent-uuid-99999", method="DELETE")
        try:
            urllib.request.urlopen(req)
            self.fail("Should have raised HTTPError 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
        print("PASS [Test 2]: Non-existent debate deletion correctly returned HTTP 404")

    def test_03_delete_entire_debate_topic_group(self):
        """3. Verify DELETE /api/history/group deletes all attempts belonging to a topic group."""
        test_topic = f"Group topic for deletion test {uuid.uuid4().hex[:6]}"
        id1 = self._insert_dummy_debate(test_topic)
        id2 = self._insert_dummy_debate(test_topic)

        # Verify 2 attempts exist in DB
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        self.assertEqual(cur.execute("SELECT count(*) FROM debates WHERE id IN (?, ?)", (id1, id2)).fetchone()[0], 2)
        conn.close()

        # Send DELETE request with debateIds
        payload = json.dumps({"debateIds": [id1, id2], "topic": test_topic}).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/history/group",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="DELETE"
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["deletedCount"], 2)

        # Verify all debates in group are deleted
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        self.assertEqual(cur.execute("SELECT count(*) FROM debates WHERE id IN (?, ?)", (id1, id2)).fetchone()[0], 0)
        conn.close()
        print(f"PASS [Test 3]: Successfully deleted topic group with {data['deletedCount']} attempts")

    def test_04_debates_alias_delete(self):
        """4. Verify DELETE /api/debates/{debateId} endpoint alias works identically."""
        test_topic = f"Debates alias delete test {uuid.uuid4().hex[:6]}"
        debate_id = self._insert_dummy_debate(test_topic)

        req = urllib.request.Request(f"{BASE_URL}/debates/{debate_id}", method="DELETE")
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["deletedId"], debate_id)
        print(f"PASS [Test 4]: Verified /debates/{debate_id} alias cleanly deletes record")

    def test_05_batch_delete_page_debates(self):
        """5. Verify DELETE /api/history/batch deletes a batch of debates across different topics on a page."""
        topic_a = f"Page Topic Alpha {uuid.uuid4().hex[:6]}"
        topic_b = f"Page Topic Beta {uuid.uuid4().hex[:6]}"
        id1 = self._insert_dummy_debate(topic_a)
        id2 = self._insert_dummy_debate(topic_a)
        id3 = self._insert_dummy_debate(topic_b)

        # Verify 3 debates exist in DB
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        self.assertEqual(cur.execute("SELECT count(*) FROM debates WHERE id IN (?, ?, ?)", (id1, id2, id3)).fetchone()[0], 3)
        conn.close()

        # Send batch DELETE request
        payload = json.dumps({"debateIds": [id1, id2, id3]}).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/history/batch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="DELETE"
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["deletedCount"], 3)

        # Verify all debates in batch are deleted
        conn = sqlite3.connect("debate_simulator.db")
        cur = conn.cursor()
        self.assertEqual(cur.execute("SELECT count(*) FROM debates WHERE id IN (?, ?, ?)", (id1, id2, id3)).fetchone()[0], 0)
        conn.close()
        print(f"PASS [Test 5]: Successfully batch deleted {data['deletedCount']} debates across topics on a page")

if __name__ == "__main__":
    unittest.main()


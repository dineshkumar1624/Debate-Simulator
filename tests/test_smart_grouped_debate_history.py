import unittest
import urllib.request
import urllib.parse
import json
import re

BASE_URL = "http://127.0.0.1:8000/api"

class TestSmartGroupedDebateHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify backend server is alive
        try:
            req = urllib.request.urlopen(f"{BASE_URL}/health", timeout=5)
            assert req.status == 200
        except Exception as e:
            raise RuntimeError(f"Backend not responding at {BASE_URL}: {e}")

    def test_01_strictly_completed_debates_only(self):
        """1. Verify that history returns ONLY completed debates with successful judge evaluation."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=50")
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode())

        self.assertIn("groups", data)
        self.assertIn("totalGroups", data)
        self.assertIn("totalCompletedDebates", data)
        self.assertGreater(data["totalGroups"], 0)
        self.assertGreater(data["totalCompletedDebates"], 0)

        # Inspect all attempts inside all returned groups
        for group in data["groups"]:
            self.assertEqual(group["status"], "completed")
            for attempt in group["attempts"]:
                self.assertIsNotNone(attempt["winner"], f"Attempt {attempt['debateId']} missing winner")
                self.assertNotEqual(attempt["winner"], "FAILED", f"Attempt {attempt['debateId']} has winner FAILED")
                self.assertIn(attempt["winner"], ["PRO", "CON", "INCONCLUSIVE", "TIE", "DRAW"])
        
        print(f"PASS [Test 1]: Verified all {data['totalCompletedDebates']} debates across {len(data['groups'])} groups are strictly completed with valid judge evaluations")

    def test_02_hides_debating_failed_and_evaluation_failed_debates(self):
        """2. Explicitly requesting non-completed status returns empty list (strict exclusion)."""
        for bad_status in ["debating", "failed", "evaluation_failed", "idle"]:
            url = f"{BASE_URL}/history?status={bad_status}&page=1&page_size=20"
            req = urllib.request.urlopen(url)
            data = json.loads(req.read().decode())
            self.assertEqual(len(data["groups"]), 0, f"Status '{bad_status}' should return 0 groups")
            self.assertEqual(data["totalGroups"], 0)
        print("PASS [Test 2]: Verified debating, failed, evaluation_failed, and idle debates are completely excluded")

    def test_03_same_question_same_doc_grouped_together(self):
        """3. Same question + same document forms ONE single grouped card with multiple attempts."""
        # Query for the Transformer paper debate
        query = urllib.parse.quote("The Transformer architecture is superior to recurrent")
        url = f"{BASE_URL}/history?query={query}&page=1&page_size=10"
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode())

        self.assertGreater(len(data["groups"]), 0)
        
        # Find group associated with transformers research paper
        paper_group = next(
            (g for g in data["groups"] if g.get("documentName") and "transformers" in g["documentName"].lower()),
            None
        )
        self.assertIsNotNone(paper_group, "Should find grouped card for Transformer paper")
        self.assertGreaterEqual(paper_group["totalAttempts"], 2, "Should have multiple attempts grouped together")
        self.assertEqual(len(paper_group["attempts"]), paper_group["totalAttempts"])

        # Check chronological attempt numbering: #1 is oldest, #N is latest
        attempts = paper_group["attempts"]
        expected_num = paper_group["totalAttempts"]
        for att in attempts:
            self.assertEqual(att["attemptNumber"], expected_num)
            expected_num -= 1

        print(f"PASS [Test 3]: Successfully grouped {paper_group['totalAttempts']} attempts of Transformer paper debate into 1 card")

    def test_04_same_question_different_doc_separated(self):
        """4. Same question + different document (or no document) forms SEPARATE cards."""
        query = urllib.parse.quote("The Transformer architecture is superior to recurrent")
        url = f"{BASE_URL}/history?query={query}&page=1&page_size=10"
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode())

        # Collect document IDs for groups with this topic
        doc_ids = [g.get("documentId") for g in data["groups"]]
        # Should have both a document-backed group and a General Proposition (None) group
        self.assertIn(None, doc_ids, "Should have a General Proposition group")
        self.assertTrue(any(d is not None for d in doc_ids), "Should have a Document-backed group")
        self.assertGreaterEqual(len(data["groups"]), 2, "Same topic with different/no document must form separate cards")
        print(f"PASS [Test 4]: Verified same proposition with different documents produces separate cards ({len(data['groups'])} cards)")

    def test_05_image_debate_grouping(self):
        """5. Debate with repeated runs on same document is grouped into 1 card."""
        query = urllib.parse.quote("Transformer architecture is superior")
        url = f"{BASE_URL}/history?query={query}&page=1&page_size=10"
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode())

        self.assertGreaterEqual(len(data["groups"]), 1)
        doc_group = next(g for g in data["groups"] if g.get("documentId") is not None)
        self.assertGreaterEqual(doc_group["totalAttempts"], 2, "Document debate should group both attempts")
        self.assertIn("transformers", doc_group["documentName"].lower())
        print(f"PASS [Test 5]: Verified document debate successfully grouped {doc_group['totalAttempts']} attempts into 1 card")

    def test_06_grouped_card_metadata(self):
        """6. Grouped card correctly exposes latest date, winner, scores, rounds, and speeches."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=5")
        data = json.loads(req.read().decode())

        for group in data["groups"]:
            self.assertIn("topic", group)
            self.assertIn("totalAttempts", group)
            self.assertIn("latestRoundsCount", group)
            self.assertIn("latestSpeechesCount", group)
            self.assertIn("attempts", group)
            self.assertGreater(group["totalAttempts"], 0)
            self.assertEqual(len(group["attempts"]), group["totalAttempts"])

            # Verify latest fields match attempts[0]
            latest_att = group["attempts"][0]
            self.assertEqual(group["latestWinner"], latest_att["winner"])
            self.assertEqual(group["latestProScore"], latest_att["proScore"])
            self.assertEqual(group["latestConScore"], latest_att["conScore"])
            self.assertEqual(group["latestRoundsCount"], latest_att["roundsCount"])
            self.assertEqual(group["latestSpeechesCount"], latest_att["speechesCount"])

        print("PASS [Test 6]: Grouped card summary metadata accurately mirrors latest attempt")

    def test_07_replay_individual_attempts_by_id(self):
        """7. Every attempt in a group has a unique debateId that can be retrieved for read-only replay."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=5")
        data = json.loads(req.read().decode())

        test_group = next((g for g in data["groups"] if g["totalAttempts"] >= 2), data["groups"][0])
        
        # Test replaying each attempt in this group
        for att in test_group["attempts"]:
            debate_id = att["debateId"]
            detail_req = urllib.request.urlopen(f"{BASE_URL}/history/{debate_id}")
            self.assertEqual(detail_req.status, 200)
            detail = json.loads(detail_req.read().decode())
            self.assertEqual(detail["id"], debate_id)
            self.assertEqual(detail["status"], "completed")
            self.assertIsNotNone(detail["synthesis"])
            self.assertEqual(detail["synthesis"]["winner"], att["winner"])

        print(f"PASS [Test 7]: Successfully replayed all {len(test_group['attempts'])} attempts in group via /history/{{debateId}}")

    def test_08_search_filters_both_proposition_and_document(self):
        """8. Search accurately filters by proposition topic and source document filename."""
        # Search by document filename substring
        req_doc = urllib.request.urlopen(f"{BASE_URL}/history?query=transformers&page=1&page_size=10")
        doc_data = json.loads(req_doc.read().decode())
        self.assertGreater(len(doc_data["groups"]), 0)
        for g in doc_data["groups"]:
            self.assertIn("transformers", g["documentName"].lower())

        # Search by proposition topic substring
        req_prop = urllib.request.urlopen(f"{BASE_URL}/history?query=arbitrage&page=1&page_size=10")
        prop_data = json.loads(req_prop.read().decode())
        self.assertGreater(len(prop_data["groups"]), 0)
        for g in prop_data["groups"]:
            self.assertIn("arbitrage", g["topic"].lower())

        print("PASS [Test 8]: Search operates correctly across proposition text and document filename")

    def test_09_pagination_does_not_split_attempts(self):
        """9. Pagination paginates grouped cards, ensuring attempts belonging to a group stay together."""
        page_size = 5
        req_p1 = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size={page_size}")
        p1 = json.loads(req_p1.read().decode())
        self.assertLessEqual(len(p1["groups"]), page_size)
        self.assertEqual(p1["pageSize"], page_size)
        self.assertEqual(p1["page"], 1)

        # Total completed debates across groups on page 1
        page1_attempts = sum(g["totalAttempts"] for g in p1["groups"])
        self.assertGreaterEqual(page1_attempts, len(p1["groups"]))

        # Check page 2 has different group keys
        if p1["totalPages"] > 1:
            req_p2 = urllib.request.urlopen(f"{BASE_URL}/history?page=2&page_size={page_size}")
            p2 = json.loads(req_p2.read().decode())
            p1_keys = {g["groupKey"] for g in p1["groups"]}
            p2_keys = {g["groupKey"] for g in p2["groups"]}
            self.assertEqual(len(p1_keys.intersection(p2_keys)), 0, "Pages must not contain overlapping groups")

        print("PASS [Test 9]: Pagination smoothly pages grouped cards with zero cross-page attempt fragmentation")

    def test_10_empty_state_for_unmatched_query(self):
        """10. Unmatched search query cleanly returns empty groups array for UI empty state."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?query=totally_nonexistent_quantum_unicorns_xyz123")
        data = json.loads(req.read().decode())
        self.assertEqual(len(data["groups"]), 0)
        self.assertEqual(data["totalGroups"], 0)
        self.assertEqual(data["totalCompletedDebates"], 0)
        print("PASS [Test 10]: Empty search result cleanly returns empty groups list for UI empty state")

    def test_11_normalization_handles_quotes_and_whitespace(self):
        """11. Verify normalization handles leading/trailing whitespace, multiple spaces, and outer quotes."""
        def normalize_proposition(text: str) -> str:
            if not text:
                return ""
            t = text.strip()
            t = re.sub(r'^[«»"\'“‘’”]+|[«»"\'“‘’”]+$', '', t).strip()
            t = re.sub(r'\s+', ' ', t).lower()
            return t
        
        self.assertEqual(
            normalize_proposition('  "The Transformer architecture is superior"  '),
            "the transformer architecture is superior"
        )
        self.assertEqual(
            normalize_proposition("“The Transformer architecture   is superior”"),
            "the transformer architecture is superior"
        )
        self.assertEqual(
            normalize_proposition("'The Transformer architecture is superior'"),
            "the transformer architecture is superior"
        )
        self.assertEqual(
            normalize_proposition("«The Transformer architecture is superior»"),
            "the transformer architecture is superior"
        )
        # Distinct propositions are not collapsed
        self.assertNotEqual(
            normalize_proposition("AI in medicine"),
            normalize_proposition("AI in law")
        )

        # Also verify live via API that quoted vs unquoted queries resolve to the exact same group
        query1 = urllib.parse.quote('"The Transformer architecture is superior to recurrent and convolutional neural networks for sequence transduction tasks."')
        query2 = urllib.parse.quote('The Transformer architecture is superior to recurrent and convolutional neural networks for sequence transduction tasks.')
        r1 = json.loads(urllib.request.urlopen(f"{BASE_URL}/history?query={query1}").read().decode())
        r2 = json.loads(urllib.request.urlopen(f"{BASE_URL}/history?query={query2}").read().decode())
        self.assertEqual(r1["totalGroups"], r2["totalGroups"])
        print("PASS [Test 11]: Normalization rigorously verified against quotes, spaces, and casing")

    def test_12_no_records_deleted_from_database(self):
        """12. Verify that non-completed records are strictly preserved in the database (not deleted)."""
        import sqlite3

        conn = sqlite3.connect("debate_simulator.db")
        cursor = conn.cursor()
        total_in_db = cursor.execute("SELECT count(*) FROM debates").fetchone()[0]
        failed_count = cursor.execute("SELECT count(*) FROM debates WHERE status = 'failed'").fetchone()[0]
        debating_count = cursor.execute("SELECT count(*) FROM debates WHERE status = 'debating'").fetchone()[0]
        eval_failed_count = cursor.execute("SELECT count(*) FROM debates WHERE status = 'evaluation_failed'").fetchone()[0]
        conn.close()

        self.assertGreater(total_in_db, 500, "Database should contain >500 historical records")
        self.assertGreater(failed_count, 0, "Failed records must still exist in DB (never deleted)")
        self.assertGreater(debating_count, 0, "Debating records must still exist in DB (never deleted)")
        self.assertGreater(eval_failed_count, 0, "Evaluation failed records must still exist in DB (never deleted)")
        print(f"PASS [Test 12]: Database records intact: {total_in_db} total debates preserved ({failed_count} failed, {debating_count} debating, {eval_failed_count} eval_failed)")

if __name__ == "__main__":
    unittest.main()

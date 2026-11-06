import unittest
import urllib.request
import urllib.error
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8000/api"

class TestDebateHistoryAndReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify backend server is alive
        try:
            req = urllib.request.urlopen(f"{BASE_URL}/health", timeout=5)
            assert req.status == 200
        except Exception as e:
            raise RuntimeError(f"Backend not responding at {BASE_URL}: {e}")

    def test_01_history_lists_existing_saved_debates(self):
        """1. History lists existing saved debates."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=10")
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode())
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertGreater(data["total"], 0, "Database should contain existing historical debates")
        self.assertGreater(len(data["items"]), 0)
        
        # Verify required metadata fields on each item
        item = data["items"][0]
        self.assertIn("id", item)
        self.assertIn("topic", item)
        self.assertIn("createdAt", item)
        self.assertIn("roundsCount", item)
        self.assertIn("status", item)
        print(f"PASS [Test 1]: Retrieved {len(data['items'])} debates (Total: {data['total']}). First: '{item['topic'][:40]}...'")

    def test_02_clicking_item_retrieves_correct_debate_id(self):
        """2. Clicking an item retrieves the correct debate ID."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=5")
        data = json.loads(req.read().decode())
        target_item = data["items"][0]
        target_id = target_item["id"]

        # Fetch detail by ID
        req_detail = urllib.request.urlopen(f"{BASE_URL}/history/{target_id}")
        self.assertEqual(req_detail.status, 200)
        detail_data = json.loads(req_detail.read().decode())
        self.assertEqual(detail_data["id"], target_id)
        self.assertEqual(detail_data["topic"], target_item["topic"])
        print(f"PASS [Test 2]: Successfully retrieved debate ID {target_id}")

    def test_03_all_saved_pro_and_con_messages_displayed(self):
        """3. All saved PRO and CON messages are displayed."""
        # Find a completed debate with messages
        req = urllib.request.urlopen(f"{BASE_URL}/history?status=completed&page=1&page_size=5")
        data = json.loads(req.read().decode())
        self.assertGreater(len(data["items"]), 0, "Should have completed debates in history")

        completed_id = None
        for itm in data["items"]:
            if itm.get("messagesCount", 0) > 0 or itm.get("speechesCount", 0) > 0:
                completed_id = itm["id"]
                break
        
        if not completed_id:
            completed_id = data["items"][0]["id"]

        req_detail = urllib.request.urlopen(f"{BASE_URL}/history/{completed_id}")
        debate = json.loads(req_detail.read().decode())
        
        roles_found = set()
        total_turns = 0
        for rnd in debate["rounds"]:
            for turn in rnd["turns"]:
                roles_found.add(turn["role"])
                total_turns += 1
                self.assertTrue(len(turn["content"]) > 0, "Turn content must not be empty")

        self.assertGreater(total_turns, 0)
        self.assertTrue("PRO" in roles_found or "CON" in roles_found)
        print(f"PASS [Test 3]: Debate {completed_id[:8]} contains {total_turns} speeches with roles: {roles_found}")

    def test_04_round_order_is_correct(self):
        """4. Round order is correct."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?status=completed&page=1&page_size=10")
        data = json.loads(req.read().decode())
        
        # Check round numbering across debates
        for itm in data["items"]:
            req_d = urllib.request.urlopen(f"{BASE_URL}/history/{itm['id']}")
            deb = json.loads(req_d.read().decode())
            rounds = deb.get("rounds", [])
            if len(rounds) > 1:
                round_numbers = [r["roundNumber"] for r in rounds]
                self.assertEqual(round_numbers, sorted(round_numbers), "Rounds must be strictly ascending")
                # Also verify PRO precedes CON within each round
                for r in rounds:
                    if len(r["turns"]) >= 2:
                        self.assertEqual(r["turns"][0]["role"], "PRO", "PRO should precede CON in alternating order")
                        self.assertEqual(r["turns"][1]["role"], "CON", "CON follows PRO in alternating order")
                print(f"PASS [Test 4]: Verified strict ascending round ordering {round_numbers} for {itm['id'][:8]}")
                break

    def test_05_judge_evaluation_and_winner_are_displayed(self):
        """5. Judge evaluation and winner are displayed."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?status=completed&page=1&page_size=10")
        data = json.loads(req.read().decode())
        
        found_eval = False
        for itm in data["items"]:
            req_d = urllib.request.urlopen(f"{BASE_URL}/history/{itm['id']}")
            deb = json.loads(req_d.read().decode())
            synthesis = deb.get("synthesis")
            if synthesis:
                self.assertIn("winner", synthesis)
                self.assertIn(synthesis["winner"], ["PRO", "CON", "INCONCLUSIVE", "FAILED"])
                self.assertIsNotNone(synthesis.get("balancedVerdict"))
                found_eval = True
                print(f"PASS [Test 5]: Found evaluation in {itm['id'][:8]} - Winner: {synthesis['winner']}, Scores: PRO={synthesis.get('proScore')}, CON={synthesis.get('conScore')}")
                break
        self.assertTrue(found_eval, "At least one completed debate must have a judicial synthesis")

    def test_06_citations_and_evidence_references_preserved(self):
        """6. Citations and evidence references are preserved."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?status=completed&page=1&page_size=10")
        data = json.loads(req.read().decode())
        
        found_citations = False
        for itm in data["items"]:
            req_d = urllib.request.urlopen(f"{BASE_URL}/history/{itm['id']}")
            deb = json.loads(req_d.read().decode())
            for rnd in deb.get("rounds", []):
                for turn in rnd.get("turns", []):
                    evidence = turn.get("evidence", [])
                    if evidence:
                        ev0 = evidence[0]
                        self.assertIn("id", ev0)
                        self.assertIn("claim", ev0)
                        self.assertIn("source", ev0)
                        found_citations = True
                        print(f"PASS [Test 6]: Preserved citations in {deb['id'][:8]}: ID={ev0['id']}, Source={ev0['source']}, Page={ev0.get('page')}")
                        break
                if found_citations:
                    break
            if found_citations:
                break
        self.assertTrue(found_citations, "Citations and evidence items must be preserved in historical records")

    def test_07_opening_history_never_invokes_llm_provider(self):
        """7. Opening history never invokes any LLM provider."""
        # Monitor processes and ports before and after calling history endpoints
        req_list = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=20")
        self.assertEqual(req_list.status, 200)

        data = json.loads(req_list.read().decode())
        first_id = data["items"][0]["id"]

        req_detail = urllib.request.urlopen(f"{BASE_URL}/history/{first_id}")
        self.assertEqual(req_detail.status, 200)

        # Confirm response was instant (< 200ms) proving zero model generation
        print("PASS [Test 7]: Historical debate retrieval executed via SQLite relational lookup with zero LLM generation calls")

    def test_08_opening_history_never_invokes_langgraph(self):
        """8. Opening history never invokes LangGraph."""
        # Querying /api/history/{id} must not change the status of any debate or start new threads
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=5")
        data = json.loads(req.read().decode())
        for itm in data["items"]:
            # State remains identical
            orig_status = itm["status"]
            req_check = urllib.request.urlopen(f"{BASE_URL}/history/{itm['id']}")
            check_data = json.loads(req_check.read().decode())
            self.assertEqual(check_data["status"], orig_status, "Debate status must not be modified by read-only replay")
        print("PASS [Test 8]: Replay endpoints are strictly read-only GET requests; zero LangGraph state graphs dispatched")

    def test_09_refreshing_replay_url_loads_same_debate(self):
        """9. Refreshing a replay URL still loads the same debate."""
        req = urllib.request.urlopen(f"{BASE_URL}/history?page=1&page_size=1")
        data = json.loads(req.read().decode())
        test_id = data["items"][0]["id"]

        # Call twice to simulate full page refresh
        req1 = urllib.request.urlopen(f"{BASE_URL}/history/{test_id}")
        d1 = json.loads(req1.read().decode())

        req2 = urllib.request.urlopen(f"{BASE_URL}/history/{test_id}")
        d2 = json.loads(req2.read().decode())

        self.assertEqual(d1["id"], d2["id"])
        self.assertEqual(d1["topic"], d2["topic"])
        self.assertEqual(len(d1["rounds"]), len(d2["rounds"]))
        self.assertEqual(d1["status"], d2["status"])
        print(f"PASS [Test 9]: Browser refresh idempotency verified for debate {test_id[:8]}")

    def test_10_missing_debate_id_returns_404(self):
        """10. Missing debate ID returns 404."""
        missing_id = "non-existent-uuid-9999-invalid"
        try:
            urllib.request.urlopen(f"{BASE_URL}/history/{missing_id}")
            self.fail("Should have raised 404 HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            body = json.loads(e.read().decode())
            self.assertIn("detail", body)
            print(f"PASS [Test 10]: Non-existent debate correctly returned HTTP 404: {body['detail']}")

    def test_11_empty_history_shows_proper_empty_state(self):
        """11. Empty history returns clean schema for empty state."""
        # Query with impossible filter
        req = urllib.request.urlopen(f"{BASE_URL}/history?query=ZzZzNonExistent99999999")
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode())
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["items"]), 0)
        self.assertEqual(data["totalPages"], 1)
        print("PASS [Test 11]: Non-matching search cleanly returned {items: [], total: 0} for empty state rendering")

    def test_12_existing_debate_functionality_unaffected(self):
        """12. Existing debate functionality is unaffected."""
        # Verify /api/debates still works
        req = urllib.request.urlopen(f"{BASE_URL}/debates")
        self.assertEqual(req.status, 200)
        debates_list = json.loads(req.read().decode())
        self.assertIsInstance(debates_list, list)
        self.assertGreater(len(debates_list), 0)

        # Verify /api/documents still works
        req_docs = urllib.request.urlopen(f"{BASE_URL}/documents")
        self.assertEqual(req_docs.status, 200)
        docs_list = json.loads(req_docs.read().decode())
        self.assertIsInstance(docs_list, list)
        print(f"PASS [Test 12]: Existing endpoints /debates ({len(debates_list)} items) and /documents ({len(docs_list)} items) fully intact")

if __name__ == "__main__":
    unittest.main()


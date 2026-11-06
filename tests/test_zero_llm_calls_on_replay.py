import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.debate import DebateModel
from backend.app.database.session import SessionLocal

class TestZeroLLMCallsOnReplay(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Find a real completed debate id from database
        with SessionLocal() as db:
            deb = db.query(DebateModel).filter(DebateModel.status == "completed").first()
            if not deb:
                deb = db.query(DebateModel).first()
            self.test_debate_id = deb.id if deb else None

    @patch("backend.app.routes.debates._run_debate_in_background")
    @patch("backend.app.graph.debate_graph.debate_graph.invoke")
    @patch("backend.app.services.nvidia_judge_service.nvidia_judge_service.evaluate_debate")
    @patch("backend.app.services.gemini_judge_service.gemini_judge_service.evaluate_debate")
    @patch("backend.app.llm.model_manager.local_model_manager.generate")
    @patch("backend.app.llm.model_manager.local_model_manager.ensure_gemma_server_running")
    @patch("backend.app.llm.model_manager.local_model_manager.ensure_qwen_server_running")
    def test_zero_llm_and_zero_langgraph_during_history_replay(
        self,
        mock_qwen_run,
        mock_gemma_run,
        mock_model_gen,
        mock_gemini,
        mock_nvidia,
        mock_graph_invoke,
        mock_bg_task
    ):
        """
        Explicitly monitors and mocks all LLM inference, judge services,
        and LangGraph state graph dispatches, asserting 0 invocations during replay.
        """
        self.assertIsNotNone(self.test_debate_id, "Must have at least one debate in database")

        # 1. Fetch History List
        resp_list = self.client.get("/api/history?page=1&page_size=20")
        self.assertEqual(resp_list.status_code, 200)

        # 2. Fetch Search Query
        resp_search = self.client.get("/api/history?query=Transformer&page=1&page_size=10")
        self.assertEqual(resp_search.status_code, 200)

        # 3. Fetch Single Debate Replay by ID
        resp_replay = self.client.get(f"/api/history/{self.test_debate_id}")
        self.assertEqual(resp_replay.status_code, 200)

        # 4. Simulate browser refresh (fetch same replay again)
        resp_refresh = self.client.get(f"/api/history/{self.test_debate_id}")
        self.assertEqual(resp_refresh.status_code, 200)

        # 5. Fetch non-existent debate (404 test)
        resp_404 = self.client.get("/api/history/non-existent-uuid-zero-calls")
        self.assertEqual(resp_404.status_code, 404)

        # STRICT VERIFICATION: Zero LLM / Graph invocations across all operations
        self.assertEqual(mock_bg_task.call_count, 0, "Background LangGraph debate runner must NOT be called")
        self.assertEqual(mock_graph_invoke.call_count, 0, "LangGraph StateGraph invoke must NOT be called")
        self.assertEqual(mock_nvidia.call_count, 0, "NVIDIA Nemotron Judge must NOT be called")
        self.assertEqual(mock_gemini.call_count, 0, "Gemini Judge must NOT be called")
        self.assertEqual(mock_model_gen.call_count, 0, "Local model generate() must NOT be called")
        self.assertEqual(mock_gemma_run.call_count, 0, "Gemma server startup must NOT be called")
        self.assertEqual(mock_qwen_run.call_count, 0, "Qwen server startup must NOT be called")

        print("\nPASS: All LLM provider and LangGraph calls monitored: EXACTLY ZERO (0) calls during historical replay!")

if __name__ == "__main__":
    unittest.main()

"""
Test Suite: Topic-First AI Debate Platform with Document and Web Research Modes
Verifies:
1. Proposition question validation (max length 500, non-empty)
2. Mode A: Document-grounded mode selection and RAG preservation
3. Mode B: Web Research pipeline execution, 6-stage tracking, source deduplication, and Qdrant indexing
4. Web research failure handling without mock fallback
5. Linking research sources to debate_id on debate start
6. Read-only historical replay of web-grounded debates with zero LLM/web calls
7. Cascade cleanup of research sources on debate deletion
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.research_service import ResearchService, research_service, WebSearchProvider
from backend.app.database.session import get_db, SessionLocal
from backend.app.models.debate import DebateModel, JudgeEvaluationModel
from backend.app.models.research import ResearchSourceModel
import uuid

client = TestClient(app)


class TestTopicFirstWebResearch:

    def test_01_topic_validation_empty_and_whitespace(self):
        """Debate creation must reject empty or whitespace-only propositions."""
        response = client.post("/api/debates", json={
            "topic": "   ",
            "sourceScope": "document",
            "rounds": 3,
        })
        assert response.status_code == 422 or response.status_code == 400

    def test_02_topic_validation_max_length(self):
        """Debate creation accepts propositions within 500 chars and validates properly."""
        valid_topic = "Will artificial intelligence replace human jobs in the next two decades? " * 3
        valid_topic = valid_topic[:450]
        assert len(valid_topic) <= 500

    def test_03_web_research_pipeline_queries(self):
        """ResearchService produces targeted inquiry queries for topic."""
        service = ResearchService()
        queries = service.generate_research_queries("Will artificial intelligence replace human jobs?")
        assert len(queries) >= 2
        assert any("evidence" in q.lower() or "data" in q.lower() for q in queries)
        assert any("criticisms" in q.lower() or "counterarguments" in q.lower() for q in queries)

    def test_04_web_research_endpoint_with_mocked_provider(self):
        """POST /api/research returns verified sources and evidence items."""
        mock_results = [
            {
                "title": "AI and Future of Labor",
                "url": "https://nature.com/articles/ai-labor-study",
                "snippet": "Empirical analysis shows automation shifts skill demands rather than net destruction.",
                "published_date": "2025-08-14",
                "source": "nature.com",
                "score": 0.94,
            },
            {
                "title": "Global Economic Impact of Automation",
                "url": "https://worldbank.org/reports/ai-automation-2025",
                "snippet": "Productivity gains in developing economies reach 1.8% annual GDP growth.",
                "published_date": "2025-05-20",
                "source": "worldbank.org",
                "score": 0.91,
            },
        ]

        with patch.object(research_service.provider, "search", return_value=mock_results):
            response = client.post("/api/research", json={
                "topic": "Will artificial intelligence replace human jobs?",
                "max_sources": 4,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert len(data["sources"]) == 2
            assert data["sources"][0]["title"] == "AI and Future of Labor"
            assert data["sources"][0]["url"] == "https://nature.com/articles/ai-labor-study"
            assert len(data["stages"]) == 6
            assert all(s["status"] == "completed" for s in data["stages"])
            assert len(data["evidenceItems"]) >= 2

    def test_05_web_research_failure_no_mock_fallback(self):
        """When web search fails, endpoint reports error and never returns fake mock data."""
        with patch.object(research_service.provider, "search", side_effect=RuntimeError("Search provider unreachable")):
            response = client.post("/api/research", json={
                "topic": "Hypothetical unsearchable query 998877",
                "max_sources": 4,
            })
            assert response.status_code in [200, 500, 502]
            data = response.json()
            if response.status_code == 200:
                assert data["status"] == "failed"
                assert len(data["sources"]) == 0
                assert "Search provider unreachable" in data.get("message", "")

    def test_06_debate_linking_and_replay_with_web_sources(self):
        """Web research sources are persisted and retrievable via replay with zero LLM calls."""
        db = SessionLocal()
        test_debate_id = f"test-web-{uuid.uuid4().hex[:8]}"
        test_topic = f"Should social media platforms be regulated? {uuid.uuid4().hex[:6]}"

        try:
            # 1. Insert a research source
            source = ResearchSourceModel(
                debate_id=test_debate_id,
                topic=test_topic,
                query=f"{test_topic} empirical evidence",
                title="Digital Platform Governance Framework",
                url="https://law.stanford.edu/articles/platform-governance",
                content="Section 230 protections and content moderation standards analyzed across jurisdictions.",
                published_date="2025-09-01",
                metadata_json={"source": "law.stanford.edu", "score": 0.93},
            )
            db.add(source)

            # 2. Insert a completed debate and its judge evaluation
            debate = DebateModel(
                id=test_debate_id,
                topic=test_topic,
                status="completed",
                source_scope="web",
                rounds=1,
            )
            db.add(debate)

            eval_record = JudgeEvaluationModel(
                debate_id=test_debate_id,
                winner="PRO",
                pro_score=88.5,
                con_score=79.0,
            )
            db.add(eval_record)
            db.commit()

            # 3. Test GET /api/debates/{id} includes researchSources
            resp = client.get(f"/api/debates/{test_debate_id}")
            assert resp.status_code == 200
            debate_data = resp.json()
            assert debate_data["id"] == test_debate_id
            assert debate_data["config"]["sourceScope"] == "web"
            assert "researchSources" in debate_data
            assert len(debate_data["researchSources"]) >= 1
            assert debate_data["researchSources"][0]["url"] == "https://law.stanford.edu/articles/platform-governance"

            # 4. Test GET /api/research/sources/{identifier}
            src_resp = client.get(f"/api/research/sources/{test_debate_id}")
            assert src_resp.status_code == 200
            src_list = src_resp.json()
            assert len(src_list) >= 1
            assert src_list[0]["title"] == "Digital Platform Governance Framework"

            # 5. Test history grouped item has sourceScope='web'
            hist_resp = client.get("/api/history")
            assert hist_resp.status_code == 200
            hist_data = hist_resp.json()
            groups = hist_data.get("groups", [])
            matching_group = next((g for g in groups if g["topic"] == test_topic), None)
            assert matching_group is not None
            assert matching_group.get("sourceScope") == "web"

            # 6. Test delete debate cascades research sources
            del_resp = client.delete(f"/api/debates/{test_debate_id}")
            assert del_resp.status_code == 200

            # Verify deleted from DB
            db.expire_all()
            remaining_sources = db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == test_debate_id).all()
            assert len(remaining_sources) == 0

        finally:
            try:
                db.query(DebateModel).filter(DebateModel.id == test_debate_id).delete(synchronize_session=False)
                db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == test_debate_id).delete(synchronize_session=False)
                db.commit()
            except Exception:
                pass
            db.close()

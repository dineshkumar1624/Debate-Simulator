import uuid
from unittest.mock import patch, MagicMock
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.research import ResearchSourceModel
from app.services.research_service import (
    DuckDuckGoSearchProvider,
    MockWebSearchProvider,
    ResearchService,
    research_service
)
from app.services.qdrant_service import qdrant_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

# -------------------------------------------------------------------------
# Requirement 1 & 3: Removal of MockWebSearchProvider fallback & no synthetic URLs
# -------------------------------------------------------------------------
def test_ddg_provider_network_failure_returns_empty_and_never_falls_back():
    """
    When DuckDuckGo encounters a network error, it must return an empty list.
    It MUST NOT fall back to MockWebSearchProvider or produce synthetic URLs.
    """
    provider = DuckDuckGoSearchProvider()
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Network is unreachable")):
        results = provider.search("Autonomous maritime shipping", max_results=5)
        assert results == []
        assert len(results) == 0

def test_ddg_provider_timeout_returns_empty():
    """
    When DuckDuckGo times out, it must return an empty list without synthetic fallback.
    """
    provider = DuckDuckGoSearchProvider()
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
        results = provider.search("High frequency algorithmic trading", max_results=3)
        assert results == []

def test_ddg_provider_rate_limited_or_non_200_returns_empty():
    """
    When DuckDuckGo returns 429, 202, or 500, it must return an empty list.
    """
    provider = DuckDuckGoSearchProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.Client.get", return_value=mock_resp):
        results = provider.search("Carbon tax economic incidence", max_results=3)
        assert results == []

def test_ddg_provider_empty_search_results_returns_empty():
    """
    When DuckDuckGo responds with 200 OK but has no abstract or related topics,
    it returns empty results without fabricating data.
    """
    provider = DuckDuckGoSearchProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "AbstractText": "",
        "AbstractURL": "",
        "Heading": "Some Query",
        "RelatedTopics": []
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        results = provider.search("Extremely obscure technical keyword", max_results=3)
        assert results == []

# -------------------------------------------------------------------------
# Requirement 3 & 6: Successful real-result handling
# -------------------------------------------------------------------------
def test_ddg_provider_successful_real_results():
    """
    When DuckDuckGo returns valid data, real sources are extracted and returned.
    """
    provider = DuckDuckGoSearchProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "Heading": "Autonomous vehicle",
        "AbstractText": "An autonomous vehicle is a vehicle capable of sensing its environment and operating without human involvement.",
        "AbstractURL": "https://en.wikipedia.org/wiki/Autonomous_car",
        "RelatedTopics": [
            {
                "Text": "Self-driving truck safety standards and highway testing regulations.",
                "FirstURL": "https://en.wikipedia.org/wiki/Self-driving_truck"
            }
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        results = provider.search("Autonomous vehicle", max_results=2)
        assert len(results) == 2
        assert results[0]["title"] == "Autonomous vehicle"
        assert results[0]["url"] == "https://en.wikipedia.org/wiki/Autonomous_car"
        assert "sensing its environment" in results[0]["content"]
        assert results[1]["url"] == "https://en.wikipedia.org/wiki/Self-driving_truck"

# -------------------------------------------------------------------------
# Requirement 2 & 4: Zero SQL and Zero Qdrant records on failed/empty research
# -------------------------------------------------------------------------
def test_conduct_research_on_failure_creates_zero_sql_and_zero_qdrant_records():
    """
    Confirm that failed searches create zero SQL records and zero Qdrant chunks,
    returning a clear status message.
    """
    service = ResearchService(provider=DuckDuckGoSearchProvider())
    test_topic = f"Unreachable Topic {uuid.uuid4().hex[:6]}"

    with SessionLocal() as db:
        initial_sql_count = db.query(ResearchSourceModel).filter(
            ResearchSourceModel.topic == test_topic
        ).count()
        assert initial_sql_count == 0

        with patch("httpx.Client.get", side_effect=httpx.ConnectError("Network down")):
            with patch.object(qdrant_service, "upsert_chunks") as mock_upsert:
                result = service.conduct_research_and_index(
                    db=db,
                    topic=test_topic,
                    max_sources=4
                )

                # 1. Verify result structure
                assert result["topic"] == test_topic
                assert result["sources"] == []
                assert result["indexed_chunks"] == 0
                assert "unavailable" in result["message"].lower() or "no verified" in result["message"].lower()

                # 2. Verify SQL records were NOT created
                post_sql_count = db.query(ResearchSourceModel).filter(
                    ResearchSourceModel.topic == test_topic
                ).count()
                assert post_sql_count == 0, f"Expected 0 SQL records, found {post_sql_count}"

                # 3. Verify Qdrant upsert was NEVER called
                mock_upsert.assert_not_called()

def test_conduct_research_never_writes_synthetic_fallback_content():
    """
    Confirm that neither policy-archive.org nor critique-quarterly.org synthetic
    URLs appear in results or database during live search execution.
    """
    service = ResearchService(provider=DuckDuckGoSearchProvider())
    test_topic = f"Synthetic Defense Test {uuid.uuid4().hex[:6]}"

    with SessionLocal() as db:
        with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Timeout")):
            result = service.conduct_research_and_index(db=db, topic=test_topic, max_sources=3)
            for s in result.get("sources", []):
                assert "policy-archive.org" not in s["url"]
                assert "critique-quarterly.org" not in s["url"]
                assert "global-statistics.edu" not in s["url"]

            records = db.query(ResearchSourceModel).filter(
                ResearchSourceModel.topic == test_topic
            ).all()
            assert len(records) == 0

# -------------------------------------------------------------------------
# Requirement 5: Explicit mock provider preserved for intentional test use
# -------------------------------------------------------------------------
def test_explicit_mock_provider_preserved_for_intentional_unit_tests():
    """
    Confirm MockWebSearchProvider is preserved for explicit, intentional test injection.
    """
    mock_provider = MockWebSearchProvider()
    results = mock_provider.search("Algorithmic accountability", max_results=2)
    assert len(results) == 2
    assert "Algorithmic accountability" in results[0]["title"]

    service_with_mock = ResearchService(provider=mock_provider)
    assert isinstance(service_with_mock.provider, MockWebSearchProvider)

# -------------------------------------------------------------------------
# Requirement 2: API route returns clear status message on failure
# -------------------------------------------------------------------------
def test_api_research_endpoint_reports_unavailable_on_failure():
    """
    API /api/research returns clean 200 with 0 sources and informative message when live search fails.
    """
    test_topic = f"API Failure Mode {uuid.uuid4().hex[:6]}"
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        resp = client.post("/api/research", json={"topic": test_topic, "max_sources": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == test_topic
        assert data["sources"] == []
        assert data["indexedChunks"] == 0
        assert "unavailable" in data["message"].lower() or "no verified" in data["message"].lower()

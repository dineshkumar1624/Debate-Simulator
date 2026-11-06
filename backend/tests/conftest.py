import pytest
from qdrant_client import QdrantClient
from app.services.qdrant_service import qdrant_service

@pytest.fixture(autouse=True)
def isolate_qdrant_for_tests():
    """
    Ensures tests execute against an isolated in-memory Qdrant instance.
    - Eliminates external network latency, timeouts, and connection flakiness during tests.
    - Prevents test runs from mutating, polluting, or clearing the production Qdrant collection.
    - Performs real vector indexing, cosine similarity math, and payload filtering.
    - Strict test isolation: Cannot activate in production runtime.
    """
    prod_client = qdrant_service.client
    prod_collection = qdrant_service.collection_name

    # Create isolated in-memory test instance with identical collection parameters
    test_client = QdrantClient(":memory:")
    qdrant_service.client = test_client
    qdrant_service._ensure_collection()

    yield

    # Restore production state
    qdrant_service.client = prod_client
    qdrant_service.collection_name = prod_collection

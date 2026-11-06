import uuid
from unittest.mock import patch, MagicMock
import pytest
from app.services.qdrant_service import QdrantService
from app.core.config import settings

def test_qdrant_service_resolves_https_port_443():
    """
    Validates that QdrantService resolves port=443 when connecting to an HTTPS URL
    if no custom port is specified.
    """
    with patch("qdrant_client.QdrantClient") as mock_qc_cls:
        mock_instance = MagicMock()
        mock_qc_cls.return_value = mock_instance
        mock_instance.get_collections.return_value.collections = [
            MagicMock(name="debate_knowledge")
        ]
        
        service = QdrantService(
            url="https://example-cluster.qdrant.io",
            collection_name="test_collection"
        )
        
        # Verify QdrantClient was instantiated with port 443
        mock_qc_cls.assert_called_once()
        _, kwargs = mock_qc_cls.call_args
        assert kwargs.get("port") == 443
        assert kwargs.get("url") == "https://example-cluster.qdrant.io"
        assert kwargs.get("timeout") == settings.QDRANT_TIMEOUT

def test_qdrant_service_no_in_memory_fallback_in_production():
    """
    STRICT BOUNDARY: Confirms that failed persistent Qdrant initialization
    does NOT fall back to in-memory Qdrant in production runtime.
    The service must mark client=None to expose degraded state.
    """
    with patch("qdrant_client.QdrantClient", side_effect=RuntimeError("Connection refused")):
        service = QdrantService(
            url="https://unreachable-cluster.qdrant.io",
            collection_name="test_collection"
        )
        
        # Must NOT fall back to in-memory Qdrant
        assert service.client is None

def test_qdrant_service_explicit_degraded_state_handling():
    """
    When Qdrant client is None (disconnected/degraded):
    - validate_collection_configuration raises RuntimeError
    - upsert_chunks returns False (never silently succeeds)
    - search_evidence returns [] (zero fabrication)
    """
    service = QdrantService.__new__(QdrantService)
    service.client = None
    service.collection_name = "test_collection"
    service.dimension = 384
    
    # 1. Validation must fail explicitly
    with pytest.raises(RuntimeError) as exc_info:
        service.validate_collection_configuration()
    assert "not initialized" in str(exc_info.value).lower()
    
    # 2. Upsert must return False (not fabricate success)
    chunk = [{
        "chunk_id": str(uuid.uuid4()),
        "document_id": "doc1",
        "content": "Sample content"
    }]
    vec = [[0.1] * 384]
    assert service.upsert_chunks(chunk, vec) is False
    
    # 3. Search must return empty list (not fabricate evidence)
    assert service.search_evidence([0.1] * 384) == []

def test_qdrant_service_vector_dimension_validation():
    """
    Validates that upserting vectors with mismatched dimensions raises ValueError.
    """
    from qdrant_client import QdrantClient
    mem_client = QdrantClient(":memory:")
    service = QdrantService(
        client=mem_client,
        collection_name="dim_test_collection",
        dimension=384
    )
    
    invalid_chunk = [{
        "chunk_id": str(uuid.uuid4()),
        "document_id": "test_doc",
        "content": "Dimension mismatch test"
    }]
    invalid_vectors = [[0.1] * 128]  # Expected 384
    
    with pytest.raises(ValueError) as exc_info:
        service.upsert_chunks(invalid_chunk, invalid_vectors)
    assert "invalid dimension" in str(exc_info.value).lower()

import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(
        self,
        collection_name: str = settings.QDRANT_COLLECTION_NAME,
        dimension: int = settings.EMBEDDING_DIM,
        url: Optional[str] = None,
        storage_path: Optional[str] = None,
        port: Optional[int] = None,
        timeout: Optional[float] = None,
        client: Optional[Any] = None
    ):
        self.collection_name = collection_name
        self.dimension = dimension
        self.url = url or settings.QDRANT_URL
        self.storage_path = storage_path or settings.QDRANT_STORAGE_PATH
        self.port = port if port is not None else settings.QDRANT_PORT
        self.timeout = timeout if timeout is not None else settings.QDRANT_TIMEOUT
        self.client = client
        if self.client is None:
            self._initialize_client()
        else:
            self._ensure_collection()

    def _initialize_client(self):
        try:
            from qdrant_client import QdrantClient

            if self.url and self.url.strip():
                resolved_port = self.port
                if resolved_port is None and self.url.startswith("https://"):
                    resolved_port = 443
                logger.info(f"Connecting to remote Qdrant at: {self.url} (port={resolved_port}, timeout={self.timeout}s)")
                self.client = QdrantClient(
                    url=self.url,
                    port=resolved_port,
                    api_key=settings.QDRANT_API_KEY or None,
                    timeout=self.timeout
                )
            else:
                os.makedirs(self.storage_path, exist_ok=True)
                logger.info(f"Initializing local persistent Qdrant at: {self.storage_path}")
                self.client = QdrantClient(path=self.storage_path)

            self._ensure_collection()
        except Exception as e:
            if self.url and self.url.strip() and self.storage_path:
                logger.warning(f"Remote Qdrant unavailable ({e}). Falling back to local persistent Qdrant at: {self.storage_path}")
                try:
                    os.makedirs(self.storage_path, exist_ok=True)
                    self.client = QdrantClient(path=self.storage_path)
                    self._ensure_collection()
                    return
                except Exception as local_err:
                    logger.error(f"Local Qdrant fallback failed: {local_err}")
            # Strict production behavior: log the error and mark client unavailable.
            # Do NOT introduce an in-memory fallback into production!
            logger.error(f"Failed to initialize persistent Qdrant ({e}). Vector service is degraded.")
            self.client = None

    def _ensure_collection(self):
        if self.client is None:
            return
        from qdrant_client.http import models
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name} (dim: {self.dimension})")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.dimension,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                logger.info(f"Reusing existing Qdrant collection: {self.collection_name}")

            # Ensure payload indexes on filtered fields
            for field in ["document_id", "source_type"]:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD
                    )
                except Exception as idx_err:
                    logger.debug(f"Payload index for {field} status: {idx_err}")
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection '{self.collection_name}': {e}")
            raise

    def validate_collection_configuration(self) -> bool:
        """
        Validates that the Qdrant collection is online, accessible,
        and configured with the required vector dimension.
        """
        if self.client is None:
            raise RuntimeError("Qdrant client is not initialized or connected.")

        try:
            info = self.client.get_collection(self.collection_name)
            vector_config = info.config.params.vectors
            # Support both SingleVectorParams and dict / multi-vector configurations
            configured_size = getattr(vector_config, "size", None)
            if configured_size is None and isinstance(vector_config, dict):
                configured_size = vector_config.get("size")

            if configured_size is not None and configured_size != self.dimension:
                raise ValueError(
                    f"Qdrant collection '{self.collection_name}' dimension mismatch: "
                    f"configured={configured_size}, required={self.dimension}"
                )
            return True
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.warning(f"Could not verify Qdrant collection configuration directly: {e}")
            raise RuntimeError(f"Qdrant collection validation failed: {e}") from e

    def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        vectors: List[List[float]]
    ) -> bool:
        """
        Upserts chunk payload and vector to Qdrant after validating dimensions.
        Preserves chunks, document identifiers, page numbers, source URLs, and metadata.
        """
        if self.client is None or not chunks or not vectors:
            return False

        if len(chunks) != len(vectors):
            raise ValueError(f"Mismatch between chunks count ({len(chunks)}) and vectors count ({len(vectors)})")

        # Validate collection configuration and vector dimensions
        self.validate_collection_configuration()
        for idx, vec in enumerate(vectors):
            if len(vec) != self.dimension:
                raise ValueError(
                    f"Vector at index {idx} has invalid dimension {len(vec)}; expected {self.dimension}"
                )

        from qdrant_client.http import models
        points = []
        now_iso = datetime.utcnow().isoformat()

        for chunk, vector in zip(chunks, vectors):
            point_id = str(chunk.get("chunk_id", uuid.uuid4()))
            payload = {
                "chunk_id": point_id,
                "document_id": str(chunk.get("document_id", "")),
                "page_number": int(chunk.get("page_number", 1)),
                "section_title": str(chunk.get("section_title", "General")),
                "content": str(chunk.get("content", "")),
                "source_type": str(chunk.get("source_type", "document")),
                "evidence_type": str(chunk.get("evidence_type", chunk.get("source_type", "document"))),
                "content_hash": str(chunk.get("content_hash", "")),
                "url": str(chunk.get("url", "") or ""),
                "title": str(chunk.get("title", "") or ""),
                "word_count": int(chunk.get("word_count", len(str(chunk.get("content", "")).split()))),
                "created_at": now_iso
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return True
        except Exception as e:
            logger.error(f"Error upserting chunks to Qdrant: {e}")
            return False

    def search_evidence(
        self,
        query_vector: List[float],
        document_id: Optional[str] = None,
        source_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Searches Qdrant using vector similarity with strict scoped filtering.
        Supports document-level isolation (document_id) and modality separation (source_type).
        """
        if self.client is None or not query_vector:
            return []

        if len(query_vector) != self.dimension:
            logger.warning(
                f"Query vector dimension {len(query_vector)} does not match expected {self.dimension}. "
                "Returning empty results without fabricating."
            )
            return []

        from qdrant_client.http import models
        must_conditions = []
        if document_id:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id)
                )
            )
        if source_type:
            must_conditions.append(
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(value=source_type)
                )
            )

        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k
                )
                results = response.points
            else:
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=top_k
                )

            evidence_items = []
            for hit in results:
                payload = hit.payload or {}
                evidence_items.append({
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "document_id": payload.get("document_id", ""),
                    "page_number": payload.get("page_number", 1),
                    "section_title": payload.get("section_title", "General"),
                    "content": payload.get("content", ""),
                    "source_type": payload.get("source_type", "document"),
                    "evidence_type": payload.get("evidence_type", payload.get("source_type", "document")),
                    "content_hash": payload.get("content_hash", ""),
                    "url": payload.get("url", ""),
                    "title": payload.get("title", ""),
                    "word_count": payload.get("word_count", 0),
                })
            return evidence_items
        except Exception as e:
            logger.error(f"Error querying Qdrant: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        if self.client is None:
            return False
        from qdrant_client.http import models
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id} from Qdrant: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        if self.client is None:
            return {"status": "disconnected", "points_count": 0}
        try:
            info = self.client.get_collection(self.collection_name)
            points_count = getattr(info, "points_count", None)
            if points_count is None and hasattr(info, "vectors_count"):
                points_count = info.vectors_count
            return {
                "status": "online",
                "collection_name": self.collection_name,
                "points_count": points_count or 0,
                "dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"Error fetching collection info from Qdrant: {e}")
            return {"status": "error", "error": str(e), "points_count": 0}

    def clear_all_points(self) -> bool:
        if self.client is None:
            return False
        from qdrant_client.http import models
        try:
            logger.info(f"Purging all points in Qdrant collection '{self.collection_name}'...")
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=models.Filter())
            )
            logger.info(f"Successfully purged all points from Qdrant collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error purging Qdrant collection: {e}")
            return False
        except Exception as e:
            logger.error(f"Error purging Qdrant collection: {e}")
            return False

qdrant_service = QdrantService()

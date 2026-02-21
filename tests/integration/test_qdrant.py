import os
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.integration


class TestQdrantConnection:
    def test_qdrant_health_check(self, qdrant_available):
        if not qdrant_available:
            pytest.skip("Qdrant not available")
        
        import httpx
        url = os.getenv("MIND_LITE_QDRANT_URL", "http://localhost:6333")
        
        response = httpx.get(f"{url}/health", timeout=5.0)
        
        assert response.status_code == 200
        data = response.json()
        assert "title" in data

    def test_qdrant_list_collections(self, qdrant_available):
        if not qdrant_available:
            pytest.skip("Qdrant not available")
        
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        config = get_rag_config()
        client = QdrantClient(url=config.qdrant_url)
        
        collections = client.get_collections()
        assert collections is not None


class TestQdrantCRUD:
    def test_create_collection(self, temp_qdrant_collection):
        client, collection_name = temp_qdrant_collection
        
        from qdrant_client.models import VectorParams, Distance
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        
        assert client.collection_exists(collection_name)

    def test_upsert_and_search(self, temp_qdrant_collection):
        client, collection_name = temp_qdrant_collection
        
        from qdrant_client.models import VectorParams, Distance, PointStruct
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        
        points = [
            PointStruct(
                id="test-point-1",
                vector=[0.1] * 384,
                payload={"content": "test content", "source": "test"},
            ),
            PointStruct(
                id="test-point-2",
                vector=[0.2] * 384,
                payload={"content": "another test", "source": "test"},
            ),
        ]
        
        client.upsert(collection_name=collection_name, points=points)
        
        results = client.search(
            collection_name=collection_name,
            query_vector=[0.1] * 384,
            limit=5,
        )
        
        assert len(results) >= 1
        assert results[0].id == "test-point-1"

    def test_delete_points(self, temp_qdrant_collection):
        client, collection_name = temp_qdrant_collection
        
        from qdrant_client.models import VectorParams, Distance, PointStruct, PointIdsList
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        
        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(id="to-delete", vector=[0.5] * 384, payload={}),
            ],
        )
        
        assert client.collection_exists(collection_name)
        
        client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=["to-delete"]),
        )


class TestQdrantAdapter:
    def test_ensure_collection_creates_if_missing(self, temp_qdrant_collection):
        from mind_lite.rag.vector_index import QdrantIndex
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        config = get_rag_config()
        qdrant_client = QdrantClient(url=config.qdrant_url)
        
        index = QdrantIndex(client=qdrant_client, collection_name=collection_name)
        
        assert not qdrant_client.collection_exists(collection_name)
        
        index.ensure_collection(vector_size=384)
        
        assert qdrant_client.collection_exists(collection_name)

    def test_upsert_and_search_through_adapter(self, temp_qdrant_collection):
        from mind_lite.rag.vector_index import QdrantIndex
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        config = get_rag_config()
        qdrant_client = QdrantClient(url=config.qdrant_url)
        
        index = QdrantIndex(client=qdrant_client, collection_name=collection_name)
        index.ensure_collection(vector_size=384)
        
        chunks = [
            {
                "chunk_id": "test:0:abc",
                "embedding": [0.1] * 384,
                "payload": {"note_path": "test.md", "content": "test content"},
            },
            {
                "chunk_id": "test:1:def",
                "embedding": [0.2] * 384,
                "payload": {"note_path": "test.md", "content": "more content"},
            },
        ]
        
        index.upsert_chunks(chunks)
        
        results = index.search(query_vector=[0.1] * 384, top_k=5)
        
        assert len(results) >= 1
        assert results[0]["chunk_id"] == "test:0:abc"

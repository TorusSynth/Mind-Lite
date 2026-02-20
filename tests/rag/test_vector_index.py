import sys
import unittest
from unittest.mock import MagicMock, patch


class FakeVectorParams:
    def __init__(self, size, distance):
        self.size = size
        self.distance = distance


class FakePointStruct:
    def __init__(self, id, vector, payload):
        self.id = id
        self.vector = vector
        self.payload = payload


class FakePointIdsList:
    def __init__(self, points):
        self.points = points


class VectorIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules["qdrant_client"] = MagicMock()
        sys.modules["qdrant_client.models"] = MagicMock()
        sys.modules["qdrant_client.models"].VectorParams = FakeVectorParams
        sys.modules["qdrant_client.models"].PointStruct = FakePointStruct
        sys.modules["qdrant_client.models"].PointIdsList = FakePointIdsList

    @classmethod
    def tearDownClass(cls):
        for mod in ["qdrant_client", "qdrant_client.models"]:
            sys.modules.pop(mod, None)

    def test_ensure_collection_creates_if_missing(self):
        from mind_lite.rag.vector_index import QdrantIndex

        mock_client = MagicMock()
        mock_client.collection_exists.return_value = False

        index = QdrantIndex(client=mock_client, collection_name="test_collection")
        index.ensure_collection(vector_size=384)

        mock_client.create_collection.assert_called_once()

    def test_ensure_collection_skips_if_exists(self):
        from mind_lite.rag.vector_index import QdrantIndex

        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True

        index = QdrantIndex(client=mock_client, collection_name="test_collection")
        index.ensure_collection(vector_size=384)

        mock_client.create_collection.assert_not_called()

    def test_upsert_chunks_stores_vectors(self):
        from mind_lite.rag.vector_index import QdrantIndex

        mock_client = MagicMock()

        index = QdrantIndex(client=mock_client, collection_name="test_collection")
        chunks = [
            {
                "chunk_id": "doc:0:hash1",
                "embedding": [0.1] * 384,
                "payload": {"note_path": "doc.md", "chunk_index": 0},
            },
            {
                "chunk_id": "doc:1:hash2",
                "embedding": [0.2] * 384,
                "payload": {"note_path": "doc.md", "chunk_index": 1},
            },
        ]
        index.upsert_chunks(chunks)

        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        self.assertEqual(call_args.kwargs["collection_name"], "test_collection")
        points = call_args.kwargs["points"]
        self.assertEqual(len(points), 2)

    def test_search_returns_top_k_results(self):
        from mind_lite.rag.vector_index import QdrantIndex

        mock_client = MagicMock()
        mock_hit = MagicMock()
        mock_hit.id = "doc:0:hash1"
        mock_hit.score = 0.95
        mock_hit.payload = {"note_path": "doc.md", "chunk_index": 0, "content": "chunk text"}
        mock_client.search.return_value = [mock_hit]

        index = QdrantIndex(client=mock_client, collection_name="test_collection")
        results = index.search(query_vector=[0.1] * 384, top_k=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], "doc:0:hash1")
        self.assertEqual(results[0]["score"], 0.95)
        mock_client.search.assert_called_once()

    def test_delete_chunks_removes_by_ids(self):
        from mind_lite.rag.vector_index import QdrantIndex

        mock_client = MagicMock()

        index = QdrantIndex(client=mock_client, collection_name="test_collection")
        index.delete_chunks(["doc:0:hash1", "doc:1:hash2"])

        mock_client.delete.assert_called_once()
        call_args = mock_client.delete.call_args
        self.assertEqual(call_args.kwargs["points_selector"].points, ["doc:0:hash1", "doc:1:hash2"])


if __name__ == "__main__":
    unittest.main()

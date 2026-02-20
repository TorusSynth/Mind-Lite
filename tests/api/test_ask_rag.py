import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock


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


class AskWithRAGTests(unittest.TestCase):
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

    def test_ask_returns_retrieval_citations_when_available(self):
        from mind_lite.api.service import ApiService

        service = ApiService()

        service._rag_retrieval = MagicMock()
        service._rag_retrieval.retrieve.return_value = [
            {
                "note_id": "notes/relevant.md",
                "path": "notes/relevant.md",
                "excerpt": "This is the relevant content for the query.",
                "chunk_id": "notes/relevant.md:0:abc",
                "score": 0.91,
            }
        ]
        service._rag_sqlite_store = MagicMock()

        result = service.ask(
            {
                "query": "what is the relevant content?",
                "path": "",
                "content": "",
                "frontmatter": {},
                "tags": [],
            }
        )

        self.assertIn("citations", result)
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["note_id"], "notes/relevant.md")

    def test_ask_retrieval_trace_present(self):
        from mind_lite.api.service import ApiService

        service = ApiService()

        service._rag_retrieval = MagicMock()
        service._rag_retrieval.retrieve.return_value = []
        service._rag_sqlite_store = MagicMock()

        result = service.ask(
            {
                "query": "test query",
                "path": "",
                "content": "",
                "frontmatter": {},
                "tags": [],
            }
        )

        self.assertIn("retrieval_trace", result)
        self.assertIn("retrieved_count", result["retrieval_trace"])

    def test_ask_degrades_gracefully_when_rag_unavailable(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        service._rag_retrieval = None
        service._rag_sqlite_store = None

        result = service.ask(
            {
                "query": "test query",
                "path": "",
                "content": "",
                "frontmatter": {},
                "tags": [],
            }
        )

        self.assertIn("answer", result)
        self.assertIn("citations", result)
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["retrieval_trace"]["available"], False)


if __name__ == "__main__":
    unittest.main()

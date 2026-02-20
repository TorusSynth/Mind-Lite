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


class RAGApiTests(unittest.TestCase):
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

    def test_rag_index_folder_returns_result(self):
        from mind_lite.api.service import ApiService

        tmpdir = tempfile.mkdtemp()
        fixture = Path(tmpdir) / "note.md"
        fixture.write_text("Test content for indexing here alpha beta gamma.")

        service = ApiService()

        class FakeEmb:
            def tolist(self):
                return [0.1] * 384

        mock_embedder = MagicMock()
        mock_embedder.embed_texts.return_value = [FakeEmb()]

        service._rag_embedder = mock_embedder
        service._rag_qdrant_index = MagicMock()
        service._rag_sqlite_store = MagicMock()
        service._rag_sqlite_store.get_status_summary.return_value = {
            "documents_count": 1,
            "chunks_count": 1,
            "last_run": None,
        }

        result = service.rag_index_folder({"folder_path": str(tmpdir)})
        self.assertIn("files_indexed", result)

    def test_rag_status_returns_summary(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        service._rag_sqlite_store = MagicMock()
        service._rag_sqlite_store.get_status_summary.return_value = {
            "documents_count": 5,
            "chunks_count": 20,
            "last_run": {"status": "completed"},
        }

        result = service.rag_status()
        self.assertEqual(result["documents_count"], 5)
        self.assertEqual(result["chunks_count"], 20)
        self.assertEqual(result["last_run"]["status"], "completed")

    def test_rag_retrieve_returns_citations(self):
        from mind_lite.api.service import ApiService

        service = ApiService()
        service._rag_retrieval = MagicMock()
        service._rag_retrieval.retrieve.return_value = [
            {
                "note_id": "notes/test.md",
                "path": "notes/test.md",
                "excerpt": "Relevant content",
                "chunk_id": "notes/test.md:0:abc",
                "score": 0.92,
            }
        ]

        result = service.rag_retrieve({"query": "test query", "top_k": 5})
        self.assertIn("citations", result)
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["note_id"], "notes/test.md")

    def test_rag_index_vault_delegates_to_index_folder(self):
        from mind_lite.api.service import ApiService

        tmpdir = tempfile.mkdtemp()
        fixture = Path(tmpdir) / "note.md"
        fixture.write_text("Vault content alpha beta gamma delta.")

        service = ApiService()

        class FakeEmb:
            def tolist(self):
                return [0.1] * 384

        mock_embedder = MagicMock()
        mock_embedder.embed_texts.return_value = [FakeEmb()]

        service._rag_embedder = mock_embedder
        service._rag_qdrant_index = MagicMock()
        service._rag_sqlite_store = MagicMock()
        service._rag_sqlite_store.get_status_summary.return_value = {
            "documents_count": 1,
            "chunks_count": 1,
            "last_run": None,
        }

        result = service.rag_index_vault({"vault_path": str(tmpdir)})
        self.assertIn("files_indexed", result)


if __name__ == "__main__":
    unittest.main()

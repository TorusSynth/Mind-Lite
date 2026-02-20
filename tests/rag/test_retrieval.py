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


class RetrievalTests(unittest.TestCase):
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

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_retrieve_returns_top_k_ordered_by_score(self):
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.sqlite_store import SqliteStore

        db_path = str(Path(self.tmpdir) / "test.db")
        store = SqliteStore(db_path)
        store.init_schema()

        store.upsert_document("notes/a.md", "hash_a", 100)
        store.replace_chunks_for_document(
            "notes/a.md",
            [
                {
                    "chunk_id": "notes/a.md:0:h1",
                    "note_path": "notes/a.md",
                    "chunk_index": 0,
                    "content": "First chunk content",
                    "start_offset": 0,
                    "end_offset": 50,
                    "token_count": 50,
                },
                {
                    "chunk_id": "notes/a.md:1:h2",
                    "note_path": "notes/a.md",
                    "chunk_index": 1,
                    "content": "Second chunk content",
                    "start_offset": 50,
                    "end_offset": 100,
                    "token_count": 50,
                },
            ],
        )

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = [
            {"chunk_id": "notes/a.md:1:h2", "score": 0.95, "payload": {}},
            {"chunk_id": "notes/a.md:0:h1", "score": 0.85, "payload": {}},
        ]

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 384

        service = RetrievalService(
            sqlite_store=store,
            qdrant_index=mock_qdrant,
            embedder=mock_embedder,
        )

        results = service.retrieve("test query", top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["score"], 0.95)
        self.assertEqual(results[1]["score"], 0.85)

    def test_retrieve_citation_includes_required_fields(self):
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.sqlite_store import SqliteStore

        db_path = str(Path(self.tmpdir) / "test.db")
        store = SqliteStore(db_path)
        store.init_schema()

        store.upsert_document("notes/example.md", "hash_x", 50)
        store.replace_chunks_for_document(
            "notes/example.md",
            [
                {
                    "chunk_id": "notes/example.md:0:abc",
                    "note_path": "notes/example.md",
                    "chunk_index": 0,
                    "content": "This is the relevant excerpt text.",
                    "start_offset": 0,
                    "end_offset": 50,
                    "token_count": 50,
                },
            ],
        )

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = [
            {
                "chunk_id": "notes/example.md:0:abc",
                "score": 0.92,
                "payload": {"note_path": "notes/example.md"},
            },
        ]

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 384

        service = RetrievalService(
            sqlite_store=store,
            qdrant_index=mock_qdrant,
            embedder=mock_embedder,
        )

        citations = service.retrieve("relevant query", top_k=5)

        self.assertEqual(len(citations), 1)
        cite = citations[0]
        self.assertIn("note_id", cite)
        self.assertIn("path", cite)
        self.assertIn("excerpt", cite)
        self.assertIn("chunk_id", cite)
        self.assertIn("score", cite)
        self.assertEqual(cite["note_id"], "notes/example.md")
        self.assertEqual(cite["path"], "notes/example.md")
        self.assertEqual(cite["excerpt"], "This is the relevant excerpt text.")

    def test_retrieve_returns_empty_list_on_no_results(self):
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.sqlite_store import SqliteStore

        db_path = str(Path(self.tmpdir) / "test.db")
        store = SqliteStore(db_path)
        store.init_schema()

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = []

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 384

        service = RetrievalService(
            sqlite_store=store,
            qdrant_index=mock_qdrant,
            embedder=mock_embedder,
        )

        results = service.retrieve("unknown query", top_k=5)

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()

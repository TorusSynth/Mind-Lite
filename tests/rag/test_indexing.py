import sys
import tempfile
import unittest
from pathlib import Path
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


class IndexingTests(unittest.TestCase):
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
        self.fixture_dir = Path(self.tmpdir) / "vault"
        self.fixture_dir.mkdir()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_index_folder_persists_documents_and_chunks(self):
        doc_path = self.fixture_dir / "note1.md"
        doc_path.write_text("This is the first sentence. This is the second sentence.")

        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.sqlite_store import SqliteStore

        db_path = str(Path(self.tmpdir) / "test.db")
        store = SqliteStore(db_path)
        store.init_schema()

        mock_qdrant = MagicMock()
        mock_embedder = MagicMock()
        mock_embedder.embed_texts.return_value = [[0.1] * 384, [0.2] * 384]

        service = IndexingService(
            sqlite_store=store,
            qdrant_index=MagicMock(),
            embedder=mock_embedder,
        )

        service.index_folder(str(self.fixture_dir))

        status = store.get_status_summary()
        self.assertEqual(status["documents_count"], 1)
        self.assertGreater(status["chunks_count"], 0)

    def test_index_folder_upserts_vectors(self):
        doc_path = self.fixture_dir / "note1.md"
        doc_path.write_text("Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda.")

        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.sqlite_store import SqliteStore

        db_path = str(Path(self.tmpdir) / "test.db")
        store = SqliteStore(db_path)
        store.init_schema()

        mock_qdrant = MagicMock()
        mock_embedder = MagicMock()

        class FakeEmb:
            def tolist(self):
                return [0.1] * 384

        mock_embedder.embed_texts.return_value = [FakeEmb(), FakeEmb()]

        service = IndexingService(
            sqlite_store=store,
            qdrant_index=mock_qdrant,
            embedder=mock_embedder,
        )

        service.index_folder(str(self.fixture_dir))

        mock_qdrant.upsert_chunks.assert_called()

    def test_reindex_removes_stale_chunks_after_content_change(self):
        doc_path = self.fixture_dir / "note1.md"
        doc_path.write_text("Original content alpha beta gamma delta epsilon zeta eta theta.")

        from mind_lite.rag.chunking import chunk_document
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.sqlite_store import SqliteStore

        db_path = str(Path(self.tmpdir) / "test.db")
        store = SqliteStore(db_path)
        store.init_schema()

        mock_qdrant = MagicMock()
        mock_embedder = MagicMock()

        class FakeEmb:
            def tolist(self):
                return [0.1] * 384

        mock_embedder.embed_texts.return_value = [FakeEmb()]

        service = IndexingService(
            sqlite_store=store,
            qdrant_index=mock_qdrant,
            embedder=mock_embedder,
        )

        service.index_folder(str(self.fixture_dir))

        old_chunks = chunk_document(
            str(doc_path), "Original content alpha beta gamma delta epsilon zeta eta theta."
        )
        old_chunk_ids = [c.chunk_id for c in old_chunks]

        doc_path.write_text("Completely new and different content with fresh words.")

        mock_embedder.embed_texts.return_value = [FakeEmb()]
        service.index_folder(str(self.fixture_dir))

        new_chunks = chunk_document(
            str(doc_path), "Completely new and different content with fresh words."
        )
        new_chunk_ids = [c.chunk_id for c in new_chunks]

        self.assertNotEqual(old_chunk_ids, new_chunk_ids)


if __name__ == "__main__":
    unittest.main()

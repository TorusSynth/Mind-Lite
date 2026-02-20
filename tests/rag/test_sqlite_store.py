import sqlite3
import tempfile
import unittest
from pathlib import Path


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test_rag.db"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_schema_creates_tables(self):
        from mind_lite.rag.sqlite_store import SqliteStore

        store = SqliteStore(str(self.db_path))
        store.init_schema()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        self.assertIn("documents", tables)
        self.assertIn("chunks", tables)
        self.assertIn("ingestion_runs", tables)

    def test_upsert_document_and_chunks(self):
        from mind_lite.rag.sqlite_store import SqliteStore

        store = SqliteStore(str(self.db_path))
        store.init_schema()

        store.upsert_document(
            note_path="notes/example.md",
            content_hash="abc123",
            token_count=100,
        )

        chunks = [
            {
                "chunk_id": "notes/example.md:0:hash1",
                "note_path": "notes/example.md",
                "chunk_index": 0,
                "content": "First chunk",
                "start_offset": 0,
                "end_offset": 50,
                "token_count": 50,
            },
            {
                "chunk_id": "notes/example.md:1:hash2",
                "note_path": "notes/example.md",
                "chunk_index": 1,
                "content": "Second chunk",
                "start_offset": 50,
                "end_offset": 100,
                "token_count": 50,
            },
        ]
        store.replace_chunks_for_document("notes/example.md", chunks)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT note_path, content_hash FROM documents")
        docs = cursor.fetchall()
        cursor.execute("SELECT chunk_id, note_path FROM chunks ORDER BY chunk_index")
        db_chunks = cursor.fetchall()
        conn.close()

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0], ("notes/example.md", "abc123"))
        self.assertEqual(len(db_chunks), 2)
        self.assertEqual(db_chunks[0][1], "notes/example.md")

    def test_replace_chunks_deletes_stale_chunks(self):
        from mind_lite.rag.sqlite_store import SqliteStore

        store = SqliteStore(str(self.db_path))
        store.init_schema()

        store.upsert_document(
            note_path="notes/example.md",
            content_hash="v1",
            token_count=100,
        )
        old_chunks = [
            {
                "chunk_id": "notes/example.md:0:old",
                "note_path": "notes/example.md",
                "chunk_index": 0,
                "content": "Old content",
                "start_offset": 0,
                "end_offset": 100,
                "token_count": 100,
            },
        ]
        store.replace_chunks_for_document("notes/example.md", old_chunks)

        new_chunks = [
            {
                "chunk_id": "notes/example.md:0:new1",
                "note_path": "notes/example.md",
                "chunk_index": 0,
                "content": "New content part 1",
                "start_offset": 0,
                "end_offset": 50,
                "token_count": 50,
            },
            {
                "chunk_id": "notes/example.md:1:new2",
                "note_path": "notes/example.md",
                "chunk_index": 1,
                "content": "New content part 2",
                "start_offset": 50,
                "end_offset": 100,
                "token_count": 50,
            },
        ]
        store.replace_chunks_for_document("notes/example.md", new_chunks)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT chunk_id FROM chunks ORDER BY chunk_index")
        remaining = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.assertEqual(remaining, ["notes/example.md:0:new1", "notes/example.md:1:new2"])
        self.assertNotIn("notes/example.md:0:old", remaining)

    def test_record_ingestion_run(self):
        from mind_lite.rag.sqlite_store import SqliteStore

        store = SqliteStore(str(self.db_path))
        store.init_schema()

        store.record_ingestion_run(
            run_type="vault",
            files_indexed=42,
            chunks_created=150,
            status="completed",
        )

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT run_type, files_indexed, chunks_created, status FROM ingestion_runs"
        )
        runs = cursor.fetchall()
        conn.close()

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0], ("vault", 42, 150, "completed"))

    def test_get_status_summary(self):
        from mind_lite.rag.sqlite_store import SqliteStore

        store = SqliteStore(str(self.db_path))
        store.init_schema()

        store.upsert_document("notes/a.md", "hash_a", 100)
        store.upsert_document("notes/b.md", "hash_b", 200)
        store.replace_chunks_for_document(
            "notes/a.md",
            [{"chunk_id": "a:0:h", "note_path": "notes/a.md", "chunk_index": 0, "content": "x", "start_offset": 0, "end_offset": 100, "token_count": 100}],
        )
        store.record_ingestion_run("vault", 2, 1, "completed")

        status = store.get_status_summary()

        self.assertEqual(status["documents_count"], 2)
        self.assertEqual(status["chunks_count"], 1)
        self.assertEqual(status["last_run"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()

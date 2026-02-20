import sqlite3
from pathlib import Path
from typing import Any


class SqliteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                note_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                note_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                token_count INTEGER NOT NULL,
                FOREIGN KEY (note_path) REFERENCES documents(note_path)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT NOT NULL,
                files_indexed INTEGER NOT NULL,
                chunks_created INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def upsert_document(
        self, note_path: str, content_hash: str, token_count: int
    ) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (note_path, content_hash, token_count)
            VALUES (?, ?, ?)
            ON CONFLICT(note_path) DO UPDATE SET
                content_hash = excluded.content_hash,
                token_count = excluded.token_count,
                indexed_at = CURRENT_TIMESTAMP
            """,
            (note_path, content_hash, token_count),
        )
        conn.commit()
        conn.close()

    def replace_chunks_for_document(
        self, note_path: str, chunks: list[dict[str, Any]]
    ) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chunks WHERE note_path = ?",
            (note_path,),
        )
        for chunk in chunks:
            cursor.execute(
                """
                INSERT INTO chunks
                    (chunk_id, note_path, chunk_index, content, start_offset, end_offset, token_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["chunk_id"],
                    chunk["note_path"],
                    chunk["chunk_index"],
                    chunk["content"],
                    chunk["start_offset"],
                    chunk["end_offset"],
                    chunk["token_count"],
                ),
            )
        conn.commit()
        conn.close()

    def record_ingestion_run(
        self, run_type: str, files_indexed: int, chunks_created: int, status: str
    ) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ingestion_runs (run_type, files_indexed, chunks_created, status)
            VALUES (?, ?, ?, ?)
            """,
            (run_type, files_indexed, chunks_created, status),
        )
        conn.commit()
        conn.close()

    def get_status_summary(self) -> dict[str, Any]:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM documents")
        documents_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunks_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT run_type, files_indexed, chunks_created, status, started_at
            FROM ingestion_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
        last_run_row = cursor.fetchone()
        conn.close()

        last_run = None
        if last_run_row:
            last_run = {
                "run_type": last_run_row[0],
                "files_indexed": last_run_row[1],
                "chunks_created": last_run_row[2],
                "status": last_run_row[3],
                "started_at": last_run_row[4],
            }

        return {
            "documents_count": documents_count,
            "chunks_count": chunks_count,
            "last_run": last_run,
        }

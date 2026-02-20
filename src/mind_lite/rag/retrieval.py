import sqlite3
from typing import Any


class RetrievalService:
    def __init__(self, sqlite_store: Any, qdrant_index: Any, embedder: Any):
        self.sqlite_store = sqlite_store
        self.qdrant_index = qdrant_index
        self.embedder = embedder

    def _get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        conn = sqlite3.connect(self.sqlite_store.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return dict(row)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_vector = self.embedder.embed_query(query)
        search_results = self.qdrant_index.search(query_vector=query_vector, top_k=top_k)

        citations = []
        for result in search_results:
            chunk_id = result["chunk_id"]
            chunk = self._get_chunk_by_id(chunk_id)

            if chunk is None:
                continue

            citations.append(
                {
                    "note_id": chunk["note_path"],
                    "path": chunk["note_path"],
                    "excerpt": chunk["content"],
                    "chunk_id": chunk_id,
                    "score": result["score"],
                }
            )

        return citations

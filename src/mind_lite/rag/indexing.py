import hashlib
from pathlib import Path
from typing import Any


class IndexingService:
    def __init__(
        self,
        sqlite_store: Any,
        qdrant_index: Any,
        embedder: Any,
        max_tokens: int = 200,
        overlap_tokens: int = 20,
    ):
        self.sqlite_store = sqlite_store
        self.qdrant_index = qdrant_index
        self.embedder = embedder
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def _compute_content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _collect_markdown_files(self, folder_path: str) -> list[Path]:
        folder = Path(folder_path)
        return sorted(folder.rglob("*.md"))

    def _index_document(self, note_path: str, content: str) -> list[dict[str, Any]]:
        from mind_lite.rag.chunking import chunk_document

        content_hash = self._compute_content_hash(content)
        token_count = len(content.split())

        self.sqlite_store.upsert_document(
            note_path=note_path,
            content_hash=content_hash,
            token_count=token_count,
        )

        chunks = chunk_document(
            note_path=note_path,
            text=content,
            max_tokens=self.max_tokens,
            overlap_tokens=self.overlap_tokens,
        )

        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "note_path": c.note_path,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "start_offset": c.start_offset,
                "end_offset": c.end_offset,
                "token_count": c.token_count,
            }
            for c in chunks
        ]

        self.sqlite_store.replace_chunks_for_document(note_path, chunk_dicts)

        return chunk_dicts

    def index_folder(self, folder_path: str) -> dict[str, Any]:
        files = self._collect_markdown_files(folder_path)
        files_indexed = 0
        chunks_created = 0

        for file_path in files:
            content = file_path.read_text(encoding="utf-8")
            note_path = str(file_path)

            chunk_dicts = self._index_document(note_path, content)

            if chunk_dicts:
                chunk_contents = [c["content"] for c in chunk_dicts]
                embeddings = self.embedder.embed_texts(chunk_contents)

                qdrant_chunks = [
                    {
                        "chunk_id": c["chunk_id"],
                        "embedding": emb,
                        "payload": {
                            "note_path": c["note_path"],
                            "chunk_index": c["chunk_index"],
                            "content": c["content"],
                        },
                    }
                    for c, emb in zip(chunk_dicts, embeddings)
                ]
                self.qdrant_index.upsert_chunks(qdrant_chunks)

            files_indexed += 1
            chunks_created += len(chunk_dicts)

        self.sqlite_store.record_ingestion_run(
            run_type="folder",
            files_indexed=files_indexed,
            chunks_created=chunks_created,
            status="completed",
        )

        return {
            "files_indexed": files_indexed,
            "chunks_created": chunks_created,
        }

    def index_vault(self, vault_path: str) -> dict[str, Any]:
        return self.index_folder(vault_path)

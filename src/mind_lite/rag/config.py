import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RagConfig:
    qdrant_url: str
    collection_name: str
    sqlite_path: str
    embed_model: str


def get_rag_config() -> RagConfig:
    return RagConfig(
        qdrant_url=os.getenv("MIND_LITE_QDRANT_URL", "http://localhost:6333"),
        collection_name=os.getenv("MIND_LITE_RAG_COLLECTION", "mind_lite_chunks"),
        sqlite_path=os.getenv("MIND_LITE_RAG_SQLITE_PATH", ".mind_lite/rag.db"),
        embed_model=os.getenv(
            "MIND_LITE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    )

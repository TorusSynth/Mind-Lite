import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    note_path: str
    chunk_index: int
    content: str
    start_offset: int
    end_offset: int
    token_count: int


def _build_chunk_id(note_path: str, chunk_index: int, content: str) -> str:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"{note_path}:{chunk_index}:{content_hash}"


def chunk_document(
    note_path: str,
    text: str,
    max_tokens: int = 200,
    overlap_tokens: int = 20,
) -> list[ChunkRecord]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be > 0")
    if overlap_tokens < 0:
        raise ValueError("overlap_tokens must be >= 0")
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")

    tokens = text.split()
    if not tokens:
        return []

    chunks: list[ChunkRecord] = []
    step = max_tokens - overlap_tokens
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_content = " ".join(chunk_tokens)
        chunks.append(
            ChunkRecord(
                chunk_id=_build_chunk_id(note_path, chunk_index, chunk_content),
                note_path=note_path,
                chunk_index=chunk_index,
                content=chunk_content,
                start_offset=start,
                end_offset=end,
                token_count=len(chunk_tokens),
            )
        )
        if end >= len(tokens):
            break
        start += step
        chunk_index += 1

    return chunks


def chunk_documents(
    documents: dict[str, str],
    max_tokens: int = 200,
    overlap_tokens: int = 20,
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for note_path in sorted(documents):
        chunks.extend(
            chunk_document(
                note_path=note_path,
                text=documents[note_path],
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
            )
        )
    return chunks

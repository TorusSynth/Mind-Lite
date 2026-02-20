from typing import Any, Optional


class QdrantIndex:
    def __init__(self, client: Any, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.models import VectorParams

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance="Cosine"),
            )

    def upsert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for chunk in chunks:
            points.append(
                PointStruct(
                    id=chunk["chunk_id"],
                    vector=chunk["embedding"],
                    payload=chunk.get("payload", {}),
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "chunk_id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        from qdrant_client.models import PointIdsList

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=chunk_ids),
        )

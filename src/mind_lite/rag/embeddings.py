from typing import Any, Optional


class EmbeddingAdapter:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: Optional[Any] = None

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._load_model()
        embeddings = model.encode(texts)
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        model = self._load_model()
        embedding = model.encode([query])
        return embedding[0].tolist()

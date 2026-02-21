import os
import pytest


pytestmark = pytest.mark.integration


class TestEmbeddingGeneration:
    def test_embedding_dimensions(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter
        
        adapter = EmbeddingAdapter(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        vectors = adapter.embed_texts(["test sentence"])
        
        assert len(vectors) == 1
        assert len(vectors[0]) == 384

    def test_embedding_multiple_texts(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter
        
        adapter = EmbeddingAdapter(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        texts = [
            "First test sentence",
            "Second test sentence",
            "Third test sentence",
        ]
        
        vectors = adapter.embed_texts(texts)
        
        assert len(vectors) == 3
        for v in vectors:
            assert len(v) == 384

    def test_embedding_empty_list(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter
        
        adapter = EmbeddingAdapter()
        
        vectors = adapter.embed_texts([])
        
        assert vectors == []

    def test_embedding_query_returns_vector(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter
        
        adapter = EmbeddingAdapter()
        
        vector = adapter.embed_query("test query")
        
        assert len(vector) == 384

    def test_embeddings_are_deterministic(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter
        
        adapter = EmbeddingAdapter()
        
        text = "This is a deterministic test"
        
        v1 = adapter.embed_texts([text])[0]
        v2 = adapter.embed_texts([text])[0]
        
        for a, b in zip(v1, v2):
            assert abs(a - b) < 1e-6

    def test_similar_texts_have_similar_embeddings(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter
        import math
        
        adapter = EmbeddingAdapter()
        
        texts = [
            "The quick brown fox jumps over the lazy dog",
            "A fast brown fox leaps over a sleepy dog",
            "Machine learning is a subset of artificial intelligence",
        ]
        
        vectors = adapter.embed_texts(texts)
        
        def cosine_similarity(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b)
        
        sim_01 = cosine_similarity(vectors[0], vectors[1])
        sim_02 = cosine_similarity(vectors[0], vectors[2])
        
        assert sim_01 > sim_02
        assert sim_01 > 0.7

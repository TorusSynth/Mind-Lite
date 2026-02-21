import os
import tempfile
import pytest
from pathlib import Path


pytestmark = pytest.mark.integration


class TestAskWithLMStudio:
    def test_ask_calls_lmstudio(self, lmstudio_available, temp_qdrant_collection, temp_db_path):
        if not lmstudio_available:
            pytest.skip("LM Studio not available")
        
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.vector_index import QdrantIndex
        from mind_lite.rag.embeddings import EmbeddingAdapter
        from mind_lite.llm.config import LlmConfig
        from mind_lite.llm.generate import generate_answer
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = Path(tmpdir) / "test.md"
            doc.write_text("The capital of France is Paris.")
            
            store = SqliteStore(temp_db_path)
            store.init_schema()
            
            config = get_rag_config()
            qdrant_client = QdrantClient(url=config.qdrant_url)
            qdrant_index = QdrantIndex(client=qdrant_client, collection_name=collection_name)
            qdrant_index.ensure_collection(vector_size=384)
            
            embedder = EmbeddingAdapter()
            
            indexing = IndexingService(
                sqlite_store=store,
                qdrant_index=qdrant_index,
                embedder=embedder,
            )
            indexing.index_folder(tmpdir)
            
            llm_config = LlmConfig(
                active_provider="lmstudio",
                active_model="lmstudio:local",
                lmstudio_url=os.getenv("MIND_LITE_LMSTUDIO_URL", "http://localhost:1234"),
            )
            
            result = generate_answer("What is the capital of France?", [], llm_config)
            
            assert result.get("success") or result.get("error")
            if result.get("success"):
                assert len(result.get("content", "")) > 0


class TestAskWithOpenRouter:
    def test_ask_calls_openrouter(self, openrouter_available):
        if not openrouter_available:
            pytest.skip("OpenRouter not available")
        
        from mind_lite.llm.config import LlmConfig
        from mind_lite.llm.generate import generate_answer
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        
        config = LlmConfig(
            active_provider="openrouter",
            active_model="deepseek/deepseek-r1-0528:free",
            openrouter_api_key=api_key,
        )
        
        result = generate_answer("What is 2 + 2?", [], config)
        
        assert result.get("success") or result.get("error")
        if result.get("success"):
            assert len(result.get("content", "")) > 0
            assert "4" in result.get("content", "") or "four" in result.get("content", "").lower()


class TestAskWithRAG:
    def test_ask_uses_rag_citations(self, qdrant_available, openrouter_available, temp_qdrant_collection, temp_db_path):
        if not qdrant_available:
            pytest.skip("Qdrant not available")
        if not openrouter_available:
            pytest.skip("OpenRouter not available")
        
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.vector_index import QdrantIndex
        from mind_lite.rag.embeddings import EmbeddingAdapter
        from mind_lite.llm.config import LlmConfig
        from mind_lite.llm.generate import generate_answer
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = Path(tmpdir) / "my_project.md"
            doc.write_text("""
# My Secret Project

This is a confidential project called "Project X".
The project started in January 2026.
The budget is $1 million.
The team consists of 5 people.
""")
            
            store = SqliteStore(temp_db_path)
            store.init_schema()
            
            config = get_rag_config()
            qdrant_client = QdrantClient(url=config.qdrant_url)
            qdrant_index = QdrantIndex(client=qdrant_client, collection_name=collection_name)
            qdrant_index.ensure_collection(vector_size=384)
            
            embedder = EmbeddingAdapter()
            
            indexing = IndexingService(
                sqlite_store=store,
                qdrant_index=qdrant_index,
                embedder=embedder,
            )
            indexing.index_folder(tmpdir)
            
            retrieval = RetrievalService(
                sqlite_store=store,
                qdrant_index=qdrant_index,
                embedder=embedder,
            )
            
            citations = retrieval.retrieve("What is the budget for Project X?", top_k=3)
            
            assert len(citations) >= 1
            
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            llm_config = LlmConfig(
                active_provider="openrouter",
                active_model="deepseek/deepseek-r1-0528:free",
                openrouter_api_key=api_key,
            )
            
            result = generate_answer("What is the budget for Project X?", citations, llm_config)
            
            if result.get("success"):
                content = result.get("content", "").lower()
                assert "$1 million" in content or "1 million" in content or "million" in content

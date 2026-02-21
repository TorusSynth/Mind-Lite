import os
import tempfile
import pytest
from pathlib import Path


pytestmark = pytest.mark.integration


class TestRAGIndexing:
    def test_index_folder_creates_documents(self, temp_qdrant_collection, temp_db_path):
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.vector_index import QdrantIndex
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test_note.md"
            doc_path.write_text("# Test Note\n\nThis is test content for indexing. " * 10)
            
            store = SqliteStore(temp_db_path)
            store.init_schema()
            
            config = get_rag_config()
            qdrant_client = QdrantClient(url=config.qdrant_url)
            qdrant_index = QdrantIndex(client=qdrant_client, collection_name=collection_name)
            qdrant_index.ensure_collection(vector_size=384)
            
            from mind_lite.rag.embeddings import EmbeddingAdapter
            embedder = EmbeddingAdapter()
            
            indexing = IndexingService(
                sqlite_store=store,
                qdrant_index=qdrant_index,
                embedder=embedder,
            )
            
            result = indexing.index_folder(tmpdir)
            
            assert result["files_indexed"] == 1
            assert result["chunks_created"] > 0
            
            status = store.get_status_summary()
            assert status["documents_count"] == 1
            assert status["chunks_count"] > 0

    def test_index_and_retrieve(self, temp_qdrant_collection, temp_db_path):
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.vector_index import QdrantIndex
        from mind_lite.rag.embeddings import EmbeddingAdapter
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "project_atlas.md"
            doc_path.write_text("""
# Project Atlas

## Overview
Project Atlas is a major initiative to improve knowledge management.

## Goals
- Centralize all documentation
- Improve search capabilities
- Enable AI-powered Q&A

## Status
Currently in active development with weekly sprints.
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
            
            citations = retrieval.retrieve("What is Project Atlas?", top_k=3)
            
            assert len(citations) >= 1
            assert "project_atlas" in citations[0]["note_id"].lower() or "atlas" in citations[0]["excerpt"].lower()

    def test_reindex_updates_content(self, temp_qdrant_collection, temp_db_path):
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.vector_index import QdrantIndex
        from mind_lite.rag.embeddings import EmbeddingAdapter
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "changing_note.md"
            doc_path.write_text("Original content that will be replaced.")
            
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
            
            doc_path.write_text("Completely new and different content about machine learning and AI.")
            
            result = indexing.index_folder(tmpdir)
            
            assert result["files_indexed"] == 1
            
            import sqlite3
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM chunks WHERE note_path LIKE '%changing_note%'")
            chunks = cursor.fetchall()
            conn.close()
            
            assert len(chunks) > 0
            assert any("machine learning" in c[0] for c in chunks)


class TestRAGRetrieval:
    def test_retrieve_returns_citations(self, temp_qdrant_collection, temp_db_path):
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.indexing import IndexingService
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.vector_index import QdrantIndex
        from mind_lite.rag.embeddings import EmbeddingAdapter
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = Path(tmpdir) / "note.md"
            doc.write_text("Python is a programming language used for data science and web development.")
            
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
            
            citations = retrieval.retrieve("What is Python used for?", top_k=5)
            
            assert len(citations) >= 1
            cite = citations[0]
            assert "note_id" in cite
            assert "path" in cite
            assert "excerpt" in cite
            assert "chunk_id" in cite
            assert "score" in cite

    def test_retrieve_empty_if_not_indexed(self, temp_qdrant_collection, temp_db_path):
        from mind_lite.rag.sqlite_store import SqliteStore
        from mind_lite.rag.retrieval import RetrievalService
        from mind_lite.rag.vector_index import QdrantIndex
        from mind_lite.rag.embeddings import EmbeddingAdapter
        from qdrant_client import QdrantClient
        from mind_lite.rag.config import get_rag_config
        
        client, collection_name = temp_qdrant_collection
        
        store = SqliteStore(temp_db_path)
        store.init_schema()
        
        config = get_rag_config()
        qdrant_client = QdrantClient(url=config.qdrant_url)
        qdrant_index = QdrantIndex(client=qdrant_client, collection_name=collection_name)
        qdrant_index.ensure_collection(vector_size=384)
        
        embedder = EmbeddingAdapter()
        
        retrieval = RetrievalService(
            sqlite_store=store,
            qdrant_index=qdrant_index,
            embedder=embedder,
        )
        
        citations = retrieval.retrieve("random query about nothing", top_k=5)
        
        assert citations == []

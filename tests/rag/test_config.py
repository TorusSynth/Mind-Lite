import os
import unittest
from unittest.mock import patch


class RagConfigTests(unittest.TestCase):
    def test_default_rag_config_values(self):
        from mind_lite.rag.config import get_rag_config

        cfg = get_rag_config()

        self.assertEqual(cfg.qdrant_url, "http://localhost:6333")
        self.assertEqual(cfg.collection_name, "mind_lite_chunks")
        self.assertEqual(cfg.sqlite_path, ".mind_lite/rag.db")
        self.assertEqual(cfg.embed_model, "sentence-transformers/all-MiniLM-L6-v2")

    def test_env_overrides_defaults(self):
        from mind_lite.rag.config import get_rag_config

        with patch.dict(
            os.environ,
            {
                "MIND_LITE_QDRANT_URL": "http://qdrant:6333",
                "MIND_LITE_RAG_COLLECTION": "custom_chunks",
                "MIND_LITE_RAG_SQLITE_PATH": "data/rag.sqlite3",
                "MIND_LITE_EMBED_MODEL": "custom-model",
            },
            clear=False,
        ):
            cfg = get_rag_config()

        self.assertEqual(cfg.qdrant_url, "http://qdrant:6333")
        self.assertEqual(cfg.collection_name, "custom_chunks")
        self.assertEqual(cfg.sqlite_path, "data/rag.sqlite3")
        self.assertEqual(cfg.embed_model, "custom-model")


if __name__ == "__main__":
    unittest.main()

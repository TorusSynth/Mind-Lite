import unittest
from unittest.mock import MagicMock, patch


class EmbeddingTests(unittest.TestCase):
    def test_model_loads_lazily(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter

        class FakeEmb:
            def tolist(self):
                return [0.1] * 384

        mock_model = MagicMock()
        mock_model.encode.return_value = [FakeEmb()]

        adapter = EmbeddingAdapter(model_name="test-model")
        self.assertIsNone(adapter._model)

        adapter._model = mock_model
        adapter.embed_texts(["hello world"])

        mock_model.encode.assert_called_once_with(["hello world"])

    def test_returns_vectors_with_stable_dimensions(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter

        mock_model = MagicMock()
        mock_model.encode.return_value = [MagicMock(tostring=lambda: [0.1] * 384), MagicMock(tostring=lambda: [0.2] * 384)]
        
        class FakeEmb:
            def __init__(self, vals):
                self._vals = vals
            def tolist(self):
                return self._vals

        mock_model.encode.return_value = [FakeEmb([0.1] * 384), FakeEmb([0.2] * 384)]

        adapter = EmbeddingAdapter(model_name="test-model")
        adapter._model = mock_model
        vectors = adapter.embed_texts(["first text", "second text"])

        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), 384)
        self.assertEqual(len(vectors[1]), 384)

    def test_embed_query_returns_single_vector(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter

        class FakeEmb:
            def tolist(self):
                return [0.5] * 384

        mock_model = MagicMock()
        mock_model.encode.return_value = [FakeEmb()]

        adapter = EmbeddingAdapter(model_name="test-model")
        adapter._model = mock_model
        vector = adapter.embed_query("single query")

        self.assertEqual(len(vector), 384)

    def test_handles_empty_input_list(self):
        from mind_lite.rag.embeddings import EmbeddingAdapter

        adapter = EmbeddingAdapter(model_name="test-model")
        adapter._model = MagicMock()
        vectors = adapter.embed_texts([])

        self.assertEqual(vectors, [])
        adapter._model.encode.assert_not_called()


if __name__ == "__main__":
    unittest.main()

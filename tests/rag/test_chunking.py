import hashlib
import unittest


class ChunkingTests(unittest.TestCase):
    def test_chunk_boundaries_and_overlap(self):
        from mind_lite.rag.chunking import chunk_document

        text = "zero one two three four five six seven eight nine"
        chunks = chunk_document(
            note_path="notes/example.md",
            text=text,
            max_tokens=4,
            overlap_tokens=1,
        )

        self.assertEqual(len(chunks), 3)
        self.assertEqual([c.start_offset for c in chunks], [0, 3, 6])
        self.assertEqual([c.end_offset for c in chunks], [4, 7, 10])
        self.assertEqual([c.token_count for c in chunks], [4, 4, 4])
        self.assertEqual(
            [c.content for c in chunks],
            [
                "zero one two three",
                "three four five six",
                "six seven eight nine",
            ],
        )

    def test_chunk_id_is_stable_from_path_index_and_content_hash(self):
        from mind_lite.rag.chunking import chunk_document

        chunks = chunk_document(
            note_path="notes/example.md",
            text="alpha beta gamma delta",
            max_tokens=2,
            overlap_tokens=0,
        )

        expected_first_hash = hashlib.sha256("alpha beta".encode("utf-8")).hexdigest()
        expected_second_hash = hashlib.sha256("gamma delta".encode("utf-8")).hexdigest()

        self.assertEqual(
            chunks[0].chunk_id,
            f"notes/example.md:0:{expected_first_hash}",
        )
        self.assertEqual(
            chunks[1].chunk_id,
            f"notes/example.md:1:{expected_second_hash}",
        )

        second_pass = chunk_document(
            note_path="notes/example.md",
            text="alpha beta gamma delta",
            max_tokens=2,
            overlap_tokens=0,
        )
        self.assertEqual([c.chunk_id for c in chunks], [c.chunk_id for c in second_pass])

    def test_chunk_documents_order_is_deterministic(self):
        from mind_lite.rag.chunking import chunk_documents

        documents = {
            "notes/zeta.md": "one two",
            "notes/alpha.md": "one two",
            "notes/mid.md": "one two",
        }

        first = chunk_documents(documents, max_tokens=2, overlap_tokens=0)
        second = chunk_documents(documents, max_tokens=2, overlap_tokens=0)

        self.assertEqual(
            [c.note_path for c in first],
            ["notes/alpha.md", "notes/mid.md", "notes/zeta.md"],
        )
        self.assertEqual(
            [(c.note_path, c.chunk_id) for c in first],
            [(c.note_path, c.chunk_id) for c in second],
        )


if __name__ == "__main__":
    unittest.main()

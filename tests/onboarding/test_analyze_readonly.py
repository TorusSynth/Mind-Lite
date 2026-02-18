import tempfile
import unittest
from pathlib import Path

from mind_lite.onboarding.analyze_readonly import analyze_folder


class AnalyzeReadonlyTests(unittest.TestCase):
    def test_profiles_markdown_files_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]\n", encoding="utf-8")
            (root / "b.markdown").write_text("No links here\n", encoding="utf-8")
            (root / "notes.txt").write_text("[[ignored]]\n", encoding="utf-8")

            profile = analyze_folder(str(root))

            self.assertEqual(profile.note_count, 2)
            self.assertEqual(profile.orphan_notes, 1)
            self.assertEqual(profile.link_density, 0.5)

    def test_counts_orphans_without_wikilinks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("No links\n", encoding="utf-8")
            (root / "b.md").write_text("[[a]] and [[c]]\n", encoding="utf-8")
            (root / "c.md").write_text("No links either\n", encoding="utf-8")

            profile = analyze_folder(str(root))

            self.assertEqual(profile.note_count, 3)
            self.assertEqual(profile.orphan_notes, 2)
            self.assertEqual(profile.link_density, 2 / 3)

    def test_rejects_nonexistent_folder(self):
        with self.assertRaises(ValueError):
            analyze_folder("/tmp/definitely-not-a-real-folder-mind-lite")


if __name__ == "__main__":
    unittest.main()

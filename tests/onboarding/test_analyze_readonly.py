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

    def test_includes_note_profiles_with_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "project.md").write_text(
                "# Project Plan\n#planning #active\nSee [[Roadmap]] and [[Tasks]]\n",
                encoding="utf-8",
            )

            profile = analyze_folder(str(root))

            self.assertEqual(len(profile.notes), 1)
            note = profile.notes[0]
            self.assertEqual(note.note_id, "project")
            self.assertEqual(note.title, "Project Plan")
            self.assertEqual(note.folder, "")
            self.assertEqual(note.tags, ["planning", "active"])
            self.assertEqual(note.content_preview, "# Project Plan")
            self.assertEqual(note.link_count, 2)

    def test_note_profiles_are_sorted_by_relative_posix_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "z-last.md").write_text("Root z\n", encoding="utf-8")
            (root / "alpha").mkdir()
            (root / "alpha" / "zeta.md").write_text("Alpha zeta\n", encoding="utf-8")
            (root / "alpha" / "beta.md").write_text("Alpha beta\n", encoding="utf-8")
            (root / "beta").mkdir()
            (root / "beta" / "a-first.markdown").write_text("Beta first\n", encoding="utf-8")
            (root / "a-root.md").write_text("Root a\n", encoding="utf-8")

            profile = analyze_folder(str(root))

            self.assertEqual(
                [note.note_id for note in profile.notes],
                ["a-root", "beta", "zeta", "a-first", "z-last"],
            )
            self.assertEqual(
                [note.folder for note in profile.notes],
                ["", "alpha", "alpha", "beta", ""],
            )


if __name__ == "__main__":
    unittest.main()

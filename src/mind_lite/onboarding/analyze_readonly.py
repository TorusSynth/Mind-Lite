import re
from dataclasses import dataclass
from pathlib import Path

WIKILINK_PATTERN = re.compile(r"\[\[[^\]]+\]\]")


@dataclass(frozen=True)
class FolderProfile:
    note_count: int
    orphan_notes: int
    link_density: float


def analyze_folder(folder_path: str) -> FolderProfile:
    root = Path(folder_path)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"folder does not exist or is not a directory: {folder_path}")

    markdown_files = _collect_markdown_files(root)
    if not markdown_files:
        return FolderProfile(note_count=0, orphan_notes=0, link_density=0.0)

    total_links = 0
    orphan_notes = 0

    for note_path in markdown_files:
        content = note_path.read_text(encoding="utf-8")
        link_count = len(WIKILINK_PATTERN.findall(content))
        total_links += link_count
        if link_count == 0:
            orphan_notes += 1

    note_count = len(markdown_files)
    link_density = total_links / note_count
    return FolderProfile(note_count=note_count, orphan_notes=orphan_notes, link_density=link_density)


def _collect_markdown_files(root: Path) -> list[Path]:
    markdown_files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
            markdown_files.append(path)
    return markdown_files

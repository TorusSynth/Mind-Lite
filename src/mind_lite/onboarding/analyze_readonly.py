import re
from dataclasses import dataclass
from pathlib import Path

WIKILINK_PATTERN = re.compile(r"\[\[[^\]]+\]\]")
TAG_PATTERN = re.compile(r"(?<!\w)#([A-Za-z0-9_-]+)")


@dataclass(frozen=True)
class NoteProfile:
    note_id: str
    title: str
    folder: str
    tags: list[str]
    content_preview: str
    link_count: int


@dataclass(frozen=True)
class FolderProfile:
    note_count: int
    orphan_notes: int
    link_density: float
    notes: list[NoteProfile]


def analyze_folder(folder_path: str) -> FolderProfile:
    root = Path(folder_path)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"folder does not exist or is not a directory: {folder_path}")

    markdown_files = _collect_markdown_files(root)
    if not markdown_files:
        return FolderProfile(note_count=0, orphan_notes=0, link_density=0.0, notes=[])

    total_links = 0
    orphan_notes = 0
    notes: list[NoteProfile] = []

    for note_path in markdown_files:
        content = note_path.read_text(encoding="utf-8")
        link_count = len(WIKILINK_PATTERN.findall(content))
        total_links += link_count
        if link_count == 0:
            orphan_notes += 1
        notes.append(
            NoteProfile(
                note_id=note_path.stem,
                title=_extract_title(note_path, content),
                folder=_relative_folder(root, note_path),
                tags=TAG_PATTERN.findall(content),
                content_preview=_content_preview(content),
                link_count=link_count,
            )
        )

    note_count = len(markdown_files)
    link_density = total_links / note_count
    return FolderProfile(note_count=note_count, orphan_notes=orphan_notes, link_density=link_density, notes=notes)


def _collect_markdown_files(root: Path) -> list[Path]:
    markdown_files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
            markdown_files.append(path)
    return sorted(markdown_files, key=lambda path: path.relative_to(root).as_posix())


def _extract_title(note_path: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        return stripped
    return note_path.stem


def _relative_folder(root: Path, note_path: Path) -> str:
    relative_parent = note_path.parent.relative_to(root)
    if relative_parent == Path("."):
        return ""
    return relative_parent.as_posix()


def _content_preview(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""

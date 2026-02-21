import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mind_lite.publish import PublisherAdapter


class LocalNginxPublisher(PublisherAdapter):
    def __init__(self, output_dir: str = ".mind_lite/published"):
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / "manifest.json"
        self._load_manifest()

    def _load_manifest(self) -> None:
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                self._manifest: dict[str, Any] = json.load(f)
        else:
            self._manifest = {"items": {}}

    def _save_manifest(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def publish(self, content: str, path: str, metadata: dict[str, Any] | None = None) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        safe_path = path.lstrip("/").replace("..", "")
        file_path = self.output_dir / safe_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content)
        
        self._manifest["items"][path] = {
            "path": path,
            "url": f"http://localhost:8080/{safe_path}",
            "published_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self._save_manifest()
        
        return f"http://localhost:8080/{safe_path}"

    def list_published(self) -> list[dict[str, Any]]:
        return list(self._manifest["items"].values())

    def unpublish(self, path: str) -> bool:
        if path not in self._manifest["items"]:
            return False
        
        safe_path = path.lstrip("/").replace("..", "")
        file_path = self.output_dir / safe_path
        
        if file_path.exists():
            file_path.unlink()
        
        del self._manifest["items"][path]
        self._save_manifest()
        
        return True

    def is_available(self) -> bool:
        return True

    def get_url_for_path(self, path: str) -> str | None:
        item = self._manifest["items"].get(path)
        return item["url"] if item else None

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mind_lite.publish import PublisherAdapter


class SFTPPublisher(PublisherAdapter):
    def __init__(
        self,
        host: str,
        username: str,
        remote_path: str,
        private_key_path: str | None = None,
        password: str | None = None,
        port: int = 22,
        base_url: str = "",
        manifest_path: str = ".mind_lite/sftp_manifest.json",
    ):
        self.host = host
        self.username = username
        self.remote_path = remote_path
        self.private_key_path = private_key_path
        self.password = password
        self.port = port
        self.base_url = base_url.rstrip("/")
        self.manifest_path = Path(manifest_path)
        self._load_manifest()

    def _load_manifest(self) -> None:
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                self._manifest: dict[str, Any] = json.load(f)
        else:
            self._manifest = {"items": {}}

    def _save_manifest(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def _get_connection(self):
        try:
            import paramiko
        except ImportError:
            raise RuntimeError("paramiko is required for SFTP publishing. Install with: pip install paramiko")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.host,
            "username": self.username,
            "port": self.port,
        }

        if self.private_key_path:
            connect_kwargs["key_filename"] = self.private_key_path
        elif self.password:
            connect_kwargs["password"] = self.password

        client.connect(**connect_kwargs)
        return client, client.open_sftp()

    def publish(self, content: str, path: str, metadata: dict[str, Any] | None = None) -> str:
        safe_path = path.lstrip("/").replace("..", "")
        remote_full_path = f"{self.remote_path}/{safe_path}"
        
        client, sftp = self._get_connection()
        try:
            remote_dir = "/".join(remote_full_path.split("/")[:-1])
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                self._mkdir_p(sftp, remote_dir)
            
            with sftp.file(remote_full_path, "w") as f:
                f.write(content)
            
            url = f"{self.base_url}/{safe_path}"
            
            self._manifest["items"][path] = {
                "path": path,
                "url": url,
                "remote_path": remote_full_path,
                "published_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
            self._save_manifest()
            
            return url
        finally:
            sftp.close()
            client.close()

    def _mkdir_p(self, sftp, remote_directory: str) -> None:
        dirs = remote_directory.split("/")
        path = ""
        for d in dirs:
            if not d:
                continue
            path = f"{path}/{d}"
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)

    def list_published(self) -> list[dict[str, Any]]:
        return list(self._manifest["items"].values())

    def unpublish(self, path: str) -> bool:
        if path not in self._manifest["items"]:
            return False
        
        item = self._manifest["items"][path]
        remote_full_path = item.get("remote_path", f"{self.remote_path}/{path}")
        
        client, sftp = self._get_connection()
        try:
            sftp.remove(remote_full_path)
            del self._manifest["items"][path]
            self._save_manifest()
            return True
        except FileNotFoundError:
            del self._manifest["items"][path]
            self._save_manifest()
            return True
        except Exception:
            return False
        finally:
            sftp.close()
            client.close()

    def is_available(self) -> bool:
        try:
            import paramiko
            client, sftp = self._get_connection()
            sftp.close()
            client.close()
            return True
        except Exception:
            return False

    def test_connection(self) -> tuple[bool, str]:
        try:
            import paramiko
            client, sftp = self._get_connection()
            sftp.listdir(self.remote_path)
            sftp.close()
            client.close()
            return True, "Connection successful"
        except ImportError:
            return False, "paramiko not installed. Run: pip install paramiko"
        except Exception as e:
            return False, str(e)

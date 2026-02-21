from abc import ABC, abstractmethod
from typing import Any


class PublisherAdapter(ABC):
    @abstractmethod
    def publish(self, content: str, path: str, metadata: dict[str, Any] | None = None) -> str:
        """Publish content and return URL or path."""
        pass

    @abstractmethod
    def list_published(self) -> list[dict[str, Any]]:
        """List all published items."""
        pass

    @abstractmethod
    def unpublish(self, path: str) -> bool:
        """Remove published content. Returns True if successful."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the publisher is available/configured."""
        pass

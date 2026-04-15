"""Base publisher interface for auto-posting content to external channels."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PublishResult:
    success: bool
    external_post_id: str | None = None
    url: str | None = None
    error: str | None = None


class BasePublisher(ABC):
    """Abstract base for all content publishers."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g. 'facebook', 'wordpress', 'telegram')."""

    @abstractmethod
    async def publish(self, title: str, body: str, **kwargs) -> PublishResult:
        """Publish content and return the result."""

    @abstractmethod
    async def delete(self, external_post_id: str) -> bool:
        """Delete a previously published post. Returns True if successful."""

    async def health_check(self) -> bool:
        """Check if the publisher connection is working."""
        return True

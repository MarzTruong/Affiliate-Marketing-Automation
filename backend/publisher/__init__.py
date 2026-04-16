# Backward-compat shim — real code now lives in backend.affiliate.publishers
from backend.affiliate.publishers.base import BasePublisher, PublishResult
from backend.affiliate.publishers.posting_service import (
    get_publications,
    get_publisher,
    publish_content,
)

__all__ = ["BasePublisher", "PublishResult", "get_publisher", "publish_content", "get_publications"]

"""Tests for publisher module."""

import pytest

from backend.affiliate.publishers.base import BasePublisher, PublishResult
from backend.affiliate.publishers.posting_service import get_publisher, PUBLISHER_REGISTRY


def test_publish_result_success():
    result = PublishResult(success=True, external_post_id="123", url="https://example.com/123")
    assert result.success is True
    assert result.error is None


def test_publish_result_failure():
    result = PublishResult(success=False, error="API rate limit")
    assert result.success is False
    assert result.error == "API rate limit"


def test_publisher_registry_has_all_channels():
    expected = {"facebook", "wordpress", "telegram", "tiktok"}
    assert set(PUBLISHER_REGISTRY.keys()) == expected


def test_get_publisher_facebook():
    pub = get_publisher("facebook")
    assert pub.platform_name == "facebook"


def test_get_publisher_wordpress():
    pub = get_publisher("wordpress")
    assert pub.platform_name == "wordpress"


def test_get_publisher_telegram():
    pub = get_publisher("telegram")
    assert pub.platform_name == "telegram"


def test_get_publisher_unknown():
    with pytest.raises(ValueError, match="Unknown publish channel"):
        get_publisher("instagram")


def test_all_publishers_implement_interface():
    for name, cls in PUBLISHER_REGISTRY.items():
        pub = cls()
        assert isinstance(pub, BasePublisher)
        assert hasattr(pub, "publish")
        assert hasattr(pub, "delete")
        assert hasattr(pub, "health_check")
        assert pub.platform_name == name

"""Test KlingEngine — image-to-video for Kênh 1."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ai_engine.kling_engine import (
    KlingAuthError,
    KlingConfig,
    KlingEngine,
    KlingResult,
    KlingTimeoutError,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_engine(api_key: str = "test", timeout_seconds: float = 180.0) -> KlingEngine:
    """Create KlingEngine bypassing __init__ (fal-client may not be installed)."""
    cfg = KlingConfig(api_key=api_key, timeout_seconds=timeout_seconds)
    engine = KlingEngine.__new__(KlingEngine)
    engine.config = cfg
    return engine


# ── Config tests ───────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_config_defaults():
    cfg = KlingConfig(api_key="test")
    assert cfg.duration_seconds == 5
    assert cfg.aspect_ratio == "9:16"
    assert cfg.model == "fal-ai/kling-video/v2/master/image-to-video"
    assert cfg.timeout_seconds == 180.0


@pytest.mark.unit
def test_config_frozen():
    cfg = KlingConfig(api_key="test")
    with pytest.raises(Exception):
        cfg.api_key = "other"  # type: ignore[misc]


# ── generate() happy path ─────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_success():
    engine = _make_engine()
    fake_url = "https://cdn.fal.ai/result/abc.mp4"

    with patch.object(engine, "_submit_job", new=AsyncMock(return_value=fake_url)):
        result = await engine.generate(
            image_url="https://example.com/sp.jpg",
            prompt="Camera pan chậm trên hộp sữa Meiji",
        )

    assert isinstance(result, KlingResult)
    assert result.video_url == fake_url
    assert result.duration_seconds == 5
    assert result.prompt == "Camera pan chậm trên hộp sữa Meiji"
    assert result.image_url == "https://example.com/sp.jpg"


# ── Validation tests ───────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_prompt_raises():
    engine = _make_engine()
    with pytest.raises(ValueError, match="prompt"):
        await engine.generate(image_url="https://x.com/a.jpg", prompt="")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_whitespace_only_prompt_raises():
    engine = _make_engine()
    with pytest.raises(ValueError, match="prompt"):
        await engine.generate(image_url="https://x.com/a.jpg", prompt="   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_image_url_raises():
    engine = _make_engine()
    with pytest.raises(ValueError, match="image_url"):
        await engine.generate(image_url="/local/path.jpg", prompt="test")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_relative_image_url_raises():
    engine = _make_engine()
    with pytest.raises(ValueError, match="image_url"):
        await engine.generate(image_url="images/product.jpg", prompt="test")


# ── Error propagation tests ────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_auth_error_propagates():
    engine = _make_engine(api_key="bad")
    with patch.object(
        engine, "_submit_job", new=AsyncMock(side_effect=KlingAuthError("401"))
    ):
        with pytest.raises(KlingAuthError):
            await engine.generate(
                image_url="https://x.com/a.jpg", prompt="valid prompt"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_error_propagates():
    from backend.ai_engine.kling_engine import KlingRateLimitError
    engine = _make_engine()
    with patch.object(
        engine, "_submit_job", new=AsyncMock(side_effect=KlingRateLimitError("429"))
    ):
        with pytest.raises(KlingRateLimitError):
            await engine.generate(
                image_url="https://x.com/a.jpg", prompt="valid prompt"
            )


# ── Timeout test ───────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_raises_kling_timeout_error():
    """KlingTimeoutError is raised when _submit_job exceeds timeout.

    We patch _submit_job to raise KlingTimeoutError directly (simulating what
    _submit_job itself raises when asyncio.TimeoutError occurs), since
    fal-client is not installed in this environment.
    """
    engine = _make_engine(timeout_seconds=0.001)

    with patch.object(
        engine,
        "_submit_job",
        new=AsyncMock(side_effect=KlingTimeoutError("Kling job timed out")),
    ):
        with pytest.raises(KlingTimeoutError):
            await engine.generate(
                image_url="https://x.com/a.jpg", prompt="test"
            )


# ── KlingResult dataclass ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_kling_result_fields():
    result = KlingResult(
        video_url="https://cdn.fal.ai/v.mp4",
        duration_seconds=5,
        prompt="test",
        image_url="https://img.com/a.jpg",
    )
    assert result.video_url == "https://cdn.fal.ai/v.mp4"
    assert result.duration_seconds == 5

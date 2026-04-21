"""Tests cho VideoComposer — dùng mock subprocess, không cần ffmpeg thật."""
from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.video.composer import (
    ComposeRequest,
    VideoComposerError,
    _ensure_local,
    _get_ffmpeg,
    _run_ffmpeg,
)


# ── _get_ffmpeg ────────────────────────────────────────────────────────────────

def test_get_ffmpeg_returns_imageio_binary():
    path = _get_ffmpeg()
    assert "ffmpeg" in path.lower()
    assert Path(path).exists(), f"ffmpeg binary không tồn tại: {path}"


# ── _ensure_local ──────────────────────────────────────────────────────────────

def test_ensure_local_http_downloads(tmp_path):
    fake_data = b"\x00\x01\x02"
    with patch("urllib.request.urlretrieve") as mock_dl:
        def side_effect(url, dest):
            Path(dest).write_bytes(fake_data)
        mock_dl.side_effect = side_effect

        result = _ensure_local("https://example.com/clip.mp4", tmp_path, "clip.mp4")

    assert result == tmp_path / "clip.mp4"
    assert result.read_bytes() == fake_data


def test_ensure_local_absolute_path(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio")
    result = _ensure_local(str(src), tmp_path, "out.mp3")
    assert result == src


def test_ensure_local_missing_local_raises(tmp_path):
    with pytest.raises(VideoComposerError, match="không tồn tại"):
        _ensure_local("/nonexistent/path.mp4", tmp_path, "x.mp4")


# ── _run_ffmpeg ────────────────────────────────────────────────────────────────

def test_run_ffmpeg_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _run_ffmpeg("ffmpeg", ["-version"], label="test")
    mock_run.assert_called_once()


def test_run_ffmpeg_failure_raises():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal error")
        with pytest.raises(VideoComposerError, match="thất bại"):
            _run_ffmpeg("ffmpeg", ["-bad-arg"], label="test")


# ── compose_tiktok_video validation ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compose_requires_clips():
    req = ComposeRequest(clip_urls=[], audio_url="https://example.com/a.mp3")
    with pytest.raises(VideoComposerError, match="ít nhất 1 clip"):
        from backend.video.composer import compose_tiktok_video
        await compose_tiktok_video(req)


@pytest.mark.asyncio
async def test_compose_requires_audio():
    req = ComposeRequest(clip_urls=["https://example.com/v.mp4"], audio_url="")
    with pytest.raises(VideoComposerError, match="audio URL"):
        from backend.video.composer import compose_tiktok_video
        await compose_tiktok_video(req)


# ── _compose_sync integration (fully mocked subprocess) ─────────────────────────

@pytest.mark.asyncio
async def test_compose_sync_calls_ffmpeg_steps(tmp_path):
    """Kiểm tra _compose_sync gọi ffmpeg đúng số bước: scale×N + concat + merge + (optional overlay)."""
    from backend.video.composer import compose_tiktok_video, _OUTPUT_DIR

    # Tạo fake clip/audio files
    clip1 = tmp_path / "clip1.mp4"
    clip2 = tmp_path / "clip2.mp4"
    audio = tmp_path / "audio.mp3"
    for f in [clip1, clip2, audio]:
        f.write_bytes(b"\x00" * 100)

    req = ComposeRequest(
        clip_urls=[str(clip1), str(clip2)],
        audio_url=str(audio),
        hook_text="Hook test!",
        product_name="Test Product",
    )

    ffmpeg_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        ffmpeg_calls.append(cmd)
        # Tạo file output giả để bước sau không lỗi
        for arg in cmd:
            if arg.endswith(".mp4") and not any(
                inp in cmd for inp in ["-i"] if cmd[cmd.index("-i") + 1] == arg
            ):
                pass
        return MagicMock(returncode=0, stderr="", stdout="15.0\n")

    fake_out = tmp_path / "fake_final.mp4"
    fake_out.write_bytes(b"\x00" * 1024)

    with patch("subprocess.run", side_effect=fake_run), \
         patch("shutil.copy2") as mock_copy, \
         patch("backend.video.composer._get_video_duration", return_value=10.0), \
         patch("backend.video.composer._OUTPUT_DIR", tmp_path), \
         patch("urllib.request.urlretrieve"):

        # Tạo output file trước để stat() không lỗi
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value = MagicMock(st_size=512000)
            result = await compose_tiktok_video(req)

    # Kiểm tra đủ bước ffmpeg: 2 scale + 1 concat + 1 merge + 1 overlay = 5
    assert len(ffmpeg_calls) >= 5, f"Expected ≥5 ffmpeg calls, got {len(ffmpeg_calls)}"

    # Bước scale phải xuất hiện
    scale_calls = [c for c in ffmpeg_calls if any("scale=" in str(a) for a in c)]
    assert len(scale_calls) == 2, "Phải scale đúng 2 clips"

    # Bước concat
    concat_calls = [c for c in ffmpeg_calls if "-f" in c and "concat" in c]
    assert len(concat_calls) == 1, "Phải có 1 bước concat"

    # Bước overlay (hook_text != "")
    overlay_calls = [c for c in ffmpeg_calls if any("drawtext" in str(a) for a in c)]
    assert len(overlay_calls) == 1, "Phải có 1 bước drawtext overlay"


@pytest.mark.asyncio
async def test_compose_no_hook_text_skips_overlay(tmp_path):
    """Không có hook_text → không gọi drawtext step."""
    from backend.video.composer import compose_tiktok_video

    clip = tmp_path / "c.mp4"
    audio = tmp_path / "a.mp3"
    clip.write_bytes(b"\x00" * 100)
    audio.write_bytes(b"\x00" * 100)

    req = ComposeRequest(
        clip_urls=[str(clip)],
        audio_url=str(audio),
        hook_text="",  # no overlay
    )

    ffmpeg_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        ffmpeg_calls.append(cmd)
        return MagicMock(returncode=0, stderr="", stdout="5.0\n")

    with patch("subprocess.run", side_effect=fake_run), \
         patch("shutil.copy2"), \
         patch("backend.video.composer._get_video_duration", return_value=5.0), \
         patch("backend.video.composer._OUTPUT_DIR", tmp_path), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=512000)
        await compose_tiktok_video(req)

    overlay_calls = [c for c in ffmpeg_calls if any("drawtext" in str(a) for a in c)]
    assert len(overlay_calls) == 0, "Không có hook_text → không drawtext"

"""Video Composer — TikTok Kênh 1 Faceless Pipeline.

Dựng MP4 cuối từ:
- N clip video (Kling AI .mp4, thường 3 × 5s = 15s)
- 1 audio track (ElevenLabs / Gemini TTS .mp3/.wav)
- Hook text overlay 2 giây đầu (tùy chọn)

Output: 9:16 vertical MP4, H.264 video + AAC audio, ≤ 20MB.

Dùng imageio-ffmpeg để có binary ffmpeg bundled — không cần cài system ffmpeg.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Thư mục lưu file output
_OUTPUT_DIR = Path(__file__).parent.parent / "static" / "video"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _get_ffmpeg() -> str:
    """Trả về đường dẫn ffmpeg binary (bundled qua imageio-ffmpeg)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"  # fallback: assume system ffmpeg in PATH


@dataclass
class ComposeRequest:
    clip_urls: list[str]          # Danh sách URL/path clip video (≥1)
    audio_url: str                # URL/path file audio (MP3/WAV)
    hook_text: str = ""           # Text overlay 2s đầu (để trống = không overlay)
    product_name: str = ""        # Tên SP — dùng làm tên file output
    target_width: int = 1080      # 9:16 standard
    target_height: int = 1920
    audio_fade_out_s: float = 1.0 # Fade out audio cuối video


@dataclass
class ComposeResult:
    video_url: str        # URL public tương đối: /static/video/xxx.mp4
    video_path: str       # Đường dẫn tuyệt đối trên server
    duration_s: float
    file_size_bytes: int
    clip_count: int


class VideoComposerError(Exception):
    """Lỗi trong quá trình dựng video."""


async def compose_tiktok_video(req: ComposeRequest) -> ComposeResult:
    """Dựng video TikTok từ clips + audio.

    Chạy ffmpeg trong thread pool (blocking I/O) để không block event loop.
    Raise VideoComposerError nếu ffmpeg fail.
    """
    if not req.clip_urls:
        raise VideoComposerError("Cần ít nhất 1 clip video")
    if not req.audio_url:
        raise VideoComposerError("Cần audio URL")

    return await asyncio.to_thread(_compose_sync, req)


def _compose_sync(req: ComposeRequest) -> ComposeResult:
    """Synchronous compose — chạy trong thread, gọi ffmpeg subprocess."""
    import subprocess

    ffmpeg = _get_ffmpeg()
    slug = req.product_name[:20].replace(" ", "_").lower() if req.product_name else "video"
    out_name = f"tiktok_{slug}_{uuid.uuid4().hex[:8]}.mp4"
    out_path = _OUTPUT_DIR / out_name

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # 1. Download remote URLs vào tmp (nếu là http/https)
        clip_paths = [_ensure_local(url, tmp, f"clip_{i}.mp4") for i, url in enumerate(req.clip_urls)]
        audio_path = _ensure_local(req.audio_url, tmp, "audio.mp3")

        # 2. Scale + pad mỗi clip lên 1080×1920 (9:16), chuẩn hoá fps=30
        scaled_clips: list[Path] = []
        for i, cp in enumerate(clip_paths):
            out = tmp / f"scaled_{i}.mp4"
            _run_ffmpeg(ffmpeg, [
                "-y", "-i", str(cp),
                "-vf", (
                    f"scale={req.target_width}:{req.target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={req.target_width}:{req.target_height}:(ow-iw)/2:(oh-ih)/2:black,"
                    "fps=30,format=yuv420p"
                ),
                "-an",           # strip original audio từ clip
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                str(out),
            ], label=f"scale clip {i}")
            scaled_clips.append(out)

        # 3. Concat tất cả scaled clips
        concat_list = tmp / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p}'" for p in scaled_clips),
            encoding="utf-8",
        )
        concat_video = tmp / "concat.mp4"
        _run_ffmpeg(ffmpeg, [
            "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(concat_video),
        ], label="concat clips")

        # 4. Merge video + audio, trim audio tới đúng video duration
        merged = tmp / "merged.mp4"
        _run_ffmpeg(ffmpeg, [
            "-y",
            "-i", str(concat_video),
            "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-af", f"afade=t=out:st={_get_video_duration(ffmpeg, concat_video) - req.audio_fade_out_s:.2f}:d={req.audio_fade_out_s}",
            "-shortest",         # trim audio nếu dài hơn video
            str(merged),
        ], label="merge audio")

        # 5. Hook text overlay (tuỳ chọn) — 2s đầu
        final = tmp / "final.mp4"
        if req.hook_text:
            safe_text = req.hook_text.replace("'", "\\'").replace(":", "\\:")
            font_size = max(40, req.target_width // 18)
            _run_ffmpeg(ffmpeg, [
                "-y", "-i", str(merged),
                "-vf", (
                    f"drawtext=text='{safe_text}':"
                    f"fontsize={font_size}:fontcolor=white:borderw=3:bordercolor=black:"
                    f"x=(w-text_w)/2:y=h*0.15:"
                    f"enable='between(t,0,2)'"
                ),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "copy",
                str(final),
            ], label="hook text overlay")
        else:
            final = merged  # skip overlay bước nếu không có text

        # 6. Copy ra output dir
        import shutil
        shutil.copy2(str(final), str(out_path))

    duration = _get_video_duration(ffmpeg, out_path)
    size = out_path.stat().st_size
    video_url = f"/static/video/{out_name}"

    logger.info(
        f"[Composer] Video dựng xong: {out_name} "
        f"| {len(req.clip_urls)} clips | {duration:.1f}s | {size // 1024}KB"
    )

    return ComposeResult(
        video_url=video_url,
        video_path=str(out_path),
        duration_s=duration,
        file_size_bytes=size,
        clip_count=len(req.clip_urls),
    )


def _ensure_local(url_or_path: str, tmp_dir: Path, filename: str) -> Path:
    """Download nếu là URL, copy nếu là path local tương đối, trả về Path tuyệt đối."""
    import urllib.request

    if url_or_path.startswith(("http://", "https://")):
        dest = tmp_dir / filename
        urllib.request.urlretrieve(url_or_path, dest)
        return dest

    # Path local — có thể là /static/audio/xxx.mp3 (relative to project root)
    p = Path(url_or_path)
    if not p.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        p = project_root / "backend" / url_or_path.lstrip("/")
    if not p.exists():
        raise VideoComposerError(f"File không tồn tại: {p}")
    return p


def _run_ffmpeg(ffmpeg: str, args: list[str], label: str = "") -> None:
    """Chạy ffmpeg subprocess, raise VideoComposerError nếu exit code != 0."""
    import subprocess

    cmd = [ffmpeg] + args
    logger.debug(f"[Composer:{label}] {' '.join(cmd[:8])}...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise VideoComposerError(
            f"ffmpeg {label} thất bại (exit {result.returncode}):\n"
            f"stderr: {result.stderr[-500:]}"
        )


def _get_video_duration(ffmpeg: str, path: Path) -> float:
    """Dùng ffprobe để đọc duration của file video/audio."""
    import subprocess
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0

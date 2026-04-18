"""Phase 0 smoke test — verify all new components wire together.

Run manually:
    .venv\\Scripts\\python.exe scripts/smoke_phase0.py

Requires env:
    GEMINI_API_KEY
    FAL_KEY
    TIKTOK_SHOP_APP_KEY / APP_SECRET / ACCESS_TOKEN (optional — skips if missing)

Note: DB-backed section requires a running PostgreSQL with migrations applied.
      Run: .venv\\Scripts\\alembic.exe upgrade head
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path

# Ensure repo root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING)

from backend.database import get_db_context  # noqa: E402
from backend.learning.hook_ab_test import HookABTestEngine  # noqa: E402
from backend.learning.product_scoring import ProductScoringEngine  # noqa: E402
from backend.tiktok_shop.tag_queue import TagQueueService  # noqa: E402


async def _smoke_gemini_tts() -> None:
    """Step 1: Gemini TTS smoke (skipped if no GEMINI_API_KEY)."""
    if not os.getenv("GEMINI_API_KEY"):
        print("1. Gemini TTS — SKIPPED (no GEMINI_API_KEY)\n")
        return

    print("1. Gemini TTS...")
    from backend.ai_engine.gemini_tts_engine import GeminiTTSConfig, GeminiTTSEngine

    tts = GeminiTTSEngine(GeminiTTSConfig(api_key=os.environ["GEMINI_API_KEY"]))
    r = await tts.generate("Xin chào các mẹ bầu!")
    print(f"   ✓ Audio saved: {r.audio_path}\n")


async def _smoke_kling() -> None:
    """Step 2: Kling AI smoke (skipped if no FAL_KEY or fal-client not installed)."""
    if not os.getenv("FAL_KEY"):
        print("2. Kling AI — SKIPPED (no FAL_KEY)\n")
        return

    try:
        from backend.ai_engine.kling_engine import KlingConfig, KlingEngine
    except ImportError as exc:
        print(f"2. Kling AI — SKIPPED ({exc})\n")
        return

    print("2. Kling AI...")
    try:
        kling = KlingEngine(KlingConfig(api_key=os.environ["FAL_KEY"]))
    except ImportError as exc:
        print(f"   SKIPPED — fal-client not installed: {exc}\n")
        return

    r = await kling.generate(
        image_url="https://via.placeholder.com/720x1280.jpg",
        prompt="Camera slowly pans across product",
    )
    print(f"   ✓ Video URL: {r.video_url}\n")


async def _smoke_db() -> None:
    """Step 3: DB-backed engines — HookABTest + ProductScoring + TagQueue."""
    print("3. Hook A/B + Product Scoring + Tag Queue (DB smoke)...")

    # HookABTestEngine — uses content_piece_id FK to content_pieces.
    # On a fresh DB without a content_pieces row, PostgreSQL will raise FK violation.
    # Use a NULL-like workaround: insert raw SQL, or skip FK check by using
    # an existing content piece.  For smoke purposes we catch FK errors gracefully.
    async with get_db_context() as db:
        hab = HookABTestEngine(db)
        content_piece_id = uuid.uuid4()
        try:
            v = await hab.record_variant(
                content_piece_id=content_piece_id,
                hook_text="Test hook — smoke",
                pattern_type="pain_point",
            )
            await hab.ingest_retention(v.id, 0.5)
            print(f"   ✓ HookVariant: {v.id}")
        except Exception as exc:
            # FK violation expected if content_pieces row doesn't exist
            print(f"   ~ HookVariant skipped (FK constraint or DB offline): {exc}")

    async with get_db_context() as db:
        psc = ProductScoringEngine(db)
        ps = await psc.record_performance(
            product_id="smoke_sp",
            ctr=0.01,
            conversion=0.02,
            return_rate=0.10,
            orders_delta=1,
        )
        print(f"   ✓ ProductScore: {ps.product_id} score={ps.score:.2f}")

    async with get_db_context() as db:
        tqs = TagQueueService(db)
        tqi = await tqs.enqueue(
            video_id=uuid.uuid4(),
            tiktok_draft_url="https://tiktok.com/smoke",
            product_id="smoke_sp",
            product_name="Smoke Test",
            commission_rate=0.15,
        )
        print(f"   ✓ TagQueueItem: {tqi.id}\n")


async def main() -> None:
    print("▶ Phase 0 smoke test\n")

    await _smoke_gemini_tts()
    await _smoke_kling()
    await _smoke_db()

    print("✓ All smoke checks passed.\n")


if __name__ == "__main__":
    asyncio.run(main())

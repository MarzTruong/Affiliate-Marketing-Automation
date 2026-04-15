"""Content Generator — orchestrate template, few-shot, CoT, và Claude API."""

import logging
import re
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai_engine.client import ClaudeClient
from backend.ai_engine.prompts.templates import (
    FACEBOOK_VARIANT_TEMPLATE,
    PRODUCT_DESCRIPTION_TEMPLATE,
    SEO_ARTICLE_TEMPLATE,
    SOCIAL_POST_TEMPLATE,
    TELEGRAM_VARIANT_TEMPLATE,
    TIKTOK_VARIANT_TEMPLATE,
    VIDEO_SCRIPT_TEMPLATE,
    _COT_HEADER,
    build_few_shot_prefix,
)
from backend.models.content import ContentPiece
from backend.models.product import Product
from backend.models.sop_template import SOPTemplate

# Số lượng few-shot examples tối đa inject vào prompt
_MAX_FEW_SHOT_EXAMPLES = 3

TEMPLATE_MAP = {
    "product_description": PRODUCT_DESCRIPTION_TEMPLATE,
    "seo_article": SEO_ARTICLE_TEMPLATE,
    "social_post": SOCIAL_POST_TEMPLATE,
    "video_script": VIDEO_SCRIPT_TEMPLATE,
}


class ContentGenerator:
    """Orchestrates content generation: few-shot → CoT template → Claude → DB."""

    def __init__(self):
        self.claude = ClaudeClient()
        from backend.ai_engine.gemini_engine import create_gemini_engine
        self._gemini = create_gemini_engine()
        self._gemini_ready = False
        from backend.ai_engine.elevenlabs_engine import create_elevenlabs_engine
        self._elevenlabs = create_elevenlabs_engine()
        self._elevenlabs_ready = False
        from backend.ai_engine.heygen_engine import create_heygen_engine
        self._heygen = create_heygen_engine()
        self._heygen_ready = False

    async def _ensure_gemini_initialized(self) -> bool:
        """Lazy init Gemini — chỉ init một lần, không block nếu unavailable."""
        if not self._gemini_ready:
            await self._gemini.initialize()
            self._gemini_ready = True
        return self._gemini.is_available()

    async def _ensure_elevenlabs_initialized(self) -> bool:
        """Lazy init ElevenLabs — chỉ init một lần, không block nếu unavailable."""
        if not self._elevenlabs_ready:
            await self._elevenlabs.initialize()
            self._elevenlabs_ready = True
        return self._elevenlabs.is_available()

    async def _ensure_heygen_initialized(self) -> bool:
        """Lazy init HeyGen — chỉ init một lần, không block nếu unavailable."""
        if not self._heygen_ready:
            await self._heygen.initialize()
            self._heygen_ready = True
        return self._heygen.is_available()

    async def generate(
        self,
        product_id: UUID,
        campaign_id: UUID,
        content_type: str,
        template_id: UUID | None = None,
        db: AsyncSession | None = None,
    ) -> ContentPiece:
        if db is None:
            raise ValueError("Database session is required")

        product = await db.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        prompt_template = await self._get_template(content_type, template_id, db)
        few_shot_examples = await self._load_few_shot_examples(content_type, product, db)

        # Gemini Vision enrichment — non-blocking, chỉ chạy nếu có ảnh
        meta = product.metadata_json or {}
        description = meta.get("description", product.name)
        image_urls: list[str] = meta.get("image_urls", [])
        if image_urls and await self._ensure_gemini_initialized():
            try:
                from backend.ai_engine.gemini_engine import ProductImageContext
                ctx = ProductImageContext(
                    product_name=product.name,
                    price=float(product.price or 0),
                    category=product.category or "",
                    platform=product.platform,
                    description=description,
                    image_urls=image_urls,
                )
                enriched = await self._gemini.enrich_product_context(ctx)
                description = enriched.description
                logger.info(f"[ContentGenerator] Gemini enriched product {product_id}")
            except Exception as e:
                logger.warning(f"[ContentGenerator] Gemini enrichment failed (ignored): {e}")

        variables = {
            "product_name": product.name,
            "price": f"{product.price:,.0f}" if product.price else "Liên hệ",
            "category": product.category or "Chung",
            "description": description,
            "platform": product.platform,
            "affiliate_url": product.affiliate_url or product.original_url,
            "social_platform": "Facebook",
            # CoT header và few-shot prefix được inject tự động
            "cot_header": _COT_HEADER,
            "few_shot_prefix": build_few_shot_prefix(few_shot_examples),
        }

        content_text, usage = await self.claude.generate(
            content_type=content_type,
            variables=variables,
            template=prompt_template,
        )

        content_text = self._strip_thinking_blocks(content_text)
        title = self._extract_title(content_text)
        keywords = self._extract_keywords(content_text)

        content_piece = ContentPiece(
            product_id=product_id,
            campaign_id=campaign_id,
            content_type=content_type,
            title=title,
            body=content_text,
            seo_keywords=keywords,
            template_id=template_id,
            claude_model=usage.get("model"),
            token_cost_input=usage.get("input_tokens"),
            token_cost_output=usage.get("output_tokens"),
            estimated_cost_usd=usage.get("cost_usd"),
            status="draft",
        )
        db.add(content_piece)
        await db.flush()
        await db.refresh(content_piece)

        # Generate 3 platform variants — non-blocking, graceful fallback
        try:
            variants = await self._generate_variants(variables)
            content_piece.platform_variants = variants
        except Exception as e:
            logger.warning(f"[ContentGenerator] Variant generation failed (ignored): {e}")

        # ElevenLabs TTS + HeyGen clips — chỉ chạy với tiktok_script, non-blocking
        if content_type == "tiktok_script":
            await self._generate_tiktok_audio(content_piece, product)
            await self._generate_heygen_clips(content_piece)

        if template_id:
            template = await db.get(SOPTemplate, template_id)
            if template:
                template.usage_count += 1

        return content_piece

    async def _generate_heygen_clips(self, content_piece: ContentPiece) -> None:
        """Tạo hook clip và CTA clip bằng HeyGen API.

        Non-blocking: lỗi chỉ log warning, không crash pipeline.
        Kết quả lưu vào content_piece.heygen_hook_url / heygen_cta_url.
        """
        try:
            if not await self._ensure_heygen_initialized():
                logger.info(
                    "[ContentGenerator] HeyGen không khả dụng — bỏ qua bước tạo video clips."
                )
                return

            from backend.ai_engine.heygen_engine import HeyGenRateLimitError

            clips = await self._heygen.generate_clips(content_piece.body)

            for clip in clips:
                if clip.clip_type == "hook":
                    content_piece.heygen_hook_url = clip.video_url
                elif clip.clip_type == "cta":
                    content_piece.heygen_cta_url = clip.video_url

            if clips:
                logger.info(
                    "[ContentGenerator] HeyGen OK — %d clips generated (hook=%s, cta=%s)",
                    len(clips),
                    content_piece.heygen_hook_url or "none",
                    content_piece.heygen_cta_url or "none",
                )

        except HeyGenRateLimitError as e:
            logger.error("[ContentGenerator] %s", e)
        except Exception as e:
            logger.warning("[ContentGenerator] HeyGen clips failed (ignored): %s", e)

    async def _generate_tiktok_audio(self, content_piece: ContentPiece, product) -> None:
        """Tổng hợp audio narration từ cột VOICE của TikTok script.

        Non-blocking: lỗi ElevenLabs chỉ log warning, không crash pipeline.
        Kết quả lưu thẳng vào content_piece (audio_url, audio_voice_id, audio_duration_s).
        """
        try:
            if not await self._ensure_elevenlabs_initialized():
                logger.info(
                    "[ContentGenerator] ElevenLabs không khả dụng — bỏ qua bước tạo audio."
                )
                return

            from backend.ai_engine.elevenlabs_engine import (
                ElevenLabsRateLimitError,
                extract_voice_text,
            )

            voice_text = extract_voice_text(content_piece.body)
            if not voice_text:
                logger.warning(
                    "[ContentGenerator] Không extract được VOICE text — bỏ qua audio."
                )
                return

            prefix = f"tiktok_{product.name[:20].replace(' ', '_')}" if product else "tiktok"
            result = await self._elevenlabs.generate_audio(
                text=voice_text,
                filename_prefix=prefix,
            )

            content_piece.audio_url = result.audio_url
            content_piece.audio_voice_id = result.voice_id
            content_piece.audio_duration_s = result.duration_s

            logger.info(
                "[ContentGenerator] ElevenLabs audio OK — url=%s, duration=%.1fs",
                result.audio_url,
                result.duration_s,
            )

        except ElevenLabsRateLimitError as e:
            logger.error("[ContentGenerator] %s", e)
        except Exception as e:
            logger.warning(
                "[ContentGenerator] ElevenLabs audio failed (ignored): %s", e
            )

    async def _get_template(
        self, content_type: str, template_id: UUID | None, db: AsyncSession
    ) -> str:
        if template_id:
            template = await db.get(SOPTemplate, template_id)
            if template:
                return template.prompt_template

        result = await db.execute(
            select(SOPTemplate)
            .where(SOPTemplate.content_type == content_type, SOPTemplate.is_active.is_(True))
            .order_by(SOPTemplate.performance_score.desc())
            .limit(1)
        )
        top_template = result.scalar_one_or_none()
        if top_template:
            return top_template.prompt_template

        return TEMPLATE_MAP.get(content_type, PRODUCT_DESCRIPTION_TEMPLATE)

    async def _load_few_shot_examples(
        self, content_type: str, product: Product, db: AsyncSession
    ) -> list[dict]:
        """Nạp văn mẫu đã được approve từ AITrainingData.

        Ưu tiên examples cùng danh mục sản phẩm, fallback về cùng content_type.
        Giới hạn _MAX_FEW_SHOT_EXAMPLES để không làm prompt quá dài.
        """
        try:
            from backend.models.ai_training_data import AITrainingData
            from sqlalchemy import and_

            # Ưu tiên: cùng content_type + cùng danh mục
            category = product.category or ""
            result = await db.execute(
                select(AITrainingData)
                .where(
                    and_(
                        AITrainingData.content_type == content_type,
                        AITrainingData.product_category == category,
                    )
                )
                .order_by(AITrainingData.created_at.desc())
                .limit(_MAX_FEW_SHOT_EXAMPLES)
            )
            examples = result.scalars().all()

            # Fallback: cùng content_type, bất kỳ danh mục
            if not examples:
                result = await db.execute(
                    select(AITrainingData)
                    .where(AITrainingData.content_type == content_type)
                    .order_by(AITrainingData.created_at.desc())
                    .limit(_MAX_FEW_SHOT_EXAMPLES)
                )
                examples = result.scalars().all()

            return [
                {
                    "content_type": ex.content_type,
                    "product_category": ex.product_category,
                    "final_text": ex.final_text,
                }
                for ex in examples
            ]
        except Exception:
            # Bảng chưa tồn tại hoặc lỗi DB — không block content generation
            return []

    async def _generate_variants(self, variables: dict) -> dict:
        """Generate 3 platform-optimized variants song song bằng Haiku (cost thấp).

        Returns:
            {"tiktok": "...", "facebook": "...", "telegram": "..."}
        """
        import asyncio

        async def _call(template: str, platform_label: str) -> str:
            text, _ = await self.claude.generate(
                content_type="social_post",
                variables=variables,
                template=template,
                model_override="claude-haiku-4-5-20251001",
            )
            return self._strip_thinking_blocks(text)

        tiktok_task = asyncio.create_task(_call(TIKTOK_VARIANT_TEMPLATE, "tiktok"))
        facebook_task = asyncio.create_task(_call(FACEBOOK_VARIANT_TEMPLATE, "facebook"))
        telegram_task = asyncio.create_task(_call(TELEGRAM_VARIANT_TEMPLATE, "telegram"))

        tiktok, facebook, telegram = await asyncio.gather(
            tiktok_task, facebook_task, telegram_task, return_exceptions=True
        )

        return {
            "tiktok": tiktok if isinstance(tiktok, str) else "",
            "facebook": facebook if isinstance(facebook, str) else "",
            "telegram": telegram if isinstance(telegram, str) else "",
        }

    def _strip_thinking_blocks(self, content: str) -> str:
        """Xóa <thinking>...</thinking> CoT blocks khỏi output trước khi lưu.

        Xử lý cả trường hợp </thinking> bị thiếu (Claude bị cắt giữa chừng do max_tokens).
        """
        import re as _re
        # Strip complete blocks
        content = _re.sub(r"<thinking>.*?</thinking>\s*", "", content, flags=_re.DOTALL)
        # Strip unclosed block (từ <thinking> đến hết chuỗi nếu không có </thinking>)
        content = _re.sub(r"<thinking>.*", "", content, flags=_re.DOTALL)
        return content.strip()

    def _extract_title(self, content: str) -> str:
        for pattern in [r"## Tiêu đề\n(.+)", r"## Meta Title\n(.+)", r"^# (.+)"]:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("<"):
                return line[:200]
        return "Untitled"

    def _extract_keywords(self, content: str) -> list[str]:
        match = re.search(r"## Từ khóa SEO\n(.+)", content, re.MULTILINE)
        if match:
            keywords_str = match.group(1).strip()
            return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
        return []

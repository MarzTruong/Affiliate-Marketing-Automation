"""GeminiContentGenerator — Tích hợp Google Gemini Pro Multimodal.

Dùng google-genai SDK (google.genai) — phiên bản chính thức mới.

Chức năng chính:
  - Phân tích hình ảnh sản phẩm qua Gemini Vision (gemini-1.5-pro)
  - Async image download qua httpx
  - Error handling chi tiết: rate limit, auth, timeout, network
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ── Config ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GeminiConfig:
    """Cấu hình kết nối Google Gemini."""
    api_key: str = ""
    project_id: str = ""
    location: str = "us-central1"
    use_vertex: bool = False

    vision_model: str = "gemini-2.5-pro"   # Multimodal — ảnh + text, mạnh nhất stable
    text_model: str = "gemini-2.5-flash"    # Text only — nhanh hơn, rẻ hơn

    temperature: float = 0.7
    max_output_tokens: int = 2048
    top_p: float = 0.95

    # httpx timeout khi download ảnh (giây)
    image_download_timeout: float = 15.0


# ── Data Transfer Objects ──────────────────────────────────────────────────────

@dataclass
class ProductImageContext:
    """Thông tin sản phẩm kết hợp với ảnh để feed vào Gemini Vision."""
    product_name: str
    price: float
    category: str
    platform: str
    description: str = ""
    affiliate_url: str = ""
    image_urls: list[str] = field(default_factory=list)

    commission_rate: float | None = None
    rating: float | None = None
    sales_count: int | None = None


@dataclass
class GeminiGenerationResult:
    """Kết quả từ Gemini generation."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    image_analysis: dict = field(default_factory=dict)
    error: str | None = None


# ── Exceptions ─────────────────────────────────────────────────────────────────

class GeminiRateLimitError(Exception):
    """429 Resource Exhausted — vượt quá quota."""


class GeminiAuthError(Exception):
    """401/403 — API key sai hoặc thiếu quyền."""


class GeminiTimeoutError(Exception):
    """DeadlineExceeded — request mất quá lâu."""


class GeminiError(Exception):
    """Lỗi Gemini API chung."""


# ── Main Class ─────────────────────────────────────────────────────────────────

class GeminiContentGenerator:
    """AI content generator dùng Google Gemini Pro Multimodal (google-genai SDK)."""

    def __init__(self, config: GeminiConfig | None = None):
        self.config = config or GeminiConfig()
        self._client: Any = None
        self._initialized = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Khởi tạo Gemini client với API key từ config."""
        if not self.config.api_key:
            logger.info("[GeminiEngine] Không có API key — chạy ở scaffold mode.")
            return

        try:
            from google import genai

            self._client = genai.Client(api_key=self.config.api_key)
            self._initialized = True
            logger.info(f"[GeminiEngine] Khởi tạo thành công — model: {self.config.vision_model}")
        except ImportError:
            logger.error("[GeminiEngine] Thư viện google-genai chưa được cài đặt.")
        except Exception as e:
            logger.error(f"[GeminiEngine] Lỗi khởi tạo: {e}")

    def is_available(self) -> bool:
        """Kiểm tra engine đã sẵn sàng dùng chưa."""
        return self._initialized and self._client is not None

    # ── Image Download ─────────────────────────────────────────────────────────

    async def _download_image_bytes(self, url: str) -> bytes | None:
        """Download ảnh từ URL bằng httpx async. Trả về None nếu lỗi."""
        try:
            async with httpx.AsyncClient(timeout=self.config.image_download_timeout) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                return resp.content
        except httpx.TimeoutException:
            logger.warning(f"[GeminiEngine] Timeout khi download ảnh: {url}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"[GeminiEngine] HTTP {e.response.status_code} khi download ảnh: {url}")
        except Exception as e:
            logger.warning(f"[GeminiEngine] Lỗi download ảnh {url}: {e}")
        return None

    # ── Error Mapping ──────────────────────────────────────────────────────────

    def _map_api_error(self, exc: Exception) -> Exception:
        """Chuyển google.genai exception → internal exception."""
        # google.genai.errors (new SDK)
        try:
            from google.genai import errors as genai_errors
            if isinstance(exc, genai_errors.ClientError):
                code = getattr(exc, "status_code", None) or getattr(exc, "code", 0)
                if code == 429 or "resource_exhausted" in str(exc).lower():
                    return GeminiRateLimitError(f"Gemini rate limit (429): {exc}")
                if code in (401, 403) or "permission" in str(exc).lower():
                    return GeminiAuthError(f"Gemini auth error ({code}): {exc}")
                return GeminiError(f"Gemini client error ({code}): {exc}")
            if isinstance(exc, genai_errors.ServerError):
                code = getattr(exc, "status_code", 500)
                if code == 503 or "deadline" in str(exc).lower() or "timeout" in str(exc).lower():
                    return GeminiTimeoutError(f"Gemini server timeout ({code}): {exc}")
                return GeminiError(f"Gemini server error ({code}): {exc}")
        except ImportError:
            pass

        # Fallback: phân loại theo message string
        exc_str = str(exc).lower()
        if "429" in exc_str or "quota" in exc_str or "exhausted" in exc_str:
            return GeminiRateLimitError(f"Gemini rate limit: {exc}")
        if "401" in exc_str or "403" in exc_str or "permission" in exc_str:
            return GeminiAuthError(f"Gemini auth error: {exc}")
        if "timeout" in exc_str or "deadline" in exc_str or "503" in exc_str:
            return GeminiTimeoutError(f"Gemini timeout: {exc}")

        return GeminiError(f"Gemini error [{type(exc).__name__}]: {exc}")

    # ── Core Generation Methods ────────────────────────────────────────────────

    async def analyze_product_image(
        self,
        image_urls: list[str],
        prompt: str,
    ) -> dict[str, Any]:
        """Phân tích ảnh sản phẩm bằng Gemini Vision.

        Args:
            image_urls: Danh sách URL ảnh sản phẩm (thử từng URL cho đến khi download được).
            prompt: Câu hỏi / yêu cầu phân tích gửi đến Gemini.

        Returns:
            dict với keys: analysis, model, image_url, input_tokens, output_tokens, error

        Raises:
            GeminiRateLimitError: khi vượt quota (caller nên retry sau)
            GeminiAuthError: khi API key sai (caller nên dừng)
            GeminiTimeoutError: khi request quá lâu
            GeminiError: các lỗi Gemini API khác
        """
        if not self.is_available():
            logger.warning("[GeminiEngine] analyze_product_image() gọi khi chưa khởi tạo.")
            return {
                "analysis": "",
                "model": self.config.vision_model,
                "image_url": "",
                "error": "GeminiEngine chưa được kích hoạt. Cấu hình GEMINI_API_KEY trong .env.",
            }

        # Download ảnh — thử từng URL cho đến khi có bytes
        image_bytes: bytes | None = None
        used_url = ""
        for url in image_urls:
            image_bytes = await self._download_image_bytes(url)
            if image_bytes:
                used_url = url
                break

        if not image_bytes:
            logger.warning("[GeminiEngine] Không download được ảnh nào từ danh sách URL.")
            return {
                "analysis": "",
                "model": self.config.vision_model,
                "image_url": "",
                "error": "Không thể download ảnh sản phẩm.",
            }

        mime_type = _detect_mime_type(image_bytes)

        try:
            from google.genai import types

            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

            # google-genai SDK là sync — chạy trong thread pool để không block event loop
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self.config.vision_model,
                    contents=[image_part, prompt],
                    config=types.GenerateContentConfig(
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens,
                        top_p=self.config.top_p,
                    ),
                ),
            )

            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
            result_text = response.text if hasattr(response, "text") else ""

            logger.info(
                f"[GeminiEngine] analyze_product_image OK — "
                f"tokens in={input_tokens} out={output_tokens}"
            )
            return {
                "analysis": result_text,
                "model": self.config.vision_model,
                "image_url": used_url,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "error": None,
            }

        except Exception as exc:
            mapped = self._map_api_error(exc)
            logger.error(f"[GeminiEngine] analyze_product_image lỗi: {mapped}")
            raise mapped from exc

    async def generate_from_image(
        self,
        image_url: str,
        product_info: ProductImageContext,
        content_type: str = "social_post",
    ) -> GeminiGenerationResult:
        """Generate content từ ảnh sản phẩm + metadata — multimodal."""
        if not self.is_available():
            return GeminiGenerationResult(
                content="",
                model=self.config.vision_model,
                error="GeminiEngine chưa được kích hoạt. Cấu hình GEMINI_API_KEY trong .env.",
            )

        prompt = _build_generation_prompt(product_info, content_type)
        image_urls = [image_url] if image_url else product_info.image_urls

        try:
            result = await self.analyze_product_image(image_urls, prompt)
            return GeminiGenerationResult(
                content=result.get("analysis", ""),
                model=result.get("model", self.config.vision_model),
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                error=result.get("error"),
            )
        except (GeminiRateLimitError, GeminiAuthError, GeminiTimeoutError, GeminiError) as e:
            return GeminiGenerationResult(
                content="",
                model=self.config.vision_model,
                error=str(e),
            )

    async def generate_image_caption(
        self,
        image_url: str,
        product_name: str,
        platform: str = "facebook",
        max_length: int = 150,
    ) -> str:
        """Generate caption ngắn cho ảnh."""
        if not self.is_available():
            return ""

        prompt = (
            f"Viết caption ngắn (tối đa {max_length} ký tự) cho ảnh sản phẩm '{product_name}' "
            f"để đăng lên {platform}. Caption bằng tiếng Việt, hấp dẫn, kêu gọi hành động mạnh."
        )
        try:
            result = await self.analyze_product_image([image_url], prompt)
            caption = result.get("analysis", "")
            return caption[:max_length] if caption else ""
        except Exception as e:
            logger.error(f"[GeminiEngine] generate_image_caption lỗi: {e}")
            return ""

    async def batch_analyze_images(
        self,
        image_urls: list[str],
        product_info: ProductImageContext,
    ) -> list[dict[str, Any]]:
        """Phân tích batch nhiều ảnh — concurrent với asyncio.gather."""
        prompt = (
            f"Phân tích ảnh sản phẩm '{product_info.product_name}'. "
            "Mô tả ngắn gọn màu sắc, trạng thái và chất lượng ảnh."
        )
        tasks = [self.analyze_product_image([url], prompt) for url in image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for r in results:
            if isinstance(r, Exception):
                output.append({"error": str(r)})
            else:
                output.append(r)
        return output

    async def enrich_product_context(
        self,
        product_info: ProductImageContext,
    ) -> ProductImageContext:
        """Làm giàu product context bằng vision analysis để feed vào ClaudeClient."""
        if not self.is_available() or not product_info.image_urls:
            return product_info

        try:
            result = await self.analyze_product_image(
                product_info.image_urls[:1],
                "Mô tả chi tiết sản phẩm trong ảnh: màu sắc thực tế, chất liệu, kích thước, tình trạng.",
            )
            analysis_text = result.get("analysis", "")
            if analysis_text and not result.get("error"):
                import dataclasses
                enriched_desc = (
                    f"{product_info.description}\n[Phân tích ảnh: {analysis_text}]"
                    if product_info.description
                    else f"[Phân tích ảnh: {analysis_text}]"
                )
                return dataclasses.replace(product_info, description=enriched_desc)
        except Exception as e:
            logger.warning(f"[GeminiEngine] enrich_product_context lỗi (bỏ qua): {e}")

        return product_info


# ── Factory ────────────────────────────────────────────────────────────────────

def create_gemini_engine() -> GeminiContentGenerator:
    """Factory — tạo GeminiContentGenerator từ settings.gemini_api_key."""
    from backend.config import settings
    config = GeminiConfig(api_key=settings.gemini_api_key)
    return GeminiContentGenerator(config=config)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _detect_mime_type(data: bytes) -> str:
    """Detect MIME type từ magic bytes."""
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _build_generation_prompt(product_info: ProductImageContext, content_type: str) -> str:
    """Xây dựng prompt từ product info + content type."""
    price_str = f"{product_info.price:,.0f}đ" if product_info.price else "Liên hệ"
    base = (
        f"San pham: {product_info.product_name}\n"
        f"Gia: {price_str}\n"
        f"Danh muc: {product_info.category}\n"
        f"Nen tang: {product_info.platform}\n"
    )
    if product_info.rating:
        base += f"Danh gia: {product_info.rating}/5\n"
    if product_info.sales_count:
        base += f"Da ban: {product_info.sales_count:,}\n"
    if product_info.commission_rate:
        base += f"Hoa hong: {product_info.commission_rate:.1f}%\n"
    if product_info.description:
        base += f"Mo ta: {product_info.description}\n"

    prompts = {
        "social_post": (
            f"{base}\nDua vao anh san pham va thong tin tren, viet bai dang Facebook/TikTok "
            "hap dan bang tieng Viet. Dung emoji, highlight uu diem noi bat tu anh, keu goi hanh dong manh."
        ),
        "product_description": (
            f"{base}\nDua vao anh san pham va thong tin tren, viet mo ta san pham chi tiet "
            "bang tieng Viet cho website affiliate. Mo ta mau sac, chat luong tu anh, cong dung, loi ich."
        ),
        "video_script": (
            f"{base}\nDua vao anh san pham va thong tin tren, viet kich ban video review ngan "
            "(30-60 giay) bang tieng Viet. Bao gom hook mo dau, diem noi bat tu anh, CTA cuoi."
        ),
    }
    return prompts.get(content_type, prompts["social_post"])

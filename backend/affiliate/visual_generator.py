"""Visual Generator — tạo ảnh tự động cho bài đăng affiliate.

Strategy:
1. Bannerbear API (primary) — nếu có BANNERBEAR_API_KEY
2. Pillow (fallback miễn phí) — tạo product card đơn giản nhưng chuyên nghiệp

Bannerbear: https://www.bannerbear.com/
- Template-based: thiết kế 1 template trên web, generate nhiều ảnh qua API
- Free tier: 60 images/month
- Trả về URL ảnh PNG/JPG sẵn sàng đăng

Pillow fallback:
- Tạo ảnh 1080x1080px (chuẩn Instagram/Facebook)
- Layout: ảnh SP + tên + giá + badge giảm giá + logo platform + CTA
"""

import io
import logging
from pathlib import Path

import httpx

from backend.config import settings
from backend.connectors.base import ProductInfo

logger = logging.getLogger(__name__)

# Kích thước ảnh chuẩn mạng xã hội
IMAGE_W, IMAGE_H = 1080, 1080

# Màu sắc theo platform
PLATFORM_COLORS = {
    "shopee": {"bg": "#EE4D2D", "text": "#FFFFFF"},
    "tiktok_shop": {"bg": "#010101", "text": "#FFFFFF"},
    "shopback": {"bg": "#D0021B", "text": "#FFFFFF"},
    "accesstrade": {"bg": "#1A73E8", "text": "#FFFFFF"},
}


async def generate_visual(
    product: ProductInfo,
    template_id: str | None = None,
) -> str | None:
    """Tạo ảnh cho sản phẩm. Trả về URL ảnh hoặc None nếu thất bại."""
    if settings.bannerbear_api_key:
        url = await _bannerbear_generate(product, template_id)
        if url:
            return url
        logger.warning("Bannerbear thất bại, dùng Pillow fallback")

    return await _pillow_generate(product)


async def _bannerbear_generate(
    product: ProductInfo,
    template_id: str | None,
) -> str | None:
    """Tạo ảnh qua Bannerbear API."""
    if not template_id and not settings.bannerbear_default_template_id:
        logger.info("Không có Bannerbear template ID — bỏ qua Bannerbear")
        return None

    tid = template_id or settings.bannerbear_default_template_id
    discount_pct = ""
    if product.price and product.original_price and product.original_price > product.price:
        pct = int((1 - product.price / product.original_price) * 100)
        discount_pct = f"-{pct}%"

    payload = {
        "template": tid,
        "modifications": [
            {"name": "product_name", "text": product.name[:80]},
            {
                "name": "price",
                "text": f"{product.price:,.0f}₫" if product.price else "Liên hệ",
            },
            {
                "name": "original_price",
                "text": f"{product.original_price:,.0f}₫" if product.original_price else "",
            },
            {"name": "discount_badge", "text": discount_pct},
            {
                "name": "commission",
                "text": f"Hoa hồng {product.commission_rate:.1f}%" if product.commission_rate else "",
            },
            {"name": "platform_logo", "text": product.platform.upper()},
            {
                "name": "product_image",
                "image_url": product.image_url or "",
            },
            {
                "name": "rating",
                "text": f"⭐ {product.rating:.1f}" if product.rating else "",
            },
        ],
        "webhook_url": None,
        "transparent": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.bannerbear.com/v2/images",
                json=payload,
                headers={"Authorization": f"Bearer {settings.bannerbear_api_key}"},
            )
            if resp.status_code == 202:
                data = resp.json()
                image_url = await _poll_bannerbear(client, data["self"])
                return image_url
    except Exception as e:
        logger.error(f"Bannerbear API lỗi: {e}")
    return None


async def _poll_bannerbear(client: httpx.AsyncClient, status_url: str) -> str | None:
    """Chờ Bannerbear render xong (poll tối đa 30 giây)."""
    import asyncio

    for _ in range(10):
        await asyncio.sleep(3)
        resp = await client.get(
            status_url,
            headers={"Authorization": f"Bearer {settings.bannerbear_api_key}"},
        )
        data = resp.json()
        if data.get("status") == "completed":
            return data.get("image_url_png") or data.get("image_url")
        if data.get("status") == "failed":
            return None
    return None


async def _pillow_generate(product: ProductInfo) -> str | None:
    """Tạo ảnh product card bằng Pillow (miễn phí, không cần API key).

    Layout:
    ┌─────────────────────────────┐
    │  [Header: màu platform]     │
    │  [Ảnh sản phẩm - 400px]    │
    │  [Tên sản phẩm]             │
    │  [Giá gốc ~~crossed~~]      │
    │  [Giá sale  ] [-25%]       │
    │  [⭐ 4.8 | 12.5k đã bán]   │
    │  [Hoa hồng: 8.5%]          │
    │  [Mua ngay →] [platform]   │
    └─────────────────────────────┘
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import asyncio

        loop = asyncio.get_event_loop()
        img_bytes = await loop.run_in_executor(None, _draw_card, product)
        if img_bytes:
            # Lưu tạm vào thư mục static, trả về URL tương đối
            static_dir = Path("backend/static/visuals")
            static_dir.mkdir(parents=True, exist_ok=True)
            filename = f"visual_{product.product_id}.png"
            filepath = static_dir / filename
            with open(filepath, "wb") as f:
                f.write(img_bytes)
            return f"/static/visuals/{filename}"
    except ImportError:
        logger.error("Pillow chưa cài. Chạy: pip install pillow")
    except Exception as e:
        logger.error(f"Pillow generate lỗi: {e}")
    return None


def _draw_card(product: ProductInfo) -> bytes | None:
    """Vẽ product card — chạy trong executor (blocking)."""
    from PIL import Image, ImageDraw, ImageFont

    colors = PLATFORM_COLORS.get(product.platform, {"bg": "#1A73E8", "text": "#FFFFFF"})
    bg_color = colors["bg"]

    img = Image.new("RGB", (IMAGE_W, IMAGE_H), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header gradient bar
    for y in range(120):
        alpha = 1 - y / 120
        r, g, b = _hex_to_rgb(bg_color)
        r2 = int(r * alpha + 255 * (1 - alpha))
        g2 = int(g * alpha + 255 * (1 - alpha))
        b2 = int(b * alpha + 255 * (1 - alpha))
        draw.line([(0, y), (IMAGE_W, y)], fill=(r2, g2, b2))

    # Platform label
    try:
        font_large = ImageFont.truetype("arial.ttf", 48)
        font_medium = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 28)
        font_price = ImageFont.truetype("arialbd.ttf", 52)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
        font_price = font_large

    platform_text = product.platform.upper().replace("_", " ")
    draw.text((40, 35), platform_text, font=font_large, fill=colors["text"])

    # Tải ảnh sản phẩm nếu có
    product_img_y = 140
    product_img_h = 380
    if product.image_url:
        try:
            import urllib.request
            with urllib.request.urlopen(product.image_url, timeout=5) as r:
                pimg = Image.open(io.BytesIO(r.read())).convert("RGBA")
                pimg = pimg.resize((380, product_img_h), Image.LANCZOS)
                # Đặt giữa
                x_offset = (IMAGE_W - 380) // 2
                img.paste(pimg, (x_offset, product_img_y), pimg.split()[3])
        except Exception:
            # Placeholder màu nhạt
            draw.rectangle(
                [(IMAGE_W // 2 - 190, product_img_y), (IMAGE_W // 2 + 190, product_img_y + product_img_h)],
                fill="#F0F0F0",
            )
            draw.text(
                (IMAGE_W // 2, product_img_y + product_img_h // 2),
                "🛍️",
                font=font_large,
                fill="#AAAAAA",
                anchor="mm",
            )
    else:
        draw.rectangle(
            [(IMAGE_W // 2 - 190, product_img_y), (IMAGE_W // 2 + 190, product_img_y + product_img_h)],
            fill="#F5F5F5",
        )

    # Badge giảm giá
    if product.price and product.original_price and product.original_price > product.price:
        pct = int((1 - product.price / product.original_price) * 100)
        badge_x, badge_y = IMAGE_W - 160, product_img_y + 10
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + 120, badge_y + 50)],
            radius=8,
            fill="#EE4D2D",
        )
        draw.text((badge_x + 60, badge_y + 25), f"-{pct}%", font=font_medium, fill="white", anchor="mm")

    # Tên sản phẩm
    name_y = product_img_y + product_img_h + 30
    name = product.name[:60] + ("..." if len(product.name) > 60 else "")
    # Wrap text thủ công
    words = name.split()
    lines, line = [], []
    for w in words:
        test = " ".join(line + [w])
        if draw.textlength(test, font=font_medium) < IMAGE_W - 80:
            line.append(w)
        else:
            if line:
                lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))

    for i, ln in enumerate(lines[:2]):
        draw.text((IMAGE_W // 2, name_y + i * 45), ln, font=font_medium, fill="#1A1A1A", anchor="mm")

    text_y = name_y + len(lines[:2]) * 45 + 20

    # Giá sale
    if product.price:
        price_text = f"{product.price:,.0f}₫"
        draw.text((IMAGE_W // 2, text_y), price_text, font=font_price, fill="#EE4D2D", anchor="mm")
        text_y += 65

    # Giá gốc (gạch ngang)
    if product.original_price and product.price and product.original_price > product.price:
        orig_text = f"{product.original_price:,.0f}₫"
        orig_x = IMAGE_W // 2
        draw.text((orig_x, text_y), orig_text, font=font_small, fill="#999999", anchor="mm")
        orig_w = draw.textlength(orig_text, font=font_small)
        mid_y = text_y + 14
        draw.line([(orig_x - orig_w // 2, mid_y), (orig_x + orig_w // 2, mid_y)], fill="#999999", width=2)
        text_y += 45

    # Rating + lượt bán
    meta_parts = []
    if product.rating:
        meta_parts.append(f"⭐ {product.rating:.1f}")
    if product.sales_count:
        cnt = product.sales_count
        meta_parts.append(f"{'%dk' % (cnt // 1000) if cnt >= 1000 else str(cnt)} đã bán")
    if meta_parts:
        draw.text((IMAGE_W // 2, text_y), "  |  ".join(meta_parts), font=font_small, fill="#555555", anchor="mm")
        text_y += 40

    # Hoa hồng
    if product.commission_rate:
        comm_text = f"💰 Hoa hồng {product.commission_rate:.1f}%"
        draw.text((IMAGE_W // 2, text_y), comm_text, font=font_small, fill="#27AE60", anchor="mm")
        text_y += 50

    # CTA button
    btn_y = IMAGE_H - 110
    draw.rounded_rectangle(
        [(IMAGE_W // 2 - 200, btn_y), (IMAGE_W // 2 + 200, btn_y + 60)],
        radius=30,
        fill=bg_color,
    )
    draw.text((IMAGE_W // 2, btn_y + 30), "Mua ngay →", font=font_medium, fill="white", anchor="mm")

    # Footer
    draw.text((IMAGE_W // 2, IMAGE_H - 30), "Affiliate Marketing Automation", font=font_small, fill="#CCCCCC", anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore

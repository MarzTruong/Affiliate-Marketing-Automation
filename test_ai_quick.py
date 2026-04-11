"""
Quick AI Content Generation Test
=================================
Chay: python test_ai_quick.py

Yeu cau: pip install anthropic
         Dat ANTHROPIC_API_KEY trong .env hoac environment variable
"""
import asyncio
import os
import sys

# Load .env
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    print("=" * 60)
    print("LOI: Chua co ANTHROPIC_API_KEY!")
    print()
    print("Buoc 1: Truy cap https://console.anthropic.com/")
    print("Buoc 2: Dang ky tai khoan (can the tin dung)")
    print("Buoc 3: Tao API Key tai Settings > API Keys")
    print("Buoc 4: Paste key vao file .env:")
    print("        ANTHROPIC_API_KEY=sk-ant-api03-xxxx...")
    print("=" * 60)
    sys.exit(1)

import anthropic

SYSTEM_PROMPT = """Bạn là một chuyên gia marketing và copywriter hàng đầu Việt Nam, \
chuyên viết nội dung SEO cho các sàn thương mại điện tử (Shopee, Lazada, TikTok Shop). \
Bạn hiểu rõ thị trường Việt Nam, hành vi người tiêu dùng Việt, và cách tối ưu SEO \
cho Google.com.vn và Cốc Cốc."""

# San pham mau de test
TEST_PRODUCTS = [
    {
        "name": "Tai Nghe Bluetooth Sony WH-1000XM5",
        "price": "7,490,000",
        "category": "Điện tử",
        "platform": "shopee",
        "description": "Tai nghe chống ồn cao cấp, pin 30 giờ, kết nối đa điểm",
    },
    {
        "name": "Kem Chống Nắng Anessa Perfect UV",
        "price": "450,000",
        "category": "Mỹ phẩm",
        "platform": "lazada",
        "description": "SPF50+ PA++++, chống nước, phù hợp da dầu",
    },
]

TEMPLATES = {
    "product_description": {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "prompt": """Viết mô tả sản phẩm hấp dẫn cho sàn {platform}:

**Tên sản phẩm**: {name}
**Giá**: {price} VNĐ
**Danh mục**: {category}
**Thông tin thêm**: {description}

Yêu cầu:
1. Tiêu đề hấp dẫn, chứa từ khóa chính
2. Mô tả ngắn gọn (150-200 từ)
3. 5-7 đặc điểm nổi bật
4. CTA phù hợp
5. 3-5 từ khóa SEO""",
    },
    "social_post": {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "prompt": """Viết bài đăng Facebook quảng bá sản phẩm:

**Tên sản phẩm**: {name}
**Giá**: {price} VNĐ
**Link**: https://affiliate.example.com/product

Yêu cầu: Ngắn gọn, thu hút, emoji phù hợp, 5-10 hashtag tiếng Việt, hook gây tò mò, CTA rõ ràng.""",
    },
}


async def test_generate(product: dict, content_type: str):
    """Generate one piece of content and display results."""
    client = anthropic.AsyncAnthropic(api_key=api_key)
    template_info = TEMPLATES[content_type]

    prompt = template_info["prompt"].format(**product)

    print(f"\n{'='*60}")
    print(f"Dang tao: {content_type} | San pham: {product['name']}")
    print(f"Model: {template_info['model']}")
    print(f"{'='*60}")

    try:
        response = await client.messages.create(
            model=template_info["model"],
            max_tokens=template_info["max_tokens"],
            system=[{"type": "text", "text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Cost calculation (Haiku 4.5 pricing)
        if "haiku" in template_info["model"]:
            cost = (input_tokens * 0.80 + output_tokens * 4.00) / 1_000_000
        else:
            cost = (input_tokens * 3.00 + output_tokens * 15.00) / 1_000_000

        print(f"\n{content}")
        print(f"\n--- Thong ke ---")
        print(f"Input tokens:  {input_tokens:,}")
        print(f"Output tokens: {output_tokens:,}")
        print(f"Chi phi:       ${cost:.4f}")
        print(f"{'='*60}")

        return {"success": True, "cost": cost, "tokens": input_tokens + output_tokens}

    except anthropic.AuthenticationError:
        print("LOI: API Key khong hop le! Kiem tra lai ANTHROPIC_API_KEY trong .env")
        return {"success": False}
    except anthropic.RateLimitError:
        print("LOI: Vuot qua rate limit. Thu lai sau 1 phut.")
        return {"success": False}
    except Exception as e:
        print(f"LOI: {e}")
        return {"success": False}


async def main():
    print("=" * 60)
    print("  TEST TAO NOI DUNG AI - AFFILIATE MARKETING AUTOMATION")
    print("=" * 60)

    total_cost = 0
    total_tokens = 0
    success_count = 0

    # Test 1: Product description (Haiku - cheap)
    result = await test_generate(TEST_PRODUCTS[0], "product_description")
    if result["success"]:
        total_cost += result["cost"]
        total_tokens += result["tokens"]
        success_count += 1
    else:
        print("\nDung test do loi API. Kiem tra API key.")
        return

    # Test 2: Social post (Haiku - cheap)
    result = await test_generate(TEST_PRODUCTS[1], "social_post")
    if result["success"]:
        total_cost += result["cost"]
        total_tokens += result["tokens"]
        success_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"  KET QUA TEST")
    print(f"{'='*60}")
    print(f"Thanh cong: {success_count}/2")
    print(f"Tong tokens: {total_tokens:,}")
    print(f"Tong chi phi: ${total_cost:.4f}")
    print(f"Du kien chi phi 100 mo ta/ngay: ~${total_cost / max(success_count, 1) * 100:.2f}")
    print(f"\nHe thong AI san sang hoat dong!")


if __name__ == "__main__":
    asyncio.run(main())

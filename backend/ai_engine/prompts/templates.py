"""Content Templates với Chain-of-Thought và Few-Shot Learning.

Cấu trúc CoT 3 bước (nhất quán cho mọi loại content):
  [BƯỚC 1 — PHÂN TÍCH SP]   : Hiểu sản phẩm, điểm mạnh/yếu, đối tượng mua
  [BƯỚC 2 — XÁC ĐỊNH GÓC NHÌN]: Chọn angle/hook phù hợp platform + đối tượng
  [BƯỚC 3 — VIẾT NỘI DUNG]  : Thực thi theo format yêu cầu

Few-Shot examples được inject vào đầu prompt qua build_few_shot_prefix().
Backward-compat: SYSTEM_PROMPT_VI vẫn được export (dùng trong client.py cũ).
"""

# Backward-compat export — client.py cũ import từ đây
from backend.ai_engine.prompts.system import BASE_SYSTEM as SYSTEM_PROMPT_VI  # noqa: F401

# ── Chain-of-Thought header (nhúng vào mọi template) ─────────────────────────
_COT_HEADER = """\
Trước khi viết, hãy suy nghĩ ngắn gọn qua 3 bước (đặt trong <thinking>...</thinking>):

<thinking>
[BƯỚC 1 — PHÂN TÍCH SP]
- Sản phẩm này giải quyết vấn đề gì? Ai là người mua điển hình?
- Điểm mạnh nổi bật nhất (giá, chất lượng, tính năng, thương hiệu)?
- Có rủi ro/nhược điểm nhỏ nào cần thừa nhận để tăng độ tin cậy?

[BƯỚC 2 — XÁC ĐỊNH GÓC NHÌN]
- Angle phù hợp nhất cho platform {{ platform }}: giá rẻ / chất lượng / trending / giải quyết pain point?
- Hook mở đầu nào sẽ dừng scroll / gây tò mò ngay lập tức?

[BƯỚC 3 — KẾ HOẠCH VIẾT]
- Format nào phù hợp? Tone: thân thiện / chuyên nghiệp / hài hước?
- CTA duy nhất cần truyền tải là gì?
</thinking>

Sau khi suy nghĩ, viết nội dung theo format yêu cầu bên dưới:\
"""


def build_few_shot_prefix(examples: list[dict]) -> str:
    """Tạo few-shot prefix từ danh sách ví dụ đã được approve.

    Args:
        examples: List[{"content_type": str, "product_category": str, "final_text": str}]
                  Lấy từ bảng AITrainingData.

    Returns:
        Chuỗi few-shot examples để nhúng vào đầu prompt, hoặc "" nếu không có.
    """
    if not examples:
        return ""

    lines = ["--- VĂN MẪU THAM KHẢO (đã được duyệt) ---\n"]
    for i, ex in enumerate(examples, 1):
        category = ex.get("product_category", "")
        text = ex.get("final_text", "").strip()
        if text:
            lines.append(f"Ví dụ {i} ({category}):\n{text}\n")
    lines.append("--- KẾT THÚC VĂN MẪU ---\n\nBây giờ hãy viết nội dung mới cho sản phẩm sau:\n")
    return "\n".join(lines)


# ── Templates ─────────────────────────────────────────────────────────────────

PRODUCT_DESCRIPTION_TEMPLATE = """\
{{ few_shot_prefix }}\
{{ cot_header }}

**Thông tin sản phẩm:**
- Tên: {{ product_name }}
- Giá: {{ price }} VNĐ
- Danh mục: {{ category }}
- Mô tả gốc: {{ description }}
- Sàn đăng: {{ platform }}

**Yêu cầu đầu ra:**

## Tiêu đề
[Tiêu đề listing ≤ 100 ký tự, chứa từ khóa mua hàng]

## Mô tả ngắn
[150-200 từ, dùng "bạn" thân thiện, nhấn vào lợi ích thực tế]

## Đặc điểm nổi bật
- [Lợi ích 1 — cụ thể, có số liệu nếu có]
- [Lợi ích 2]
- [Lợi ích 3]
- [Lợi ích 4]
- [Lợi ích 5]

## CTA
[1 câu kêu gọi hành động, tạo urgency tự nhiên]

## Từ khóa SEO
[5-7 từ khóa phân tách bằng dấu phẩy, mix ngắn + dài]\
"""

SEO_ARTICLE_TEMPLATE = """\
{{ few_shot_prefix }}\
{{ cot_header }}

**Thông tin sản phẩm:**
- Tên: {{ product_name }}
- Giá: {{ price }} VNĐ
- Danh mục: {{ category }}
- Mô tả gốc: {{ description }}
- Sàn / Link affiliate: {{ platform }} — {{ affiliate_url }}

**Yêu cầu đầu ra (bài 800-1200 từ):**

## Meta Title
[≤ 60 ký tự, chứa "review" hoặc "đánh giá" + tên SP]

## Meta Description
[≤ 160 ký tự, tóm tắt bài, chứa CTA ngắn]

## Nội dung bài viết
[Bài hoàn chỉnh với cấu trúc H2/H3:
- Mở bài: đặt vấn đề người đọc đang gặp
- Tổng quan sản phẩm
- Ưu điểm chi tiết (dẫn chứng cụ thể)
- Nhược điểm (1-2 điểm nhỏ — tăng độ tin cậy)
- So sánh giá/giá trị
- Kết luận + CTA với link affiliate]

## Từ khóa SEO
[6-8 từ khóa: mix head term + long-tail]\
"""

SOCIAL_POST_TEMPLATE = """\
{{ few_shot_prefix }}\
{{ cot_header }}

**Thông tin sản phẩm:**
- Tên: {{ product_name }}
- Giá: {{ price }} VNĐ
- Platform đăng: {{ social_platform }}
- Link affiliate: {{ affiliate_url }}
- Danh mục: {{ category }}

**Yêu cầu đầu ra:**

[Bài đăng hoàn chỉnh, sẵn sàng copy-paste — 100-200 từ]
- Dòng đầu tiên: Hook ≤ 10 từ, đủ mạnh để dừng scroll
- Thân bài: 2-3 điểm lợi ích ngắn, dùng emoji tự nhiên
- Giá + link affiliate rõ ràng
- CTA cuối: 1 hành động duy nhất (bình luận / click link / lưu bài)
- 5-8 hashtag tiếng Việt liên quan\
"""

# ── Platform Variant Templates (One-Click Copy) ───────────────────────────────

TIKTOK_VARIANT_TEMPLATE = """\
Viết caption TikTok affiliate cho sản phẩm sau. CHỈ trả về caption, không giải thích.

**Sản phẩm:** {{ product_name }}
**Giá:** {{ price }} VNĐ
**Danh mục:** {{ category }}
**Mô tả:** {{ description }}
**Link affiliate:** {{ affiliate_url }}

**Yêu cầu TikTok (NGHIÊM NGẶT):**
- Tổng độ dài: 100-150 ký tự (không kể hashtag)
- Dòng 1: Hook gây tò mò ≤ 10 từ, dùng emoji mạnh (😱🔥💥)
- Dòng 2-3: 1-2 lợi ích ngắn + giá rõ ràng
- Dòng 4: Link affiliate ({{ affiliate_url }})
- Dòng 5: 5-6 hashtag trending tiếng Việt (#reviewsanpham #muasamonline #deal...)\
"""

FACEBOOK_VARIANT_TEMPLATE = """\
Viết bài đăng Facebook affiliate cho sản phẩm sau. CHỈ trả về bài đăng, không giải thích.

**Sản phẩm:** {{ product_name }}
**Giá:** {{ price }} VNĐ
**Danh mục:** {{ category }}
**Mô tả:** {{ description }}
**Link affiliate:** {{ affiliate_url }}

**Yêu cầu Facebook:**
- Độ dài: 200-300 ký tự
- Dòng 1: Hook storytelling hoặc câu hỏi gợi mở
- Thân bài: 2-3 lợi ích chính, dùng emoji vừa phải (không quá 5 emoji)
- Giá và link affiliate rõ ràng ở cuối
- CTA: 1 hành động cụ thể (bình luận "GIÁ" / nhấn link)
- 3-5 hashtag ngắn\
"""

TELEGRAM_VARIANT_TEMPLATE = """\
Viết bài đăng Telegram channel affiliate cho sản phẩm sau. CHỈ trả về bài đăng, không giải thích.

**Sản phẩm:** {{ product_name }}
**Giá:** {{ price }} VNĐ
**Danh mục:** {{ category }}
**Mô tả:** {{ description }}
**Link affiliate:** {{ affiliate_url }}

**Yêu cầu Telegram:**
- Độ dài: 300-500 ký tự
- Tiêu đề in đậm: **Tên sản phẩm**
- Mô tả chi tiết: 3-4 điểm lợi ích với emoji bullet (✅ 🔹 ⭐)
- Giá gốc vs giá sale (nếu có) — nếu không có giá sale thì bỏ qua
- Link affiliate nổi bật
- CTA rõ ràng
- Không cần hashtag (Telegram không dùng hashtag nhiều)\
"""


VIDEO_SCRIPT_TEMPLATE = """\
{{ few_shot_prefix }}\
{{ cot_header }}

**Thông tin sản phẩm:**
- Tên: {{ product_name }}
- Giá: {{ price }} VNĐ
- Đặc điểm nổi bật: {{ description }}
- Danh mục: {{ category }}

**Yêu cầu kịch bản (30-60 giây):**

## Hook (0-3s)
[Pattern interrupt — câu hỏi / tuyên bố gây sốc / demo kết quả ngay]

## Giới thiệu (3-10s)
[Tên SP + giá + 1 lý do mua ngay]

## Nội dung chính (10-45s)
[Cảnh 1 — demo tính năng chính]
[Cảnh 2 — before/after hoặc so sánh]
[Cảnh 3 — social proof ngắn]

## CTA (45-60s)
[1 hành động: link bio / sticker / bình luận từ khóa — không ép buộc]

## Nhạc nền gợi ý
[Trend phù hợp danh mục]\
"""


TIKTOK_SCRIPT_TEMPLATE = """\
{{ few_shot_prefix }}\
{{ cot_header }}

**Thông tin sản phẩm:**
- Tên: {{ product_name }}
- Giá: {{ price }} VNĐ
- Danh mục: {{ category }}
- Mô tả: {{ description }}
- Sàn: {{ platform }}

**NHIỆM VỤ:** Viết kịch bản TikTok faceless review 45–60 giây cho sản phẩm trên.

**QUY TẮC BẮT BUỘC:**
1. Đại từ: dùng "mình" — KHÔNG dùng "tôi", "bạn", "chúng ta"
2. Từ CẤM: siêu phẩm, hoàn hảo, tuyệt vời, số 1, tốt nhất, không thể thiếu
3. CTA cuối: luôn kết thúc bằng "nhấn giỏ vàng góc trái nhé" hoặc tương đương
4. KHÔNG đặt link affiliate — dùng "giỏ vàng góc trái" hoặc "link in bio"
5. Chỉ đề cập ĐÚNG 2 tính năng cụ thể trong body (4–35s)
6. Hook (0–3s): tình huống đau/vấn đề thực tế — không giới thiệu sản phẩm ngay

**FORMAT ĐẦU RA — CHỈ trả về bảng markdown dưới đây, không thêm text nào khác:**

| ⏱ Thời gian | 🎙 VOICE (Text-to-Speech) | 📹 VISUAL |
|-------------|--------------------------|-----------|
| 0–3s | *"[Hook: tình huống đau/vấn đề, 10–15 từ, dùng "mình"]"* | [Cảnh mở — thể hiện vấn đề] |
| 4–15s | *"[Tính năng 1: mô tả cụ thể, có số liệu, dùng "mình"]"* | [Close-up demo tính năng 1] |
| 16–35s | *"[Tính năng 2: mô tả cụ thể, có số liệu, dùng "mình"]"* | [Demo tính năng 2 hoặc before/after] |
| 36–45s | *"[CTA: kết quả ngắn gọn + nhấn giỏ vàng góc trái nhé]"* | [Product shot + giỏ vàng overlay] |\
"""

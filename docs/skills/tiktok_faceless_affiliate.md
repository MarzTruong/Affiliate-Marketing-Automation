# Skill: TikTok Faceless Affiliate Script Generator

- **Name:** tiktok_faceless_affiliate
- **Version:** 1.0.0
- **Trigger:** User asks to create a TikTok video, TikTok script, or affiliate review content
- **Language:** Output script in Vietnamese. Report to owner in Vietnamese.
- **Author:** Claude (Lead System Architect)
- **Created:** 2026-04-14

---

## Mục tiêu (Goal)

Tạo script video TikTok affiliate theo phong cách **UGC (User Generated Content)** — chân thực, không lộ mặt, nhắm vào sản phẩm gia dụng thông minh, đồ chăm sóc trẻ cao cấp (địu em bé, máy hâm sữa, v.v.) và phần cứng PC/gaming gear.

Mục tiêu chuyển đổi: Người xem nhấn vào **giỏ hàng affiliate màu vàng** ở góc dưới bên trái màn hình TikTok.

---

## Quy tắc bất biến (Non-negotiable Rules)

| Quy tắc | Chi tiết |
|---------|---------|
| **Đại từ** | Luôn dùng **"mình"** — không dùng "tôi", "bạn", "chúng ta" |
| **Từ cấm** | `siêu phẩm`, `hoàn hảo`, `tuyệt vời`, `số 1`, `tốt nhất`, `không thể thiếu` |
| **Tone** | Chân thực, trò chuyện như bạn bè — KHÔNG phải quảng cáo |
| **Tổng thời lượng** | 45–60 giây đọc tự nhiên |
| **Số tính năng** | Đúng **2 tính năng** thực tế — không hơn, không kém |
| **Hook** | Bắt đầu bằng **pain point cụ thể** — không chào hỏi, không giới thiệu |

---

## Cấu trúc Script (Script Structure)

### HOOK — 0 đến 3 giây
- **Mục tiêu:** Kéo sự chú ý ngay trong 3 giây đầu bằng một vấn đề hàng ngày người xem đang gặp phải.
- **Công thức:** `[Situation người xem đang trong đó] + [Vấn đề / sự khó chịu thực tế]`
- **Ví dụ tốt:** *"Mình mất cả buổi tối chỉ để set up cái router này..."*
- **Ví dụ xấu:** *"Hôm nay mình sẽ giới thiệu cho các bạn một sản phẩm..."*

### BODY — 4 đến 35 giây
- **Mục tiêu:** Trình bày đúng **2 tính năng/thông số thực tế** giải quyết pain point vừa nêu.
- **Công thức mỗi tính năng:** `[Tên tính năng cụ thể] + [Con số / thông số] + [Ý nghĩa thực tế với người dùng]`
- **Lưu ý:** Dùng ngôn ngữ "mình thấy...", "cái hay là...", "điểm mình thích nhất..." — tránh ngôn ngữ catalog.

### CTA — 36 đến 45 giây
- **Mục tiêu:** Hướng người xem đến giỏ hàng affiliate một cách tự nhiên.
- **Công thức:** `[Nhận xét cá nhân ngắn] + [Hành động cụ thể: nhấn vào giỏ vàng góc trái]`
- **Ví dụ tốt:** *"Mình đã dùng được 2 tuần rồi, nếu bạn đang tìm cái tương tự thì link mình để ở giỏ vàng góc trái màn hình nhé."*
- **Ví dụ xấu:** *"Mua ngay hôm nay để nhận ưu đãi đặc biệt!"*

---

## Format Output Bắt buộc

### Bước 1 — Script Table (2 cột)

Xuất script theo bảng **2 cột nghiêm ngặt**:

| ⏱ Thời gian | 🎙 VOICE (AI Text-to-Speech — ElevenLabs) | 📹 VISUAL (B-Roll — Camera Angles) |
|-------------|------------------------------------------|-------------------------------------|
| 0–3s | `[Hook text]` | `[Camera angle / shot description]` |
| 4–15s | `[Tính năng 1 + con số + ý nghĩa]` | `[Close-up / macro shot description]` |
| 16–35s | `[Tính năng 2 + con số + ý nghĩa]` | `[Demo shot / in-use description]` |
| 36–45s | `[CTA tự nhiên → giỏ vàng]` | `[Screen tap animation hint / product shot]` |

> **Ghi chú cột VISUAL:** Mô tả góc quay đủ chi tiết để owner hiểu cần quay gì (ví dụ: "Close-up tay cầm thiết bị từ trên xuống, ánh sáng tự nhiên từ cửa sổ bên trái").

### Bước 2 — SEO Metadata

Sau bảng script, tự động xuất:

```
📝 CAPTION:
[1–2 câu ngắn, engaging, có keyword tự nhiên. Dưới 150 ký tự.]

#️⃣ HASHTAGS (5–7 tags):
[Hashtag trending + niche-specific + product category]
```

**Quy tắc hashtag:**
- 2–3 tag trending rộng (ví dụ: `#reviewsanpham`, `#tiktokshop`)
- 2–3 tag niche cụ thể theo danh mục sản phẩm
- 1 tag brand/product nếu có
- Ưu tiên hashtag tiếng Việt

---

## Danh mục sản phẩm được hỗ trợ (Product Categories)

| Danh mục | Pain points điển hình | Góc quay gợi ý |
|----------|----------------------|----------------|
| Smart home / Router / Camera | Setup phức tạp, lag, mất kết nối | Close-up app interface, speed test screen |
| Gia dụng nhỏ (nồi chiên, máy pha cà phê) | Tốn thời gian nấu, khó vệ sinh | Overhead shot thức ăn, tay thao tác |
| Đồ chăm sóc trẻ (địu, máy hâm sữa) | Mỏi tay, con quấy, an toàn | Side-angle dùng thật, close-up nút điều chỉnh |
| PC Hardware / Gaming Gear | FPS thấp, lag, đau tay khi chơi lâu | Benchmark screen, hand-on-gear shot |
| Phụ kiện điện thoại | Sạc chậm, vỡ màn, hết pin lúc quan trọng | Charging speed demo, drop test setup |

---

## Ví dụ Output Mẫu (Máy hâm sữa)

### Script Table

| ⏱ Thời gian | 🎙 VOICE | 📹 VISUAL |
|-------------|----------|-----------|
| 0–3s | *"3 giờ sáng, mình vừa pha xong bình sữa mà con vẫn khóc vì sữa nguội quá nhanh..."* | Cận cảnh đồng hồ 3:00 AM, tay cầm bình sữa mờ ánh đèn ngủ |
| 4–15s | *"Cái mình đang dùng giữ nhiệt được ở đúng 40°C liên tục 12 tiếng — không cần cắm điện cả đêm."* | Close-up màn hình hiển thị 40.0°C, tay đặt bình vào |
| 16–35s | *"Và thời gian hâm từ lạnh lên 37°C chỉ mất khoảng 3 phút — mình test thật, không phải số quảng cáo."* | Stop-motion đồng hồ đếm ngược 3 phút, bình sữa đổi màu indicator |
| 36–45s | *"Mình dùng được 1 tháng rồi, đêm nào cũng thấy đáng tiền. Bạn nào cần thì nhấn vào cái giỏ vàng góc trái màn hình nhé."* | Product shot từ trên xuống, ngón tay tap nhẹ vào màn hình |

### SEO Metadata

```
📝 CAPTION:
3 giờ sáng pha sữa mà nguội quá nhanh... may mà có cái này 😮‍💨 Review thật sau 1 tháng dùng.

#️⃣ HASHTAGS:
#reviewsanpham #mayhamsua #chamsocbé #tiktokshop #momlife #babycare #giadungthongminh
```

---

## Checklist trước khi xuất (Pre-output Checklist)

Trước khi trả kết quả, AI tự kiểm tra:

- [ ] Script đúng 2 tính năng, không hơn không kém
- [ ] Không có từ cấm (`siêu phẩm`, `hoàn hảo`, `tuyệt vời`, v.v.)
- [ ] Hook bắt đầu bằng pain point — không phải lời chào
- [ ] Dùng đại từ "mình" xuyên suốt
- [ ] CTA đề cập đúng "giỏ vàng góc trái"
- [ ] Tổng thời lượng đọc tự nhiên nằm trong 45–60 giây
- [ ] Caption dưới 150 ký tự
- [ ] Có đúng 5–7 hashtag
- [ ] Cột VISUAL đủ chi tiết để owner hiểu cần quay gì

---

## Tích hợp với hệ thống Automation

Khi được gọi từ pipeline:
- **Input:** `ProductInfo` object (tên, ảnh, giá, commission, danh mục)
- **Output:** Lưu vào `ContentPiece` với `content_type = "tiktok_script"`
- **Audio:** Cột VOICE → đưa vào `ElevenLabsEngine` để tạo narration MP3
- **Video:** Cột VISUAL → đưa vào `HeyGenEngine` để tạo hook/outro clips
- **Notify:** Gửi Telegram với script + download links khi assets sẵn sàng

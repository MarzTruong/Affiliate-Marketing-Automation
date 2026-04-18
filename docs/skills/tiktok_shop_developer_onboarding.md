# TikTok Shop Developer — Hướng dẫn Apply (Vietnam)

> **Mục đích:** Giúp owner (Non-Dev) tự tay apply TikTok Shop Developer Custom App để lấy API credentials cho Kênh 1 & Kênh 2.
> **Thời gian dự kiến:** 2-3 tuần từ lúc nộp đến lúc được duyệt.
> **Chi phí:** Miễn phí.
> **Yêu cầu trước:** CCCD (căn cước công dân) + email doanh nghiệp hoặc email cá nhân đáng tin.

---

## Checklist tổng quan

- [ ] **Bước 1:** Tạo tài khoản TikTok Shop Seller (VN) — nếu chưa có
- [ ] **Bước 2:** Tạo tài khoản TikTok for Developers
- [ ] **Bước 3:** Verify danh tính qua CCCD
- [ ] **Bước 4:** Tạo Custom App (Private App) cho affiliate
- [ ] **Bước 5:** Request scopes cần thiết (Affiliate Creator + Content Posting)
- [ ] **Bước 6:** Submit App Review
- [ ] **Bước 7:** Nhận credentials → paste vào `/settings` của dashboard

---

## Bước 1 — Tạo TikTok Shop Seller Vietnam

1. Truy cập: https://seller-vn.tiktok.com/
2. Nhấn **"Đăng ký ngay"** → chọn **Cá nhân** (Individual) hoặc **Doanh nghiệp** (Business).
   - **Khuyến nghị:** Chọn **Cá nhân** cho giai đoạn MVP (đủ điều kiện affiliate, không cần giấy phép kinh doanh).
3. Nhập:
   - Số điện thoại VN (nhận OTP)
   - Email (dùng cho liên hệ dev)
   - Mật khẩu mạnh (≥ 12 ký tự)
4. Upload CCCD:
   - Mặt trước + mặt sau
   - Ảnh selfie cầm CCCD (phải thấy rõ mặt + số)
5. Chờ duyệt (thường 1-3 ngày làm việc).

> **Lưu ý:** Nếu bạn đã có tài khoản TikTok Shop đang hoạt động, bỏ qua bước này. Dùng thẳng tài khoản đó.

---

## Bước 2 — Tạo TikTok for Developers Account

1. Truy cập: https://developers.tiktok.com/
2. Nhấn **"Login"** → chọn **"TikTok"** (dùng tài khoản TikTok cá nhân của bạn, không phải Seller).
3. Đồng ý ToS (Terms of Service).
4. Điền thông tin:
   - Full name (đúng theo CCCD)
   - Country: **Vietnam**
   - Developer type: **Individual** (hoặc **Business** nếu có giấy phép)
   - Purpose: Chọn **"Affiliate marketing automation"**

> **Quan trọng:** Phần Purpose viết chi tiết bằng tiếng Anh, ví dụ:
> *"Build automation tool for TikTok Shop affiliate creators to search products, generate content, track orders, and optimize posting schedule. Use cases: product discovery, order tracking, content posting."*

---

## Bước 3 — Verify Identity (KYC)

TikTok yêu cầu verify với creator/business được phép truy cập API:

1. Trong Developer Dashboard → **Settings** → **Identity Verification**
2. Upload CCCD mặt trước + mặt sau (ảnh JPG/PNG, rõ nét, không che góc nào)
3. Selfie real-time (bấm chụp trong app, không upload ảnh cũ)
4. Chờ 1-3 ngày làm việc.

> **Nếu bị reject:** Thường do CCCD mờ hoặc selfie thiếu sáng. Chụp lại ngoài trời ban ngày, không đeo kính, không đội mũ.

---

## Bước 4 — Tạo Custom App (Private App)

**Custom App** = app chỉ dành cho chính bạn sử dụng, không public. Miễn phí, duyệt nhanh hơn Standard App.

1. Dashboard → **Manage Apps** → **Create an App** → chọn **Custom App**
2. Điền form:
   - **App name:** `Affiliate Automation` (hoặc tên bất kỳ)
   - **App description:** *"Personal automation for TikTok Shop affiliate — product search, content generation, order tracking, scheduled posting."*
   - **Category:** `Productivity` hoặc `Marketing`
   - **Website URL:** Bất kỳ (có thể dùng github repo: `https://github.com/MarzTruong/Affiliate-Marketing-Automation`)
   - **Terms of Service URL:** Link tới README của repo
   - **Privacy Policy URL:** Link tới README (hoặc viết 1 trang đơn giản)
   - **Icon:** Upload ảnh 512x512 (có thể dùng icon bất kỳ — AI tạo cũng OK)
3. Nhấn **Create**.

> **Pro tip:** Viết Privacy Policy đơn giản dạng "Tool cá nhân, không thu thập data của người dùng khác, chỉ lưu local database" — 1 đoạn 300 chữ là đủ.

---

## Bước 5 — Request Scopes (Quyền API cần thiết)

Trong app vừa tạo → tab **Scopes** → chọn các scope sau:

### Scope bắt buộc cho dự án này

| Scope | Dùng để | Priority |
|-------|---------|----------|
| `user.info.basic` | Lấy thông tin user đã login | Phải có |
| `video.publish` | Upload video lên TikTok | Phải có |
| `video.upload` | Upload draft | Phải có |
| `video.list` | List video của user | Phải có |
| `affiliate.creator.product.search` | Tìm SP affiliate | Phải có |
| `affiliate.creator.order.list` | Track đơn hàng | Phải có |
| `affiliate.creator.performance.list` | Xem commission + CTR | Phải có |

### Scope optional (có thể thêm sau)

- `research.data.basic` — pull analytics chi tiết (retention@3s, impression source)
- `user.info.profile` — nếu cần thêm info profile

Mỗi scope phải ghi **Justification** (lý do dùng) bằng tiếng Anh:

**Template:**
```
We use this scope to automate affiliate product search and content workflow
for the authenticated creator only. No third-party data is accessed. All data
is stored locally for personal analytics and AI content generation.
```

---

## Bước 6 — Submit App Review

1. Điền đầy đủ:
   - Data usage description (200-500 chữ, nhấn mạnh "personal use, local storage")
   - Screenshot UI của tool (có thể dùng screenshot `/tiktok-studio` dashboard hiện tại)
   - Demo video 1-2 phút quay màn hình workflow (OBS Studio record)
2. Nhấn **Submit for Review**.
3. Chờ:
   - Lần review đầu: 7-14 ngày
   - Nếu reject: fix theo feedback → resubmit (thường thêm 5-7 ngày)

> **Tip tăng tỉ lệ duyệt:**
> - Demo video nói tiếng Anh, rõ ràng, slow-paced
> - Emphasize "single-user, personal automation"
> - KHÔNG nhắc đến "sell data", "scrape", "crawl"

---

## Bước 7 — Nhận Credentials

Sau khi duyệt, trong app dashboard sẽ hiện:

- **Client Key** (aka App ID)
- **Client Secret**
- **Redirect URI** (bạn tự set — dùng `https://localhost:3000/api/auth/tiktok/callback` cho local dev)

### Nhập vào dashboard dự án

1. Mở dashboard: http://localhost:3000/settings
2. Tab **TikTok Shop** → paste:
   - Client Key
   - Client Secret
   - Redirect URI
3. Nhấn **Save**.
4. Test OAuth flow: nhấn **Connect TikTok** → login → approve scopes.

> **Lưu ý bảo mật:** Client Secret là **bí mật tuyệt đối**, KHÔNG paste lên chat/email/git. Nếu lỡ lộ → revoke trong dashboard dev và tạo mới.

---

## Troubleshooting

### Lỗi 1: "Your application has been rejected"

**Nguyên nhân thường gặp:**
- Privacy Policy URL 404
- Demo video không rõ hoặc không có
- Scopes request quá rộng (xin `user.info.profile` khi không cần)

**Cách fix:** Đọc feedback trong email, chỉnh sửa rồi resubmit.

### Lỗi 2: "Identity verification failed"

**Nguyên nhân:** CCCD mờ, selfie sai góc, hoặc CCCD hết hạn.

**Cách fix:** Chụp CCCD mới ngoài trời ban ngày, selfie theo hướng dẫn trong app.

### Lỗi 3: OAuth redirect trả về error sau khi approved

**Nguyên nhân:** Redirect URI không khớp giữa app dashboard và code.

**Cách fix:** Đảm bảo URI giống 100% (kể cả trailing slash, http vs https).

### Lỗi 4: API trả về `invalid_scope`

**Nguyên nhân:** Scope bị reject nhưng code đang gọi.

**Cách fix:** Check scope list trong app dashboard, re-submit scope còn thiếu.

---

## FAQ

**Q: Có cần giấy phép kinh doanh không?**
A: KHÔNG, cá nhân VN có CCCD là đủ cho Custom App (nhưng nếu muốn scale lên Standard App thì cần).

**Q: Tôi có thể dùng tài khoản TikTok đang dùng hằng ngày để apply không?**
A: Được, nhưng tốt nhất tạo TikTok account riêng cho developer để tách biệt.

**Q: App Review mất bao lâu?**
A: 7-14 ngày cho lần đầu. Nếu reject + resubmit, cộng thêm 5-7 ngày.

**Q: Sau khi approved, credentials có hạn không?**
A: Không, nhưng TikTok có thể revoke nếu phát hiện vi phạm ToS. Check định kỳ.

**Q: Nếu tôi pause không dùng 6 tháng, app có bị disable không?**
A: Có thể. TikTok disable inactive apps. Gọi API tối thiểu 1 lần/tháng để giữ active.

---

## Next Steps sau khi có Credentials

1. ✅ Dev integrate TikTok Shop Connector (`backend/tiktok_shop/connector.py`)
2. ✅ Test product search API → lấy 10 SP mẹ & bé đầu tiên
3. ✅ Test order tracking API với 1 đơn mẫu
4. ✅ Tag Queue UI → publish 1 video thật → confirm đơn tracking hoạt động
5. ✅ Bật Phase 1 Warm Up

---

## References

- [TikTok for Developers — Getting Started](https://developers.tiktok.com/doc/getting-started-create-an-app)
- [Affiliate Creator API Overview](https://partner.tiktokshop.com/docv2/page/affiliate-creator-api-overview)
- [Content Posting API](https://developers.tiktok.com/products/content-posting-api/)
- [Vietnam Eligibility Guide](https://seller-vn.tiktok.com/university/essay?knowledge_id=104015979497218)

---

**Version:** 1.0
**Ngày cập nhật:** 2026-04-18
**Tác giả:** Brainstorm session — Kênh TikTok dual-channel design

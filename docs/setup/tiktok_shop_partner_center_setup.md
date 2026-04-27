# TikTok Shop Partner Center — Setup Guide
> Hướng dẫn đăng ký **partner.tiktokshop.com** để lấy credentials cho Affiliate & Shop API.
> Guide còn lại: [TikTok Content Posting API Setup](tiktok_content_posting_api_setup.md)

---

## Phân biệt 2 platform TikTok

> **Quan trọng:** Đây là 2 hệ thống hoàn toàn riêng biệt — token, credentials, OAuth flow đều KHÔNG dùng chung được.

| | TikTok for Developers | TikTok Shop Partner Center |
|---|---|---|
| **URL** | developers.tiktok.com | partner.tiktokshop.com |
| **Mục đích trong dự án** | Upload/đăng video lên TikTok | Lấy sản phẩm affiliate, track đơn & hoa hồng |
| **API endpoint** | `open.tiktokapis.com/v2` | `open-api.tiktokglobalshop.com` |
| **Đăng nhập bằng** | Tài khoản TikTok cá nhân | Email mới (tạo riêng) |
| **Loại credentials** | Client Key + Client Secret | App Key + App Secret |
| **Settings key trong DB** | `tiktok_client_key` / `tiktok_client_secret` | `tiktok_shop_app_key` / `tiktok_shop_app_secret` |
| **Xác thực người dùng** | OAuth 2.0 (user cấp quyền) | App Key tĩnh (không cần user login) |
| **Thời gian duyệt app** | 3–7 ngày làm việc | 2–5 ngày làm việc |
| **Trạng thái hiện tại** | ✅ App tạo xong, chờ upload demo video → submit | ⏳ Chưa thực hiện |

---

## Thông tin chung

> **Mục đích:** Giúp owner (Non-Dev) tự tay đăng ký TikTok Shop Partner Center để lấy API credentials.
> **Nền tảng:** https://partner.tiktokshop.com
> **Thời gian dự kiến:** 2-5 ngày làm việc.
> **Chi phí:** Miễn phí.
> **KHÔNG cần:** Giấy phép kinh doanh, giấy chứng nhận đăng ký công ty — nếu chọn đúng hạng mục bên dưới.

> **⚠️ Lưu ý:** Partner Center là hệ thống RIÊNG — bắt buộc tạo tài khoản mới bằng email, KHÔNG đăng nhập bằng tài khoản TikTok cá nhân hay Seller Center.

---

## Checklist tổng quan

- [ ] **Bước 1:** Tạo tài khoản Partner Center (email + mật khẩu)
- [ ] **Bước 2:** Nhấn "Bắt đầu" → Wizard 3 bước → Chọn đúng hạng mục
- [ ] **Bước 3:** Điền thông tin chi tiết → Gửi → Chờ duyệt
- [ ] **Bước 4:** Vào App & Service → Tạo Custom App
- [ ] **Bước 5:** Apply permissions → Nhận App Key + App Secret
- [ ] **Bước 6:** Paste credentials vào `/settings` của dashboard

---

## Bước 1 — Tạo tài khoản Partner Center

1. Truy cập: https://partner.tiktokshop.com
2. Nhấn **"Join now"** (góc trên phải).
3. Điền email + mật khẩu → xác nhận email (OTP).
4. Đăng nhập → sẽ thấy trang **"Hồ sơ"**.

> Trang Hồ sơ hiển thị ô "Bắt đầu hoạt động kinh doanh của bạn" ở bên phải — đây là bước tiếp theo.

---

## Bước 2 — Chọn hạng mục (Wizard 3 bước)

Nhấn **"Bắt đầu"** → vào wizard 3 bước: **Hạng mục & thị trường → Điền thông tin chi tiết → Xem xét & phê duyệt**

### Bước 2a — Hạng mục & thị trường

| Trường | Giá trị |
|--------|---------|
| Khu vực đăng ký | **Việt Nam** (không đổi được sau khi duyệt) |
| Thị trường mục tiêu | **Việt Nam** |

**Hạng mục kinh doanh — chọn đúng như sau:**

Dropdown "Hạng mục kinh doanh" có 4 nhóm chính:

| Nhóm | Subcategory |
|------|------------|
| MCN/CAP | Quản lý nhà sáng tạo |
| **Nhà phát triển ứng dụng** | Dịch vụ khách hàng, Marketing, **Nhà phát triển nội bộ của người bán**, Quản lý thương mại điện tử, Thúc đẩy bán hàng, Tài chính, Tương tác với khách hàng, Vận chuyển & Hoàn thiện |
| TikTok Shop Partner (TSP) | Quản lý cửa hàng (cho TSP), Quản lý nội dung (cho TSP) |
| Đối tác liên kết | Kết hợp người bán và nhà sáng tạo phân cấp |

### Lựa chọn khuyến nghị:

> **Chọn: "Nhà phát triển ứng dụng" → "Nhà phát triển nội bộ của người bán"**

**Lý do:**
- "Nhà phát triển nội bộ của người bán" = developer tự build tool cho shop của chính mình → **KHÔNG yêu cầu giấy chứng nhận đăng ký công ty**.
- Các hạng mục khác (TSP, MCN) yêu cầu tên pháp lý công ty + giấy chứng nhận sáp nhập + mã số đăng ký công ty.
- Hạng mục này đúng với dự án: bạn là người tự build automation tool cho tài khoản của mình.

**Cách chọn trong giao diện:**
1. Nhấn vào dropdown "Hạng mục kinh doanh"
2. Tích checkbox **"Nhà phát triển ứng dụng"**
3. Cột bên phải xuất hiện — tích **"Nhà phát triển nội bộ của người bán"**
4. Nhấn **Tiếp theo** (hoặc Next)

---

## Bước 3 — Điền thông tin chi tiết

Sau khi chọn hạng mục đúng, bước 2 của wizard yêu cầu điền thông tin. Với "Nhà phát triển nội bộ của người bán", form sẽ nhẹ hơn (không cần giấy tờ công ty).

**Thông tin thường yêu cầu:**

| Trường | Gợi ý điền |
|--------|-----------|
| Tên đối tác / Tên hiển thị | Tên bạn hoặc tên tự đặt |
| Website (nếu có) | `https://github.com/MarzTruong/Affiliate-Marketing-Automation` |
| Giới thiệu về bản thân / doanh nghiệp | *"Cá nhân tự build automation tool để quản lý kênh TikTok affiliate cá nhân. Không phục vụ bên thứ ba."* |
| Kinh nghiệm liên quan | Mô tả ngắn: đã dùng TikTok Shop bao lâu, có kênh TikTok không |
| Thông tin liên hệ | Email + số điện thoại |

Nhấn **"Gửi"** → chuyển sang Bước 3: **Xem xét & phê duyệt**.

> **Thời gian chờ duyệt:** 2-5 ngày làm việc. Kiểm tra email (kể cả spam).

---

## Bước 4 — Tạo App sau khi được duyệt

Sau khi tài khoản được duyệt, menu trái Partner Center sẽ mở rộng thêm các mục mới.

1. Tìm **"App & Service"** trong menu trái → nhấn vào.
2. Nhấn **"Create app & service"** (hoặc "Tạo ứng dụng").
3. Chọn loại app:
   - **Custom App** → dùng riêng cho bạn, không public (chọn cái này cho MVP).
   - Public App → đăng lên TikTok Shop App Store (phức tạp hơn, không cần thiết).
4. Điền thông tin App:

| Trường | Gợi ý điền |
|--------|-----------|
| App name | `Affiliate Automation` |
| Category | `Marketing` hoặc `Productivity` |
| Logo | Upload ảnh 512x512 (AI tạo OK) |
| Target market | Việt Nam |
| Redirect URL | `http://localhost:8000/auth/tiktok/callback` |
| Webhook URL | Để trống hoặc `http://localhost:8000/webhooks/tiktok` |

5. Nhấn **"Create App"** → copy ngay **App Key** và **App Secret** từ trang detail.

---

## Bước 5 — Apply API Permissions

Trong trang App detail:

1. Tìm tab **"Manage API"** hoặc **"API Permissions"**.
2. Apply các permission cần thiết:

| Permission | Dùng để |
|-----------|---------|
| `affiliate.creator.product.search` | Tìm sản phẩm affiliate |
| `affiliate.creator.order.list` | Track đơn hàng |
| `affiliate.creator.performance.list` | Xem hoa hồng, CTR |
| `video.publish` | Upload video |
| `video.upload` | Upload draft |

3. Justification template (tiếng Anh):
```
Personal automation tool for my own TikTok Shop affiliate account only.
Used to search affiliate products, track my own orders, and publish
content. No third-party data access. All data stored locally.
```

---

## Bước 6 — Kết nối Dashboard

1. Mở: http://localhost:3000/settings
2. Tab **TikTok Shop** → paste:
   - App Key
   - App Secret
   - Redirect URI: `http://localhost:8000/auth/tiktok/callback`
3. Nhấn **Save** → nhấn **"Connect TikTok"** → test OAuth flow.

> **Bảo mật:** App Secret KHÔNG paste vào chat, email, hay git. Nếu lộ → revoke trong Partner Center và tạo key mới.

---

## Nếu bị yêu cầu Giấy chứng nhận đăng ký công ty

> **Dấu hiệu bạn chọn sai hạng mục:** Form bước 2 hiển thị "Tên pháp lý của công ty", "Giấy chứng nhận sáp nhập", "Mã số đăng ký công ty" → đây là form của TSP hoặc MCN.

**Cách fix:** Nhấn **"Quay lại"** → Bước 1 → chọn lại **"Nhà phát triển ứng dụng" → "Nhà phát triển nội bộ của người bán"**.

Nếu không quay lại được (đã submit), liên hệ support qua "Trợ giúp" (góc trên phải Partner Center) để đổi hạng mục.

---

## Troubleshooting

### Không tìm thấy "App & Service" sau khi được duyệt
Tài khoản vẫn đang trong trạng thái "Đang xem xét". Chờ thêm và kiểm tra email.

### OAuth callback lỗi sau khi approved
Redirect URI trong App detail phải giống 100% với `TIKTOK_REDIRECT_URI` trong `.env` — kể cả `http` vs `https`, trailing slash.

### Token hết hạn sau 24h
Giới hạn Sandbox. Re-auth qua `/auth/tiktok` mỗi ngày. Production có refresh_token tự động.

---

## FAQ

**Q: Tôi có cần tài khoản TikTok Shop Seller không?**
A: Không bắt buộc để đăng ký Partner Center. Nhưng để test affiliate API thật (track đơn, hoa hồng) thì cần là Affiliate Creator trên TikTok Shop.

**Q: "Nhà phát triển nội bộ của người bán" có thể dùng affiliate API không?**
A: Có — bạn có thể apply permission `affiliate.creator.*` cho bất kỳ app nào, kể cả internal developer app.

**Q: Custom App vs Public App?**
A: Custom App = dùng riêng, duyệt nhanh. Public App = lên App Store, review nghiêm. Dùng Custom App cho dự án này.

**Q: Credentials có hạn không?**
A: App Key/Secret không hết hạn. Access Token hết hạn 24h (sandbox). TikTok có thể revoke nếu vi phạm ToS.

---

## Next Steps sau khi có Credentials

1. Paste App Key + App Secret → http://localhost:3000/settings
2. Test OAuth: nhấn "Connect TikTok" → xác nhận callback
3. Dev: wire TikTok Shop Connector với real credentials
4. Test product search API → lấy 10 SP đầu tiên
5. Tag Queue → publish 1 video thật → bật Phase 1

---

## References

- [TikTok Shop Partner Center](https://partner.tiktokshop.com)
- [Developer Onboarding Docs](https://partner.tiktokshop.com/docv2/page/developer-onboarding)
- [Affiliate Creator API Overview](https://partner.tiktokshop.com/docv2/page/6697960798b0a502f89e3d00)

---

**Version:** 3.0
**Ngày cập nhật:** 2026-04-19
**Lý do cập nhật:** Fix theo giao diện thực tế (ảnh chụp màn hình từ owner) — thêm wizard 3 bước, tên hạng mục đúng theo UI tiếng Việt, cảnh báo tránh chọn TSP/MCN (yêu cầu giấy tờ công ty), khuyến nghị "Nhà phát triển nội bộ của người bán".

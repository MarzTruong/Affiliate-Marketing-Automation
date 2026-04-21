# TikTok for Developers — Setup Guide (Content Posting API)
> Hướng dẫn hoàn tất setup app tại **developers.tiktok.com** để upload video lên TikTok tự động.
> Guide còn lại: [TikTok Shop Partner Center Setup](tiktok_shop_partner_center_setup.md)

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

## Thông tin app (Production)

- **App name:** Affiliate Automation
- **Organization:** Lab Gia Dụng
- **Tab đang dùng:** Production (không phải Sandbox)
- **Client Key:** awfhheejs84z5x8k *(lưu trong system_settings DB, không commit)*

---

## 1. App Details

### Category
- Utilities

### Description (120 ký tự)
```
Personal automation tool to generate and post TikTok affiliate content for my own channels. No third-party access.
```

### Terms of Service URL
```
https://marztruong.github.io/Affiliate-Marketing-Automation/terms.html
```

### Privacy Policy URL
```
https://marztruong.github.io/Affiliate-Marketing-Automation/privacy.html
```

### Platforms
- ✅ Web

### Web/Desktop URL
```
https://marztruong.github.io/Affiliate-Marketing-Automation
```

### Verify URL properties
**Phương pháp:** URL prefix (chọn cái này, không chọn Domain)

**Quy trình verify:**
1. Click "URL properties" (góc phải trên)
2. "Verify properties" → chọn **URL prefix**
3. Nhập: `https://marztruong.github.io/Affiliate-Marketing-Automation/` *(có trailing slash)*
4. TikTok tạo file `.txt` dạng `tiktokXXXXX.txt`
5. Xem nội dung file → báo cho Claude
6. Claude tạo file trong `docs/` → push lên GitHub
7. Chờ 2-3 phút → mở URL file trong browser để confirm live
8. Click **Verify**

**Lưu ý quan trọng:**
- Mỗi lần click Verify, TikTok có thể tạo file mới → phải tạo lại file mới trong repo
- Verify 1 lần cho base URL → cover luôn terms.html, privacy.html, và web URL
- KHÔNG dùng `raw.githubusercontent.com` — TikTok không verify được
- KHÔNG dùng Domain method vì `github.io` không cho phép thêm DNS record

---

## 2. App Review

### Description text (copy-paste vào form)
```
This is a personal affiliate marketing automation tool for a single user (the developer).

Login Kit: Used to authenticate the developer's own TikTok account via OAuth 2.0, obtaining an access token to interact with TikTok APIs on behalf of the account owner.

Content Posting API: Used to upload pre-produced short-form video content (MP4) to the developer's TikTok account. The app generates product review videos using AI tools, then publishes them as direct posts to the TikTok profile.

video.publish scope: Required to directly post videos to the authorized user's TikTok profile as public posts.

video.upload scope: Required to upload video files to TikTok before publishing.

user.info.basic scope: Required to retrieve the user's open_id after OAuth login to associate the access token with the correct account.

The app is used exclusively by the developer/owner to automate affiliate content creation and posting workflow. No end-users are involved.
```

### Demo video
- Quay màn hình (Windows + G) show: Dashboard app, TikTok Studio, Swagger API docs
- Format: mp4/mov, tối đa 50MB, tối đa 5 files
- **Đây là bước còn lại duy nhất để submit**

---

## 3. Products

| Product | Trạng thái | Ghi chú |
|---------|-----------|---------|
| Login Kit | ✅ Added | Cần Redirect URI |
| Content Posting API | ✅ Added | Direct Post: ON |
| Share Kit | ❌ Không cần | Có thể xóa |

### Login Kit — Redirect URI (Web)
```
https://marztruong.github.io/Affiliate-Marketing-Automation/callback.html
```
*(Sẽ cập nhật thành backend URL thật khi có domain public)*

---

## 4. Scopes

| Scope | Nguồn | Trạng thái |
|-------|-------|-----------|
| user.info.basic | Login Kit | ✅ |
| video.publish | Content Posting API | ✅ |
| video.upload | Content Posting API | ✅ |

Không cần thêm scope nào khác.

---

## 5. Lưu ý Production vs Sandbox

- **Sandbox tab** có Client Key/Secret riêng → dùng để test
- **Production tab** có Client Key/Secret riêng → dùng khi đăng thật (sau khi được approve)
- Lưu cả 2 bộ credentials vào `system_settings` DB với key riêng biệt
- Hiện tại đang dùng **Plan D' Hybrid** (upload thủ công) → chưa cần dùng API credentials

---

## 6. GitHub Pages (docs/)

Files đã có:
- `docs/index.html` — landing page
- `docs/terms.html` — Terms of Service
- `docs/privacy.html` — Privacy Policy
- `docs/callback.html` — OAuth callback page
- `docs/tiktokXXXX.txt` — TikTok verification signature files

URL base: `https://marztruong.github.io/Affiliate-Marketing-Automation/`

---

## 7. Sau khi được approve

1. Lấy Production Client Key + Secret từ TikTok developer portal
2. Lưu vào `system_settings` DB qua UI `/settings`
3. Cập nhật Redirect URI thành backend URL thật (nếu triển khai server public)
4. Implement OAuth flow trong `backend/tiktok/auth.py` dùng Production credentials

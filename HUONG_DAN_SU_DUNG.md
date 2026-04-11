# Affiliate Marketing Automation - Huong Dan Su Dung

## Muc luc

1. [Gioi thieu](#1-gioi-thieu)
2. [Cai dat](#2-cai-dat)
3. [Cau hinh](#3-cau-hinh)
4. [Chay he thong](#4-chay-he-thong)
5. [Huong dan su dung tung tinh nang](#5-huong-dan-su-dung-tung-tinh-nang)
6. [API Reference](#6-api-reference)
7. [Xu ly su co](#7-xu-ly-su-co)

---

## 1. Gioi thieu

He thong tu dong hoa tiep thi lien ket (Affiliate Marketing) cho cac san thuong mai dien tu Viet Nam. Su dung AI (Claude API) de tao noi dung SEO, tu dong dang bai, phan tich hieu suat va phat hien gian lan.

### Tinh nang chinh

- **AI Content Generation**: Tao bai viet SEO, mo ta san pham, bai mang xa hoi, kich ban video bang tieng Viet
- **5 Nen tang ket noi**: Shopee, Lazada, TikTok Shop, ShopBack, AccessTrade VN
- **3 Kenh dang bai**: Facebook Page, WordPress, Telegram
- **Phan tich hieu suat**: Dashboard thoi gian thuc, bieu do, xuat CSV
- **Phat hien gian lan**: Click spam, bat thuong thoi gian, dot bien ty le chuyen doi
- **SOP tu hoc**: Cham diem template, A/B testing, tu dong tien hoa prompt
- **He thong thong bao**: Canh bao gian lan, ket qua A/B test, loi he thong

### Kien truc

```
Frontend (Next.js 16)  <-->  Backend (FastAPI)  <-->  PostgreSQL + Redis
                                   |
                          Claude API (Anthropic)
                                   |
                    Shopee / Lazada / TikTok / ShopBack / AccessTrade
```

---

## 2. Cai dat

### Yeu cau he thong

- Python 3.11+
- Node.js 18+
- Docker Desktop (cho PostgreSQL va Redis)
- Anthropic API Key (cho AI content generation)

### Buoc 1: Clone va cai dat backend

```bash
cd "E:/.claude/Affiliate Marketing Automation"

# Tao virtual environment
python -m venv .venv

# Kich hoat (Windows)
.venv\Scripts\activate

# Cai dat dependencies
pip install -e ".[dev]"
```

### Buoc 2: Cai dat frontend

```bash
cd frontend
npm install
```

### Buoc 3: Khoi dong Docker (PostgreSQL + Redis)

```bash
docker compose up -d
```

Kiem tra trang thai:
```bash
docker compose ps
```

---

## 3. Cau hinh

### File .env

Tao file `.env` o thu muc goc voi noi dung:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Claude API (bat buoc de tao noi dung AI)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_DAILY_COST_LIMIT_USD=20.00

# Shopee (tuy chon)
SHOPEE_PARTNER_ID=
SHOPEE_PARTNER_KEY=
SHOPEE_ACCESS_TOKEN=
SHOPEE_SHOP_ID=

# Lazada (tuy chon)
LAZADA_APP_KEY=
LAZADA_APP_SECRET=
LAZADA_ACCESS_TOKEN=

# TikTok Shop (tuy chon)
TIKTOK_APP_KEY=
TIKTOK_APP_SECRET=
TIKTOK_ACCESS_TOKEN=

# ShopBack (tuy chon)
SHOPBACK_PARTNER_ID=
SHOPBACK_API_KEY=

# AccessTrade VN (tuy chon)
ACCESSTRADE_API_KEY=
ACCESSTRADE_SITE_ID=

# Facebook Publisher (tuy chon)
FACEBOOK_PAGE_ID=
FACEBOOK_ACCESS_TOKEN=

# WordPress Publisher (tuy chon)
WORDPRESS_SITE_URL=
WORDPRESS_USERNAME=
WORDPRESS_APP_PASSWORD=

# Telegram Publisher (tuy chon)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=
```

**Luu y**: Chi can `ANTHROPIC_API_KEY` la bat buoc. Cac API key khac chi can khi ban muon ket noi voi nen tang tuong ung.

---

## 4. Chay he thong

### Khoi dong Backend

```bash
cd "E:/.claude/Affiliate Marketing Automation"
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Backend chay tai: http://localhost:8000
API docs (Swagger): http://localhost:8000/docs

### Khoi dong Frontend

```bash
cd frontend
npm run dev
```

Frontend chay tai: http://localhost:3000

### Chay test

```bash
.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

---

## 5. Huong dan su dung tung tinh nang

### 5.1 Tong quan (Dashboard)

Trang chu hien thi:
- **KPI Cards**: Tong luot click, chuyen doi, doanh thu, chi phi AI
- **Bieu do hieu suat**: Xu huong theo ngay (click, chuyen doi, doanh thu)
- **Trang thai he thong**: Kiem tra Database, Redis, Claude API
- **Tong quan he thong**: So chien dich, noi dung, template, A/B test

### 5.2 Chien dich (Campaigns)

**Tao chien dich moi:**
1. Vao trang "Chien dich"
2. Nhan "Tao chien dich"
3. Dien ten, chon nen tang (Shopee/Lazada/TikTok Shop/ShopBack), ngan sach, danh muc
4. Nhan "Tao" -> Chien dich o trang thai "Nhap"

**Kich hoat chien dich:**
- Nhan nut "Kich hoat" ben canh chien dich
- Trang thai chuyen tu "Nhap" sang "Dang chay"

**Tim san pham:**
- Trong chi tiet chien dich, su dung chuc nang "Tim san pham" de tim tren nen tang
- San pham tim duoc se tu dong tao lien ket tiep thi (affiliate link)

### 5.3 Noi dung (Content)

**Tao noi dung AI:**
1. Vao trang "Noi dung"
2. Chon chien dich va san pham
3. Chon loai noi dung:
   - **Mo ta san pham**: Ngan gon, thu hut, co CTA
   - **Bai SEO**: Bai viet dai, toi uu tu khoa cho Google/Coc Coc
   - **Bai mang XH**: Ngan gon cho Facebook/TikTok
   - **Kich ban video**: Kich ban quay video review
4. (Tuy chon) Chon template SOP cu the
5. Nhan "Tao noi dung" -> AI se viet noi dung bang tieng Viet

**Model AI su dung:**
- **Haiku** (nhanh, re): Mo ta san pham, bai mang XH
- **Sonnet** (chat luong cao): Bai SEO, kich ban video

**Tai tao noi dung:**
- Nhan "Tai tao" de AI viet lai voi noi dung khac

### 5.4 Dang bai (Publisher)

**Dang noi dung ngay:**
1. Vao trang "Dang bai"
2. Chon noi dung da tao
3. Chon kenh: Facebook, WordPress, Telegram (co the chon nhieu kenh)
4. Nhan "Dang ngay"

**Len lich dang bai:**
- Su dung API: `POST /api/v1/publisher/schedule`
- Truyen `content_id`, `channels`, `scheduled_at`
- He thong tu dong dang vao thoi diem da hen

**Lich su dang bai:**
- Xem trang thai: Cho xu ly, Da len lich, Dang dang, Da dang, That bai
- Xem ma bai dang va thoi gian

### 5.5 SOP & A/B Test

**Template SOP:**
- Danh sach template voi diem hieu suat (0-100)
- Diem duoc tinh tu: CTR (25%), Ty le chuyen doi (35%), Doanh thu/Hien thi (25%), So luong (15%)
- Nhan "Cham diem lai" de cap nhat diem tu du lieu moi nhat

**A/B Testing:**
1. Tao A/B test giua 2 template (qua API)
2. He thong tu dong phan phoi variant A/B theo round-robin
3. Ghi nhan impression va conversion
4. Tu dong ket thuc khi dat du mau (hoac nhan "Ket thuc som")
5. Xac dinh nguoi thang bang z-test (do tin cay 95%)
6. Template thang duoc +5 diem, thua bi -3 diem

**Tien hoa Prompt (AI):**
- Nhan "Tien hoa" ben canh template
- AI (Sonnet) phan tich template hien tai va tao phien ban cai tien
- Template moi duoc tao tu dong, san sang A/B test

### 5.6 Phan tich (Analytics)

- **Tong quan KPI**: Hien thi, click, CTR, chuyen doi, ty le CD, doanh thu
- **Bieu do xu huong**: Theo ngay, trong 30 ngay gan nhat
- **Hieu suat theo nen tang**: Bang so sanh Shopee/Lazada/TikTok/ShopBack
- **Xuat CSV**: Nhan "Xuat CSV" de tai du lieu phan tich

**Canh bao gian lan:**
- Click spam: >10 click/IP/gio
- Bat thuong thoi gian: Click den deu dan (bot)
- Dot bien ty le chuyen doi: >15% (bat thuong)

### 5.7 Cai dat (Settings)

- Xem cac nen tang da ket noi va trang thai
- Danh sach API key can cau hinh
- Ho tro: Shopee, Lazada, TikTok Shop, ShopBack, AccessTrade, Facebook, WordPress, Telegram

### 5.8 Thong bao (Notifications)

- Xem thong bao gian lan, ket qua A/B test, loi he thong
- Mau sac theo muc do: Xanh (thong tin), Vang (canh bao), Do (loi), Do dam (nghiem trong)
- Danh dau da doc tung thong bao hoac tat ca
- Badge so thong bao chua doc o sidebar (tu dong cap nhat moi 30 giay)

---

## 6. API Reference

Backend API chay tai `http://localhost:8000/api/v1/`

### Campaigns
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | /campaigns | Tao chien dich moi |
| GET | /campaigns | Danh sach chien dich |
| GET | /campaigns/{id} | Chi tiet chien dich |
| PATCH | /campaigns/{id} | Cap nhat chien dich |
| POST | /campaigns/{id}/activate | Kich hoat chien dich |
| POST | /campaigns/{id}/products/search | Tim san pham tren nen tang |
| GET | /campaigns/{id}/products | San pham cua chien dich |
| GET | /campaigns/{id}/stats | Thong ke chien dich |

### Content
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | /content/generate | Tao noi dung AI |
| GET | /content | Danh sach noi dung |
| GET | /content/{id} | Chi tiet noi dung |
| POST | /content/{id}/regenerate | Tai tao noi dung |

### Publisher
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | /publisher/publish | Dang bai ngay |
| POST | /publisher/schedule | Len lich dang bai |
| GET | /publisher/publications | Lich su dang bai |
| GET | /publisher/channels | Danh sach kenh |

### Analytics
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | /analytics/overview | Tong quan KPI |
| GET | /analytics/daily | Thong ke theo ngay |
| GET | /analytics/by-platform | Theo nen tang |
| GET | /analytics/compare-campaigns | So sanh chien dich |
| GET | /analytics/export | Xuat CSV |
| GET | /analytics/fraud-alerts | Canh bao gian lan |
| GET | /analytics/costs | Chi phi AI |

### SOP Engine
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | /sop/templates | Tao template |
| GET | /sop/templates | Danh sach template |
| GET | /sop/templates/{id} | Chi tiet template |
| PATCH | /sop/templates/{id} | Cap nhat template |
| POST | /sop/score-all | Cham diem tat ca |
| POST | /sop/ab-tests | Tao A/B test |
| GET | /sop/ab-tests | Danh sach A/B test |
| POST | /sop/ab-tests/{id}/impression | Ghi impression |
| POST | /sop/ab-tests/{id}/conversion | Ghi conversion |
| POST | /sop/ab-tests/{id}/conclude | Ket thuc test |
| POST | /sop/evolve | Tien hoa template |

### System
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | /system/health | Kiem tra suc khoe |
| GET | /system/stats | Thong ke he thong |
| POST | /system/tasks/score-templates | Chay cham diem |
| POST | /system/tasks/evolve-templates | Chay tien hoa |
| POST | /system/tasks/process-scheduled | Xu ly lich dang |
| POST | /system/tasks/fraud-scan | Quet gian lan |

### Notifications
| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | /notifications | Danh sach thong bao |
| GET | /notifications/unread-count | So chua doc |
| PATCH | /notifications/{id}/read | Danh dau da doc |
| POST | /notifications/read-all | Doc tat ca |

**Tong cong: 49 API endpoints**

Xem day du Swagger docs tai: http://localhost:8000/docs

---

## 7. Xu ly su co

### Backend khong khoi dong
```
ModuleNotFoundError: No module named 'uvicorn'
```
-> Kiem tra da kich hoat venv: `.venv\Scripts\activate`

### Loi ket noi database
```
connection refused: localhost:5432
```
-> Kiem tra Docker dang chay: `docker compose ps`
-> Khoi dong lai: `docker compose up -d`

### Chi phi AI vuot gioi han
```
Daily Claude API cost limit reached
```
-> Tang `CLAUDE_DAILY_COST_LIMIT_USD` trong `.env`
-> Hoac doi sang ngay hom sau (reset luc 00:00 UTC)

### Frontend khong hien thi du lieu
-> Kiem tra backend dang chay tai port 8000
-> Kiem tra CORS: backend cho phep `localhost:3000`
-> Xem Console logs trong trinh duyet (F12)

### Loi ket noi nen tang (Shopee, Lazada, v.v.)
-> Kiem tra API key trong `.env` da dung chua
-> Su dung endpoint `/api/v1/platforms/{id}/test` de kiem tra ket noi
-> Xem log backend de biet chi tiet loi

---

*Phien ban: v0.2.0 | Cap nhat: 2026-04-05*

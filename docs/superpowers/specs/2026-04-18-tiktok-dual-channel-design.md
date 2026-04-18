# TikTok Dual-Channel Affiliate Automation — Design Spec

**Ngày tạo:** 2026-04-18
**Tác giả:** Brainstorm session với Owner
**Trạng thái:** Draft — chờ review

---

## 1. Mục tiêu & Scope

Xây dựng 2 kênh TikTok bán affiliate song song, target net profit **~30M VND/tháng** (EV realistic) sau 6-12 tháng vận hành.

### 1.1 Hai kênh

| | Kênh 1 | Kênh 2 |
|---|--------|--------|
| **Tên tạm** | Faceless Auto | Real Review |
| **Niche** | Mẹ & bé + sức khỏe gia đình (2 sub-niche sẽ chọn sau) |
| **Format** | 100% faceless, AI video từ ảnh SP | Linh hoạt — faceless hoặc lộ mặt tùy video |
| **Monetization** | TikTok Shop Affiliate Native | TikTok Shop Affiliate Native |
| **Volume target** | Phase 2: 2-3 video/ngày (~90/tháng) | Phase 2: 4-5 video/tuần (~20/tháng) |
| **User input** | Approve review queue (30-45 phút/ngày) | Quay + dựng (5-6h/tuần) + approve |
| **AI tự học** | 5 feedback loops (3 đã có, 2 mới) | Cross-channel learning từ Kênh 2 → Kênh 1 |

### 1.2 Platform phân công

- **TikTok (2 kênh trên):** Chỉ dùng **TikTok Shop Native Affiliate** — KHÔNG AccessTrade
- **Facebook + YouTube (tương lai):** Dùng **AccessTrade** cho Shopee/Lazada/Tiki

### 1.3 Ngoài scope

- Phát triển app riêng ngoài TikTok/Facebook/YouTube
- Tự build avatar AI từ đầu (dùng HeyGen/Kling có sẵn)
- Livestream automation (phase 3+, sau 10k followers)
- Multi-account scale (phase 3+)

---

## 2. Phased Rollout

### Phase 0 — Foundation (Tuần 1-3)

**Mục tiêu:** Chuẩn bị hạ tầng trước khi post video đầu tiên.

- Owner: Apply TikTok Shop Developer Custom App + CCCD verification
- Dev: Build TikTok Shop Affiliate API connector
- Dev: Build Tag Queue UI (dashboard batch tag)
- Dev: Thêm Gemini TTS Engine + Kling AI Engine
- Chọn 2 sub-niche cụ thể (vd: "Mẹ bầu tiết kiệm" + "Đồ chơi Montessori")
- Setup content pillars + hook formula library (skill files)

### Phase 1 — Warm Up (Tuần 4-8)

**Mục tiêu:** Train thuật toán TikTok + tune AI content.

- Kênh 1: **1-2 video/ngày** (30-60/tháng)
- Kênh 2: **3 video/tuần** (~12/tháng)
- Không push volume, ưu tiên chất lượng
- Test A/B hook (3 variants per video)
- Batch tag session 2 buổi/tuần

### Phase 2 — Growth (Tháng 2-6)

**Mục tiêu:** Scale volume dựa trên retention/CTR data.

- Kênh 1: **2-3 video/ngày** (push 3 nếu retention > 50%)
- Kênh 2: **4-5 video/tuần**
- Bật Loop 4 (Hook A/B) + Loop 5 (Product Scoring)
- Kill-switch: Tháng 3 review — nếu Kênh 1 avg < 500 views → pause 50% volume

### Phase 3 — Scale (Tháng 7-12)

**Mục tiêu:** Monetize rộng hơn, có thể thuê editor cho Kênh 2.

- Kênh 1: 3 video/ngày steady
- Kênh 2: 5 video/tuần + thử long-form 60-90s
- Livestream bán trực tiếp sau 10k followers
- Mở thêm Facebook/YouTube (dùng AccessTrade)
- Cross-channel learning: Kênh 2 data → retrain Kênh 1 prompts

---

## 3. Architecture

### 3.1 High-Level Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    Product Discovery Layer                      │
├─────────────────────┬──────────────────────────────────────────┤
│  TikTok Shop        │  AccessTrade                              │
│  Affiliate API      │  (Shopee/Lazada/Tiki)                     │
│  → Kênh 1, 2        │  → Facebook, YouTube (future)             │
└─────────────────────┴──────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│              Content Generation Pipeline (existing)             │
│  - Claude: script + hook variants                               │
│  - Gemini Vision: enrich từ ảnh SP                              │
│  - Gemini TTS (Kênh 1) / ElevenLabs Clone (Kênh 2)              │
│  - Kling AI: tạo clip 5-10s từ ảnh (Kênh 1 only)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    Review Queue (existing)                      │
│  - Human approve/edit/reject                                    │
│  - Feeds AITrainingData (Loop 1)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│               Publish & Tag Flow (NEW)                          │
│  - Upload video to TikTok via Content Posting API (draft)       │
│  - Tag Queue UI: user tag SP manually (30s/video)               │
│  - Scheduler posts at optimal time (Loop 2)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│              Analytics Feedback (NEW)                           │
│  - TikTok Shop Order API: track conversion                      │
│  - TikTok Analytics: views, retention, CTR                      │
│  - Feeds Loop 3 (platform perf) + Loop 4 (hook) + Loop 5 (SP)   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Module Boundaries

```
backend/
├── affiliate/                    # Facebook/YouTube + AccessTrade (giữ nguyên)
├── tiktok/                       # Đã có
│   ├── studio.py                 # CRUD projects
│   ├── production.py             # Pipeline tạo video
│   └── router.py
├── tiktok_shop/                  # NEW — tách riêng TikTok Shop affiliate
│   ├── connector.py              # TikTok Shop Affiliate API client
│   ├── product_search.py         # Search high-commission products
│   ├── order_tracking.py         # Pull orders for feedback loop
│   └── tag_queue.py              # Tag Queue state manager
├── ai_engine/
│   ├── claude_engine.py
│   ├── gemini_engine.py          # Vision (đã có)
│   ├── gemini_tts_engine.py      # NEW — TTS primary
│   ├── elevenlabs_engine.py      # Kênh 2 voice clone (giữ)
│   ├── heygen_engine.py          # Kênh 2 hook/CTA avatar (giữ)
│   └── kling_engine.py           # NEW — image-to-video cho Kênh 1
└── learning/                     # NEW — self-learning loops
    ├── hook_ab_test.py           # Loop 4
    └── product_scoring.py        # Loop 5
```

### 3.3 Frontend

```
frontend/src/app/
├── tiktok-studio/                # Đã có
└── tag-queue/                    # NEW — dashboard batch tag
    └── page.tsx
```

---

## 4. Công nghệ & Services

### 4.1 AI Stack

| Mục đích | Service | Kênh | Chi phí/video |
|---------|---------|------|----------------|
| Content script + hook | Claude Sonnet 4.6 | Cả 2 | ~$0.05 |
| Image enrichment | Gemini Vision 2.5 Pro | Cả 2 | ~$0.02 |
| TTS Voice (Kênh 1) | **Gemini 2.5 Pro TTS** | Kênh 1 | ~$0.02 |
| Voice Clone (Kênh 2) | ElevenLabs Professional | Kênh 2 | ~$0.10 |
| Image-to-Video | **Kling AI 2.0** (via fal.ai) | Kênh 1 | ~$1.00 (3 clip) |
| Avatar hook/CTA | HeyGen | Kênh 2 (optional) | ~$0.30 |

**Tổng chi phí ước tính:**
- Kênh 1: ~$1.10/video × 90 = **~$100/tháng**
- Kênh 2: ~$0.50/video × 20 = **~$10-30/tháng** (+ ElevenLabs plan $22)

**Total ~$130-150/tháng ~ 3.3-3.8M VND**

### 4.2 Platform APIs

| API | Mục đích | Onboarding | Cost |
|-----|----------|-------------|------|
| TikTok Shop Affiliate Creator | Search SP, track orders, commission | 2-3 tuần (Custom App) | Free |
| TikTok Content Posting | Upload video draft | Đã có | Free |
| TikTok OAuth | Auth user | Đã có | Free |
| AccessTrade (giữ) | FB/YouTube future | Đã có | Free |

---

## 5. Feedback Loops (AI Self-Learning)

### 5.1 Hiện có (đã hoạt động)

1. **Loop 1 — Content Quality (AITrainingData)**
   User approve/edit → Few-Shot Learning inject vào prompt tiếp theo.

2. **Loop 2 — Optimal Post Time (Adaptive Scheduler)**
   EMA + epsilon-greedy học giờ vàng riêng cho mỗi kênh.

3. **Loop 3 — Platform Performance (Webhooks)**
   Cần mở rộng: Facebook đã có, thêm TikTok Analytics polling.

### 5.2 Mới (cần build)

4. **Loop 4 — Hook Performance A/B Test**
   - Claude gen 3 hook variants/video
   - Random chọn 1 để post
   - Sau 48h: pull retention@3s từ TikTok Analytics
   - Score variant theo retention
   - Sau 20 samples: bias generation sang pattern thắng

5. **Loop 5 — Product Success Scoring**
   - Lưu actual CTR + conversion per product
   - Reinforce product patterns (price, brand, sub-niche)
   - Blacklist SP có return > 25%

### 5.3 Bonus — Cross-Channel Learning (Phase 3)

- Claude analyze Kênh 2 scripts chuyển đổi tốt
- Extract pattern → inject vào BASE_SYSTEM của Kênh 1
- Rút ngắn learning curve Kênh 1 khoảng 2-3 tháng

---

## 6. Data Models (mới)

### 6.1 HookVariant

```python
@dataclass
class HookVariant:
    id: UUID
    content_piece_id: UUID
    hook_text: str
    pattern_type: str  # "question" | "pain_point" | "social_proof" | "shock"
    retention_at_3s: float | None  # set sau 48h
    score: float  # running average
```

### 6.2 ProductScore

```python
@dataclass
class ProductScore:
    product_id: str  # TikTok Shop product ID
    actual_ctr: float
    actual_conversion: float
    return_rate: float
    total_orders: int
    status: Literal["active", "blacklisted"]
    last_updated: datetime
```

### 6.3 TagQueueItem

```python
@dataclass
class TagQueueItem:
    video_id: UUID
    tiktok_draft_url: str
    product_id: str
    product_name: str
    commission_rate: float
    tagged_at: datetime | None
    published_at: datetime | None
```

---

## 7. Content Strategy

### 7.1 Content Pillars (Kênh 1)

4 pillars rotation:

1. **Review sản phẩm đơn lẻ** (40%) — 1 SP, so sánh với market
2. **Top 5 list** (30%) — "5 món đồ mẹ bầu không thể thiếu"
3. **Dupe so sánh** (20%) — "SP xịn 500k vs dupe 100k — có đáng?"
4. **Haul / Unboxing** (10%) — AI-generated unboxing clip

### 7.2 Hook Formulas (10 templates)

Lưu trong `docs/skills/script_formula_library.md`:

1. Pain point: "Chị em nào đang đau đầu vì [X]..."
2. Shocking stat: "90% mẹ bầu không biết..."
3. Question: "Bạn có biết SP này ẩn chứa..."
4. Social proof: "100,000 mẹ đã dùng và..."
5. Curiosity: "Thử SP này 7 ngày và đây là kết quả..."
6. Negative: "Đừng mua [X] nếu bạn chưa biết..."
7. Comparison: "500k vs 100k — SP nào xịn hơn..."
8. Scarcity: "Cháy hàng trên Shopee nhưng TikTok Shop còn..."
9. Myth busting: "Ai bảo [X] tốt cho bé? Sai rồi..."
10. Tutorial: "Mẹo dùng [X] mà 95% bà mẹ làm sai..."

### 7.3 Kênh 2 SOP

Lưu trong `docs/skills/kenh2_review_sop.md`:

1. User list đồ dùng gia đình (Google Sheet hoặc form UI)
2. AI analyze + tìm SP matching trên TikTok Shop
3. AI gen script + thoại + CTA + B-roll suggestion
4. User quay (batch 5 video/buổi, 2h)
5. User dựng CapCut
6. Upload via Tag Queue
7. Tag SP manually → publish

---

## 8. SOPs (Daily/Weekly/Monthly)

### 8.1 `docs/skills/daily_operator_sop.md`

**Sáng (15 phút):**
- Check Telegram alert qua đêm (error, viral hit)
- Review queue (approve 5-10 video AI gen)

**Tối (20-30 phút):**
- Batch tag 10-15 video lên TikTok
- Check retention@3s của video 24h trước
- Quick note hook nào thắng

### 8.2 `docs/skills/weekly_review_sop.md`

**Chủ nhật (1h):**
- Review doanh thu tuần (DB query)
- Top 3 video viral + pattern
- Bottom 3 flop + lesson
- A/B winner hook của tuần
- Plan 5 video Kênh 2 tuần tới

### 8.3 `docs/skills/monthly_pivot_sop.md`

**Cuối tháng (2h):**
- Check kill switch criteria
- P&L per kênh
- Product return rate → blacklist
- Adjust phase nếu cần (volume ↑ hay ↓)

---

## 9. Testing Strategy

### 9.1 Unit Tests
- Mỗi connector/engine mới: >= 10 test
- AI Engines: mock API response, test fallback

### 9.2 Integration Tests
- End-to-end pipeline: SP → content → video → draft upload
- Feedback loop: simulate approve → few-shot inject

### 9.3 Manual Testing
- Tag Queue UI: test flow 1 video thật trên TikTok Creator
- Gemini TTS output: A/B blind test giọng với ElevenLabs (10 samples)

### 9.4 Coverage
- Target 80% unit coverage, 60% integration coverage

---

## 10. Risk Management (tóm tắt)

| # | Rủi ro | Mitigation chính |
|---|--------|-----------------|
| 1 | TikTok ban AI faceless | Kết hợp 1 yếu tố real + backup account |
| 2 | Cash flow âm 3-6 tháng | Budget cap 4M/tháng đầu + buffer 25M |
| 3 | Return rate > 25% | Product vetting + honest script + Loop 5 blacklist |
| 4 | AI cost tăng | Multi-provider + daily cap |
| 5 | Nghị định VN siết | Disclosure #ad + track policy update |
| 6 | Niche bão hòa | Sub-niche focus + angle khác biệt |
| 7 | Burnout | Batch recording + outsource editor khi revenue > 15M |
| 8 | Bug pipeline | Review queue + idempotency + Telegram alert |

**Kill Switch:**
- Tháng 3: Kênh 1 < 500 views avg → pause 50%
- Tháng 6: Tổng revenue < 5M → pivot hoặc dừng Kênh 1
- Return > 30% → pause 2 tuần, vet lại SP
- TikTok cảnh báo 2 lần → chuyển Reels/Shorts

---

## 11. Success Criteria (Definition of Done cho MVP)

**Hoàn thành Phase 0 khi:**
- [ ] TikTok Shop Developer Custom App approved + API credentials
- [ ] 2 sub-niche được chốt
- [ ] Gemini TTS Engine hoạt động (10 mẫu test pass blind test 70%+)
- [ ] Kling AI Engine: generate 1 clip 10s từ ảnh SP thành công
- [ ] Tag Queue UI: upload 1 video thật lên TikTok draft + tag SP + publish
- [ ] Loop 4 (Hook A/B) schema + ingestion
- [ ] Loop 5 (Product Score) schema + ingestion
- [ ] Content pillars + 10 hook templates saved in docs/skills/
- [ ] SOP daily/weekly/monthly saved in docs/skills/

**Hoàn thành Phase 1 (warm up) khi:**
- [ ] 30 video Kênh 1 + 12 video Kênh 2 đã post
- [ ] Hook A/B đã có 20+ samples, bias generation hoạt động
- [ ] Ít nhất 5 đơn thật (không cần lãi)

---

## 12. Budget & Timeline

### Budget

| Item | Chi phí | Tần suất |
|------|---------|----------|
| AI stack | ~3.5M/tháng | Ongoing |
| Buffer cash flow | 25M | One-time |
| Dev time (coding) | ~40h = free (tự làm) | Phase 0 |
| Editor Kênh 2 | 0 → 1M/tháng | Khi revenue > 15M |

### Timeline

- **Tuần 1-3:** Phase 0 — Foundation
- **Tuần 4-8:** Phase 1 — Warm Up
- **Tháng 2-6:** Phase 2 — Growth (break-even tháng 4-5)
- **Tháng 7-12:** Phase 3 — Scale

### Expected Value năm 1

- Revenue: ~400-500M VND
- Cost: ~45M VND (AI) + ~10M (testing/fail)
- **Net profit: ~330-420M VND (~30M/tháng sau 6 tháng)**

---

## 13. Open Questions (cần decide trước implement)

- [ ] **Sub-niche cụ thể Kênh 1?** (gợi ý: "Mẹ bầu tiết kiệm" + "Đồ chơi Montessori")
- [ ] **Voice preset Kênh 1?** — Giọng nữ trẻ, vùng miền (Bắc/Nam/trung tính)
- [ ] **Kênh 2 — user upload list đồ qua UI form hay Google Sheet?**
- [ ] **Thời gian user muốn tag batch** — thứ 7+CN hay hàng ngày?
- [ ] **Backup account ngay từ đầu?** Hay chỉ chuẩn bị credentials để mở khi cần?

---

## 14. References

- [AccessTrade TikTok Affiliate Partner](https://accesstrade.vn/accesstrade-chinh-thuc-tro-thanh-doi-tac-chien-luoc-cua-tiktok-shop-tiktok-affiliate-partner-tap/)
- [TikTok Shop Affiliate Creator API](https://partner.tiktokshop.com/docv2/page/affiliate-creator-api-overview)
- [TikTok Content Posting API](https://developers.tiktok.com/products/content-posting-api/)
- [Eligibility Vietnam](https://seller-vn.tiktok.com/university/essay?knowledge_id=104015979497218)

Session files: `.superpowers/brainstorm/510-1776443996/content/`

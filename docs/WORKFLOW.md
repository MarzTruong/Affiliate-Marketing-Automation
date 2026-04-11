# Workflow Reference

> Extracted from CLAUDE.md. For survival rules, see [`../CLAUDE.md`](../CLAUDE.md). For architecture, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## AI Content Generation Pipeline

```
1. Few-Shot Load      → Read AITrainingData (approved content), prefer same category
2. Gemini Enrich      → If image_urls exist → Gemini analyzes images, enriches description
3. CoT Template       → Render Jinja2 with cot_header (3-step thinking) + few_shot_prefix
4. Claude Generate    → Model routing: Haiku (social/description), Sonnet (SEO/video)
5. Strip Thinking     → Remove <thinking>...</thinking> from output before saving
```

### Model Details

| Engine | Model | Use Case |
|--------|-------|----------|
| Claude Haiku | Social posts, product descriptions | Fast, cheap |
| Claude Sonnet | SEO articles, video scripts | Higher quality |
| Gemini 2.5 Pro | Image analysis (vision) | Multimodal |
| Gemini 2.5 Flash | Text enrichment | Fast, cheap |

### Gemini SDK

- Use `google-genai` v1.70.0+ — **NOT** `google-generativeai` (deprecated)
- Init: `create_gemini_engine()` → `await engine.initialize()` in app lifespan
- Exceptions: `GeminiRateLimitError` (429), `GeminiAuthError` (401/403), `GeminiTimeoutError` (503)

### Human-in-the-Loop

- Approve → save `AITrainingData` with `quality_signal="approved"`
- Edit then approve → `quality_signal="edited_then_approved"` + update `ContentPiece.body`
- Next generation auto-injects approved content as few-shot examples

---

## Review Queue API

```
GET  /api/v1/automation/review-queue
POST /api/v1/automation/review/{id}/approve    # optional edited_body
POST /api/v1/automation/review/{id}/reject
POST /api/v1/automation/review/bulk-approve    # {"post_ids": [...]}
POST /api/v1/automation/review/bulk-reject     # {"post_ids": [...], "reason": "..."}
```

---

## Connectors & Rate Limiting

**AccessTrade** (PRIMARY and ONLY product source):
- Rate limit: 0.5s delay between requests (class-level `RateLimiter`)
- Retry: Tenacity 3x, exponential backoff 2s→4s→8s, only on `RateLimitError` or `ConnectorNetworkError`
- `AuthError` (401/403): no retry — fail fast

**Shopee:** Delegates all search + link generation to AccessTrade (no scraping)

**product_scanner.py** mock fallback triggers:
- `no_api_key` — API key not configured
- `auth_failed` — authentication failure
- `empty_result` — API returned empty
- Always logs the reason

---

## Automation Pipeline Flow

```
Product Scan (AccessTrade)
    → Filter (rules matching)
        → AI Content Generation (see pipeline above)
            → Visual Generation (Bannerbear API + Pillow fallback)
                → ScheduledPost (status: pending_review)
                    → Owner approves/rejects via Review Queue
                        → Publisher dispatches to Facebook/WordPress/Telegram/TikTok
```

**Critical:** Pipeline NEVER auto-publishes. Every post goes through `pending_review`.

---

## Adaptive Scheduling

`adaptive_scheduler.py` uses EMA (Exponential Moving Average) + epsilon-greedy algorithm to learn optimal posting times per channel based on engagement data.

---

## Background Workers

`workers/` — Async task processing via arq + Redis for:
- Scheduled post publishing
- Analytics aggregation
- Report generation
- Platform sync operations

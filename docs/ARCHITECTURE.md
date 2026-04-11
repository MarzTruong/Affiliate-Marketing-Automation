# Architecture Reference

> Extracted from CLAUDE.md. For survival rules and workflow, see [`../CLAUDE.md`](../CLAUDE.md).

## Project Stack

| Layer | Stack |
|-------|-------|
| Backend | FastAPI + PostgreSQL + Redis + Claude AI + Google Gemini |
| Frontend | Next.js 16 (React 19) + TanStack Query + Recharts + Tailwind CSS v4 |
| Infra | Docker Compose (PostgreSQL + Redis), Alembic migrations |
| AI Engine | Claude (content gen) + Gemini 2.5 Pro (vision) |
| Connectors | AccessTrade (primary), Shopee, ShopBack, TikTok Shop |
| Publishers | Facebook, WordPress, Telegram, TikTok |

---

## Backend (`backend/`)

```
main.py              # FastAPI app + lifespan
                     #   1. create_all() guard (dev only)
                     #   2. apply_db_settings() — load creds from DB
                     #   3. Gemini engine init (app.state.gemini)
                     #   4. APScheduler start
config.py            # pydantic-settings: DATABASE_URL, ANTHROPIC_API_KEY, GEMINI_API_KEY
database.py          # Async SQLAlchemy engine, get_db()

models/              # SQLAlchemy ORM
  system_settings.py # Key-value platform credentials store
  ai_training_data.py# Approved content → few-shot examples
  automation.py      # AutomationRule, ScheduledPost
  product.py         # Product catalog
  content.py         # ContentPiece
  campaign.py        # Campaign tracking
  analytics.py       # Click/revenue events
  publication.py     # Published post records
  notification.py    # System notifications
  fraud_event.py     # Fraud detection
  sop_template.py    # SOP templates
  platform_account.py# Connected platform accounts

schemas/             # Pydantic request/response

api/v1/
  settings.py        # Credentials CRUD via system_settings table
  automation.py      # Rules, pipeline runs, review queue

ai_engine/
  client.py          # ClaudeClient — model routing, cost tracking
  content_generator.py # Orchestrator: few-shot → Gemini → CoT → Claude → strip thinking
  gemini_engine.py   # google-genai SDK, vision gemini-2.5-pro
  cost_tracker.py    # Daily cost limit enforcement
  prompts/
    system.py        # System prompt builder
    templates.py     # Jinja2 CoT + few-shot injection

connectors/
  accesstrade.py     # PRIMARY source — RateLimiter 0.5s + Tenacity 3x retry
  shopee.py          # Delegates to AccessTrade (no scraping)
  shopback.py        # ShopBack Partner API
  tiktok_shop.py     # TikTok Shop Affiliate API
  base.py            # Base connector interface

automation/
  scheduler.py       # APScheduler cron triggers
  pipeline.py        # scan → filter → AI content → visual → pending_review
  product_scanner.py # AccessTrade scanner; mock fallback with logged reason
  adaptive_scheduler.py # EMA + epsilon-greedy posting time optimization
  visual_generator.py   # Bannerbear API + Pillow fallback
  cbd_agent.py       # AI chat agent (Claude) for Vietnamese NL control

publisher/
  facebook.py        # Facebook Graph API
  wordpress.py       # WordPress REST API
  telegram.py        # Telegram Bot API
  tiktok.py          # TikTok posting
  posting_service.py # Unified posting service
  scheduler.py       # Publishing scheduler
  base.py            # Base publisher interface

analytics/           # Click/revenue tracking
reports/             # Report generation
sop_engine/          # SOP templates
workers/             # Async background tasks (arq + Redis)

tests/
  conftest.py        # Shared fixtures
  test_api.py        # API endpoint tests
  test_connectors.py # Connector tests
  test_models.py     # Model tests
  test_publisher.py  # Publisher tests
  test_sop_engine.py # SOP engine tests
  test_fraud_detector.py # Fraud detection tests
```

---

## Frontend (`frontend/src/app/`)

Next.js App Router. Each subdirectory = route:

| Route | Purpose |
|-------|---------|
| `automation/` | Automation Rules + Review Queue (approve/reject/bulk) |
| `calendar/` | Content Calendar (weekly, by channel) |
| `chat/` | AI Chat — Vietnamese natural language control |
| `content/` | Manual content management |
| `campaigns/` | Campaign tracking |
| `analytics/` | Performance analytics |
| `settings/` | Credentials config (reads/writes `system_settings`) |
| `publisher/` | Publishing channel management |
| `notifications/` | System notifications |
| `sop/` | Standard Operating Procedures |

---

## Key Constraints

- **Pipeline does NOT auto-publish.** Creates `ScheduledPost` with `pending_review` → owner must approve via Review Queue
- **AccessTrade is the ONLY product source** — Shopee delegates to AccessTrade, no scraping
- **One server per port** — never run parallel backend or frontend instances
- **`.venv/` at project root**, not inside `backend/`

---

## Credentials & Environment

| Variable | Source | Notes |
|----------|--------|-------|
| `DATABASE_URL` | `.env` | PostgreSQL connection |
| `ANTHROPIC_API_KEY` | `.env` | Claude API |
| `GEMINI_API_KEY` | `.env` | Google Gemini API |
| Platform credentials | `system_settings` table | Via `/settings` UI or `POST /api/v1/settings/credentials`. API rejects (400) `.env` writes. |

---

## Logs

| File | Content |
|------|---------|
| `backend.log` | Application logs (info, warning) |
| `backend_err.log` | Error logs (exceptions, crashes) |
| `frontend.log` | Frontend build/runtime logs |

All at project root.

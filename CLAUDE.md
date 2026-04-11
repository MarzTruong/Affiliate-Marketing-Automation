# CLAUDE.md — Project Constitution

> **Mandatory for ALL AI agents.** No exceptions. Violating any rule = critical failure.

> **Communication:** This file is English (token efficiency). Claude MUST ALWAYS speak to the owner in **Vietnamese** (simple, Non-Dev friendly).

> **Modular docs:** Architecture → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Workflow & commands → [`docs/WORKFLOW.md`](docs/WORKFLOW.md)

---

## 1. Survival Rules

### Fail Loud — No Silent Errors

- **BANNED:** `except: pass`, `except: return None`, any silent swallow
- **REQUIRED:** Every `except` → `logger.error(...)` + `raise` (or HTTP 4xx/5xx)
- **REQUIRED:** Exception chaining (`from e`) on re-raise
- Never return HTTP 200 on failure. Never return mock data to hide errors.

### Data Protection

- `DROP TABLE` / `TRUNCATE` / `DELETE (no WHERE)` → **BANNED** unless owner types: `TÔI XÁC NHẬN XÓA`
- Editing applied migrations → **BANNED** (create new one)
- **NEVER** commit real API keys to source. **NEVER** log secrets to terminal.
- `.env` = only `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- All platform creds → `system_settings` DB table (UI `/settings` or API)

### API Cost Guard

- **429** → stop pipeline, no continuous retry
- **402/403** → halt AI pipeline, display: `CẢNH BÁO: HẾT QUOTA API — [Service] — [Error]`
- Never bypass `cost_tracker.py` daily limits. Non-AI features must keep running.

### Transparent Reporting

- After every task → report in Vietnamese: files changed, feature description, test command + result
- Breaking changes → `**CẢNH BÁO:**` prefix

---

## 2. TDD Mandatory

- **RED** (failing test) → **GREEN** (minimal code) → **REFACTOR**
- Coverage: 80%+ new code. Structure: AAA (Arrange/Act/Assert)
- Must run tests + paste results before reporting task complete

---

## 3. Vibe Coding Workflow

### 3.1 Plan Mode — Think Before Code

- Every new request → output **Plan** → **WAIT** for owner ("OK" / "Làm đi")
- Plan includes: Goal · Files to change · Approach · Risks · Test plan · Complexity (S/M/L)
- Exception: production crash hotfix (fix first, plan after, report immediately)

### 3.2 Agentic Loop (Max 3 Retries)

- Error → analyze → fix → retry. **Max 3 attempts.**
- After 3 failures → **STOP** → report in Vietnamese (what failed, what was tried, suspected cause)
- **BANNED:** Returning mock/default data in `except` to fake success. Returning 200 with fake payload.

### 3.3 Auto Memory

- **MAY auto-update:** Dev commands (§4 below), `TODO.md`, `memory/` files
- **MUST NOT auto-update:** Survival rules (§1-3), architecture docs, `.env`, `docker-compose.yml`

### 3.4 Skill Files (Meta Prompting)

- MAY generate `.md` skills in `docs/skills/` for recurring tasks
- Format: name, trigger, version, steps, checklist (Vietnamese)
- Notify owner after creation. No duplicates.

### 3.5 Git Isolation

- Hotfix (1-2 files) → `hotfix/name` branch
- Feature (3-5 files) → `feature/name` branch
- Large feature (6+ files) → git worktree + `feature/name`
- **BANNED:** Direct commits to `main` for features. `git push --force` to `main` — never.

### 3.6 MCP Git Connection

- **Repo:** `https://github.com/MarzTruong/Affiliate-Marketing-Automation.git`
- Commits: English, conventional (`feat:`, `fix:`, `refactor:`)
- Push: only on owner request or Save Game
- `git reset --hard` on `main` → BANNED unless `TÔI XÁC NHẬN RESET`
- Destructive ops → list consequences, wait for confirmation

### 3.7 Session Management

**"Bắt đầu" (Start Game):** Read TODO.md + CLAUDE.md + memory/ → git status + git log -5 → health checks → Vietnamese status report → "Sẵn sàng nhận lệnh."

**"Nghỉ thôi" (Save Game):** Update TODO.md + memory/ → run linter + tests → git add + commit + push → Vietnamese closing report (done/remaining/notes).

---

## 4. Development Commands

> Auto Memory zone — Claude may update this section when better commands are discovered.

```bash
# Infra
docker-compose up -d postgres redis

# Backend (project root, one instance only)
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (/frontend, one instance only)
cd frontend && npm run dev

# Test
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pytest --cov=backend

# Lint & Format
.venv\Scripts\python.exe -m ruff check backend/
.venv\Scripts\python.exe -m ruff format backend/
cd frontend && npm run lint
cd frontend && npm run build

# Alembic
.venv\Scripts\alembic.exe revision --autogenerate -m "description"
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\alembic.exe downgrade -1
```

| Health Check | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend Docs | http://localhost:8000/docs |
| Backend Health | http://localhost:8000/health |

---

## 5. Context Limits

- **At 25 messages:** warn owner → `CẢNH BÁO: Phiên dài 25+ tin. Chạy /clear hoặc phiên mới.`
- Before warning → auto-save (TODO.md + memory/)
- **At 40 messages:** run Save Game (§3.7), insist on new session

---

## Quick Reference

| Rule | Keyword |
|------|---------|
| Plan before code | **Think first** |
| Max 3 retries, no fake success | **Fail real** |
| Auto-update commands/memory | **Long-term memory** |
| Generate skill files | **Automate process** |
| New feature = new branch | **Isolate safely** |
| Git via MCP for Non-Dev | **Git proxy** |
| "Bắt đầu" = load, "Nghỉ thôi" = save | **Session control** |
| Warn 25 msgs, insist 40 | **Context guard** |

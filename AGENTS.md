# Agent Configuration

## Agent skills

### Issue tracker

Local markdown files under `.scratch/` directories. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout with one `CONTEXT.md` at repo root. See `docs/agents/domain.md`.

## Project overview

Language-learning web app: grammar-rule content generation via LangGraph agents, with a Supabase-backed FastAPI server and HTMX admin panel.

## Stack

- **Python 3.13**, managed with **uv** (see `.python-version`)
- **FastAPI** + **uvicorn** — `serve.py` is the real entrypoint (not `main.py`, which is a stub)
- **SQLAlchemy** ORM (not SQLModel) — models in `models/`, CRUD in `crud/`, DB session from `database.py`
- **Alembic** — app-level migrations (`alembic/`)
- **Supabase** (local) — infrastructure migrations (`supabase/migrations/`), auth, Postgres on port 54322
- **LangGraph** + **LangChain** via **OpenRouter** (GPT-4o-mini) — agent graphs in `graphs/`
- **Jinja2** + **HTMX** — server-rendered admin panel, templates in `templates/`
- **LangSmith** tracing enabled for all graph runs

## Dev commands

```sh
# Full stack (Supabase + uvicorn)
./scripts/start.sh
./scripts/stop.sh

# Migrations (starts Supabase if needed, runs Alembic, assigns admin role)
./scripts/migrate.sh

# Just the backend (no Supabase)
uv run uvicorn serve:app --reload    # port 8080

# LangGraph dev server
uv run langgraph dev

# Alembic
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# Add a dependency
uv add package_name
```

No lint, typecheck, or test commands are configured in this repo.

## Two migration systems

Keep them separate:
- **Supabase migrations** (`supabase/migrations/`) — infrastructure: extensions (pgvector), roles, RLS policies
- **Alembic migrations** (`alembic/versions/`) — application schema: tables, columns, indexes

When adding a new table, create an Alembic migration. When adding RLS or Postgres extensions, create a Supabase migration.

## Architecture

```
serve.py              ← FastAPI app, uvicorn entrypoint
routers/              ← FastAPI routers (auth, admin, CRUD)
  auth.py             ← Supabase JWT auth, require_admin dependency
models/               ← SQLAlchemy models (one file per table)
crud/                 ← Database access functions
core/                 ← Shared utils (Jinja2 template config, HTMX render helper)
graphs/               ← LangGraph agents
  nodes/              ← Graph node functions
  prompts.py          ← LangChain prompt templates
  models.py           ← Pydantic models for graph I/O
  states.py           ← TypedDict state definitions
  llm.py              ← OpenRouter ChatOpenAI client
  suggest_rules_graph.py   ← Proposes 5 grammar rules
  initial_rule_graph.py    ← Categorizes, persists, translates, generates content
templates/            ← Jinja2 HTML templates (HTMX admin panel)
static/               ← CSS, FontAwesome icons
supabase/             ← Supabase config + SQL migrations
alembic/              ← Alembic migration scripts
scripts/              ← Shell scripts for dev workflow
```

## Auth model

- Supabase Auth issues JWTs; verified locally via JWKS at `http://127.0.0.1:54321/auth/v1/.well-known/jwks.json`
- `get_current_user()` in `routers/auth.py` validates JWT from cookie (`access_token`) or `Authorization` header
- `require_admin()` checks `app_metadata.role == "admin"` — set via `scripts/migrate.sh`
- 401/403 exceptions outside `/auth` paths redirect to `/login` (see `serve.py` exception handler)

## Key conventions

- DB URL comes from `.env` `DATABASE_URL_LOCAL` (Postgres on port 54322) — `database.py` reads it at import time
- Models use `database.Base` (declarative_base), not SQLModel
- UUIDs are primary keys everywhere, generated with `uuid.uuid4()`
- Templates use a Jinja2 filter `flag` (from `country_flags.py`) for country flag emojis
- HTMX: `core/render.py` renders full pages for direct navigation, fragment templates for HTMX requests (`HX-Request` header)
- `useful_commands.py` is gitignored — contains scratch notes and secrets, do not commit
- `.env` is gitignored — required for runtime, contains API keys and local Supabase credentials

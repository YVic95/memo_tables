# Code Standards — memo_tables

Language-learning web app: grammar-rule content generation via LangGraph agents, with a Supabase-backed FastAPI server and HTMX admin panel.

---

## 1. Project Structure

```
memo_tables/
├── serve.py                     # FastAPI entrypoint (NOT main.py)
├── database.py                  # SQLAlchemy engine, session, Base
├── country_flags.py             # Language code → emoji flag mapping
├── alembic.ini                  # Alembic config
├── langgraph.json               # LangGraph server config
├── .python-version              # Python 3.13
│
├── models/                      # SQLAlchemy ORM models (one file per table)
│   ├── __init__.py              #   MUST exist — Alembic imports from here
│   ├── language.py
│   ├── grammar_rules.py
│   ├── grammar_rule_translations.py
│   ├── grammar_rule_rows.py
│   ├── grammar_rule_row_translations.py
│   ├── word_categories.py
│   ├── base_words.py
│   ├── base_word_topics.py
│   ├── word_forms.py
│   ├── word_form_translations.py
│   ├── word_form_sentences.py
│   ├── word_translations.py
│   ├── word_rule_assignments.py
│   ├── topics.py
│   ├── topic_translations.py
│   ├── expressions.py
│   ├── expression_translations.py
│   ├── expression_topics.py
│   ├── sentences.py
│   ├── sentence_translations.py
│   ├── entity_embeddings.py
│   ├── language_pairs.py
│   └── chat_sessions.py
│
├── crud/                        # Database access functions (one file per domain)
│   ├── __init__.py
│   ├── languages.py
│   ├── language_pairs.py
│   ├── rules.py
│   └── chat_sessions.py
│
├── graphs/                      # LangGraph agent definitions
│   ├── llm.py                   #   OpenRouter ChatOpenAI client
│   ├── states.py                #   TypedDict state definitions
│   ├── models.py                #   Pydantic models for graph I/O
│   ├── prompts.py               #   LangChain PromptTemplate definitions
│   ├── suggest_rules_graph.py   #   Proposes 5 grammar rules
│   ├── initial_rule_graph.py    #   Categorizes, persists, translates, generates content
│   ├── generate_table_graph.py  #   Generates grammar/conjugation tables
│   ├── edit_tables_graph.py     #   Edits tables with conversation memory
│   └── nodes/                   #   Graph node functions (one file per node)
│       ├── propose_rules_node.py
│       ├── attach_grammatical_category_to_rule_node.py
│       ├── persist_rule.py
│       ├── translate_rule.py
│       ├── persist_translation.py
│       ├── generate_rule_content.py
│       ├── fetch_rule_category_node.py
│       ├── generate_category_table_node.py
│       ├── generate_general_table_node.py
│       ├── generate_fragmented_tables_node.py
│       └── edit_tables.py
│
├── routers/                     # FastAPI routers (one file per feature)
│   ├── auth.py                  #   Supabase JWT auth, get_current_user(), require_admin()
│   ├── user_login.py            #   GET /login
│   ├── admin_dashboard.py       #   GET /admin-panel
│   ├── languages.py             #   Language CRUD endpoints
│   ├── language_pairs.py        #   Language pair endpoints
│   ├── grammar_rules.py         #   Rules list endpoint
│   ├── create_rule_agent.py     #   POST /api/create-rule-agent (SSE streaming)
│   ├── save_rule.py             #   POST /api/grammar-rules/{id}/append-content
│   ├── generate_table_agent.py  #   POST /api/generate-table
│   ├── edit_tables_agent.py     #   POST /api/edit-tables
│   ├── chat_sessions.py         #   POST /api/chat-sessions
│   ├── save_tables_agent.py     #   POST /api/save-tables
│   └── legal_pages.py           #   GET /privacy, GET /terms
│
├── core/                        # Shared utilities
│   ├── __init__.py
│   ├── templates.py             #   Jinja2Templates setup + |flag filter
│   ├── render.py                #   HTMX-aware render_section()
│   ├── menu.py                  #   Sidebar menu sections config
│   └── checkpointer.py          #   PostgresSaver for LangGraph
│
├── templates/                   # Jinja2 HTML templates
│   ├── admin-panel.html         #   Base layout (sidebar + header + content)
│   ├── admin-panel-languages.html
│   ├── admin-panel-rules.html
│   ├── login.html
│   ├── menu-sections/           #   Content fragments per sidebar section
│   └── partials/                #   Reusable HTMX swap fragments
│
├── static/                      # Frontend assets
│   ├── css/                     #   admin-panel.css, login.css, typography.css, FontAwesome
│   ├── js/                      #   htmx.min.js + app-specific JS files
│   ├── fonts/                   #   ElmsSans, Cantarell
│   └── images/                  #   bg.jpeg
│
├── alembic/                     # Alembic migrations (app schema)
│   ├── env.py                   #   Imports all models, sets target_metadata
│   └── versions/                #   One migration per table change
│
├── supabase/                    # Supabase config + infrastructure migrations
│   ├── config.toml
│   └── migrations/              #   SQL: extensions, RLS, roles
│
├── scripts/                     # Dev workflow shell scripts
│   ├── start.sh
│   ├── stop.sh
│   ├── migrate.sh
│   └── create_admin_user.py
│
└── docs/                        # Documentation
    ├── agents/
    │   ├── domain.md
    │   ├── issue-tracker.md
    │   └── triage-labels.md
    ├── privacy_policy.md
    └── terms_of_service.md
```

---

## 2. Language & Runtime

- **Python 3.13** managed with **uv** (see `.python-version`)
- No lint, typecheck, or test commands are configured
- Run the backend: `uv run uvicorn serve:app --reload` (port 8080)
- Run the full stack: `./scripts/start.sh`

---

## 3. Database Models (SQLAlchemy)

**Location:** `models/` — one file per table, snake_case filename.

**Convention:** `database.Base = declarative_base()` — NOT SQLModel.

### Rules

- Every model inherits from `database.Base`
- Every table has a UUID primary key: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
- Foreign keys use string references: `ForeignKey("table_name.column_name")`
- **No ORM relationships defined** — all joins are done manually in CRUD functions
- `__tablename__` must be snake_case plural (e.g., `grammar_rules`)
- `models/__init__.py` must exist (Alembic requires it to discover models)
- When creating a new model, **add its import to `alembic/env.py`**

### Example: `models/grammar_rules.py`

```python
import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class GrammarRule(Base):
    __tablename__ = "grammar_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(UUID(as_uuid=True), ForeignKey("word_categories.id"), nullable=False)
```

### Example with cascade delete: `models/grammar_rule_translations.py`

```python
grammar_rule_id = Column(
    UUID(as_uuid=True),
    ForeignKey("grammar_rules.id", ondelete="CASCADE"),
    nullable=False,
)
```

### Composite primary key example: `models/expression_topics.py`

```python
from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint
from database import Base

class ExpressionTopic(Base):
    __tablename__ = "expression_topics"

    expression_id = Column(UUID(as_uuid=True), ForeignKey("expressions.id"), primary_key=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), primary_key=True)

    __table_args__ = (
        PrimaryKeyConstraint("expression_id", "topic_id"),
    )
```

---

## 4. CRUD Layer

**Location:** `crud/` — one file per domain area.

### Rules

- Every function takes `db: Session` as its first parameter
- Use `db.query(Model).filter().first()` for lookups
- Use `db.add()` + `db.commit()` + `db.refresh()` for writes
- Return model instances or dicts — no Pydantic in CRUD
- No ORM relationships; joins done manually

### Example: `crud/rules.py`

```python
from uuid import uuid4
from sqlalchemy.orm import Session
from models.grammar_rules import GrammarRule

def create_grammar_rule(
    db: Session,
    title: str,
    description: str,
    language_id: str,
    word_category_id: str,
) -> GrammarRule:
    rule = GrammarRule(
        id=str(uuid4()),
        name=title,
        description=description,
        language_id=language_id,
        word_category_id=word_category_id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def get_grammar_rule_by_id(db: Session, rule_id: str) -> GrammarRule | None:
    return db.query(GrammarRule).filter(GrammarRule.id == rule_id).first()
```

---

## 5. Pydantic Models (Graph I/O)

**Location:** `graphs/models.py`

### Rules

- All Pydantic models for graph I/O live in this single file
- Used as structured output schemas for LLM calls (`llm.with_structured_output(Model)`)
- Also used as request/response models for API endpoints in routers
- Use `Field(description=...)` for every field — LLMs use these descriptions

### Example: `graphs/models.py`

```python
from pydantic import BaseModel, Field

class Rule(BaseModel):
    title: str = Field(description="Short name of the grammar/language rule")
    explanation: str = Field(description="Clear explanation of the rule")

class ProposedRules(BaseModel):
    rules: list[Rule] = Field(description="Exactly 5 proposed rules")

class TableData(BaseModel):
    title: str = Field(description="Heading for this table")
    headers: list[str] = Field(description="Column headers")
    rows: list[TableRow] = Field(description="Table rows")
```

---

## 6. LangGraph Agents

**Location:** `graphs/` with subdirectories:

| File | Purpose |
|------|---------|
| `llm.py` | OpenRouter `ChatOpenAI` client (gpt-4o-mini) |
| `states.py` | TypedDict state definitions for each graph |
| `models.py` | Pydantic models for structured LLM output |
| `prompts.py` | LangChain `PromptTemplate` definitions |
| `*_graph.py` | Graph definitions (one file per graph) |
| `nodes/` | Node functions (one file per node) |

### Graph file pattern

```python
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import MyState
from graphs.nodes.my_node import my_node

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

graph_builder = StateGraph(MyState)

graph_builder.add_node("my_node", my_node)
graph_builder.add_edge(START, "my_node")
graph_builder.add_edge("my_node", END)

graph = graph_builder.compile()
```

### Node file pattern

```python
from graphs.llm import llm
from graphs.models import MyOutput
from graphs.prompts import my_prompt
from graphs.states import MyState

my_llm = llm.with_structured_output(MyOutput)
my_chain = my_prompt | my_llm

def my_node(state: MyState) -> MyState:
    result: MyOutput = my_chain.invoke({
        "input_field": state["input_field"],
    })

    return {
        **state,
        "output_field": result.some_field,
    }
```

### State TypedDict pattern (`graphs/states.py`)

```python
from typing import TypedDict, Optional
from sqlalchemy.orm import Session

class MyState(TypedDict):
    db: Session
    input_field: str
    output_field: Optional[str]
```

### Key conventions

- All graph files set LangSmith tracing env vars at module level
- Node functions return `{**state, ...updates}` — never mutate state directly
- Use `llm.with_structured_output(PydanticModel)` for structured LLM output
- Prompt templates live in `graphs/prompts.py`, not inline in nodes
- Graphs registered in `langgraph.json` for the LangGraph dev server

---

## 7. FastAPI Routers

**Location:** `routers/` — one file per feature.

### Rules

- Create an `APIRouter` with `prefix` and `tags`
- Protected pages use `require_admin` dependency: `user: Annotated[dict, Depends(require_admin)]`
- DB sessions via `db: Annotated[Session, Depends(get_db)]`
- Register every router in `serve.py` with `app.include_router(...)`

### HTMX pages pattern

```python
from fastapi import APIRouter, Request, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import require_admin
from core.render import render_section
from core.menu import menu_sections

router = APIRouter(prefix="/admin-panel/my-section", tags=["my-section"])

@router.get("")
async def my_section(
    request: Request,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return render_section(
        request=request,
        full_template="admin-panel-my-section.html",     # full page for direct nav
        fragment_template="menu-sections/_my_content.html", # fragment for HTMX swap
        context={
            "user": user,
            "menu_sections": menu_sections,
            "data": get_data(db),
        },
    )
```

### API endpoint pattern

```python
@router.post("/api/my-endpoint")
async def my_endpoint(
    request: Request,
    body: MyRequestModel,
    db: Annotated[Session, Depends(get_db)],
):
    result = do_something(db, body)
    return {"result": result}
```

### Auth model

- Supabase Auth issues JWTs; verified via JWKS at `http://127.0.0.1:54321/auth/v1/.well-known/jwks.json`
- `get_current_user()` validates JWT from cookie (`access_token`) or `Authorization` header
- `require_admin()` checks `app_metadata.role == "admin"`
- 401/403 exceptions outside `/auth` paths redirect to `/login` (see `serve.py` exception handler)

---

## 8. Templates (Jinja2 + HTMX)

**Location:** `templates/`

### Structure

| Path | Purpose |
|------|---------|
| `admin-panel.html` | Base layout with sidebar, header, `#main-content` block |
| `admin-panel-*.html` | Extend base layout via `{% extends %}` / `{% block content %}` |
| `login.html` | Standalone login page |
| `menu-sections/_*_content.html` | Content fragments swapped into `#main-content` by HTMX |
| `partials/_*.html` | Reusable fragments for modals, errors, dynamic lists |

### Key conventions

- HTMX navigation: sidebar links use `hx-get` + `hx-target="#main-content"` + `hx-swap="innerHTML"` + `hx-push-url="true"`
- `core/render.py` `render_section()` checks `HX-Request` header to decide full page vs fragment
- `|flag` Jinja2 filter for country flag emojis (e.g., `{{ lang.code | flag }}`)
- HTMX JSON encoding extension (`htmx-json-enc.js`) for POST bodies

---

## 9. Core Utilities

**Location:** `core/`

| File | Purpose |
|------|---------|
| `templates.py` | `Jinja2Templates(directory="templates")` + registers `flag` filter |
| `render.py` | `render_section()` — returns full page or fragment based on `HX-Request` header |
| `menu.py` | Sidebar menu sections config (list of dicts with `name`, `label`, `icon`) |
| `checkpointer.py` | `PostgresSaver` for LangGraph conversation memory; `setup_checkpointer()` creates tables idempotently |

---

## 10. Migrations (Two Systems)

### Alembic — Application Schema

**Location:** `alembic/versions/`

- Tables, columns, indexes, constraints
- One migration per schema change
- Generate: `uv run alembic revision --autogenerate -m "description"`
- Apply: `uv run alembic upgrade head`
- `alembic/env.py` imports ALL model files — add new models there
- `./scripts/migrate.sh` runs Alembic + assigns admin role

### Supabase — Infrastructure

**Location:** `supabase/migrations/`

- Postgres extensions (pgvector), RLS policies, roles, auth functions
- SQL-only, no Python
- Run automatically with `supabase db push` or via `./scripts/start.sh`

### When to use which

| Change type | Migration system |
|-------------|-----------------|
| New table, new column, new index | Alembic |
| RLS policy, Postgres extension, role | Supabase |
| Data migration (seed data) | Alembic |

---

## 11. Static Assets

**Location:** `static/`

| Path | Contents |
|------|----------|
| `css/admin-panel.css` | Main admin panel styles (1046 lines) |
| `css/login.css` | Login page with glassmorphism |
| `css/typography.css` | `@font-face` for ElmsSans |
| `css/fontawesome-free-7.3.0-web/` | FontAwesome 7 icon library |
| `js/htmx.min.js` | HTMX library |
| `js/htmx-json-enc.js` | HTMX JSON encoding extension |
| `js/chat_*.js` | Chat interface logic (agent API, streaming, messages, sessions, table edit/preview) |
| `js/generate_table.js` | Table generation API call |
| `js/table_renderer.js` | Builds DOM table from `TableData` objects |
| `js/language_pair_select.js` | Loads language pairs from API |
| `js/markdown_to_html.js` | Custom markdown-to-HTML converter |
| `js/switch_rules_tabs.js` | Tab switching for Chat/History/Rules |
| `fonts/` | ElmsSans (primary), Cantarell (secondary) |

---

## 12. Key Conventions Summary

| Convention | Detail |
|------------|--------|
| **ORM** | SQLAlchemy with `database.Base` (NOT SQLModel) |
| **Primary keys** | UUIDs everywhere, generated with `uuid.uuid4()` in Python |
| **No relationships** | FK columns only; joins done manually in CRUD |
| **LLM provider** | OpenRouter (gpt-4o-mini) via `graphs/llm.py` |
| **Tracing** | LangSmith enabled for all graph runs |
| **DB URL** | From `.env` `DATABASE_URL_LOCAL` (Postgres on port 54322) |
| **Session** | `database.get_db()` generator for FastAPI DI |
| **Env vars** | `.env` is gitignored; required at runtime |
| **Entrypoint** | `serve.py` (NOT `main.py`, which is a stub) |
| **Port** | 8080 for uvicorn |

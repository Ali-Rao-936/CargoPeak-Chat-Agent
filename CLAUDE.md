# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dev server (auto-reload)
uvicorn main:app --reload

# Run on a specific port
uvicorn main:app --reload --port 8000

# Interactive chat tester (requires the server to be running in another terminal)
python chat_test.py
```

Copy `.env.example` to `.env` and fill in `SUPABASE_DB_URL` and `OPENAI_API_KEY` before starting.

## Architecture

This is a **FastAPI + OpenAI agentic chatbot** for Cargo Peak, a UAE logistics company. The bot qualifies shipping leads and books appointments via tool calls.

### Request flow

```
POST /api/chat
  → main.py: validates request, calls run_agent()
    → agent.py: agentic loop (up to MAX_ITERATIONS=5)
        → OpenAI gpt-4o-mini with TOOL_SCHEMAS
        → if finish_reason="tool_calls": execute_tool() → db insert / n8n webhook
        → if finish_reason="stop": return text to main.py
  → main.py: saves full conversation to DB, returns ChatResponse
```

### Key files

| File | Role |
|------|------|
| `main.py` | FastAPI app, routes, lifespan (db pool open/close) |
| `agent.py` | OpenAI agentic loop — `run_agent(conversation, session_id)` |
| `tools.py` | Tool schemas (sent to OpenAI) + implementations (`capture_lead`, `book_appointment`) |
| `db.py` | asyncpg connection pool; `conversations`, `leads`, `appointments` tables |
| `config.py` | pydantic-settings loading from `.env` |
| `chat_test.py` | Interactive CLI tester — hits the running server, maintains conversation state |
| `utils/supabase/client.py` | Supabase REST client singleton — **not used by the main flow** |

### Tool system

Tools are defined in two places in `tools.py`:
- `TOOL_SCHEMAS` — OpenAI function-calling JSON schemas sent with every request
- `_TOOL_REGISTRY` — maps tool name → async implementation function

To add a new tool: add an entry to both `TOOL_SCHEMAS` and `_TOOL_REGISTRY`. The agent loop in `agent.py` calls `execute_tool(name, args, session_id)` automatically.

### Database

`db.py` uses raw `asyncpg` against the Supabase PostgreSQL connection string. The pool is created at FastAPI startup via the lifespan context manager. Three tables must exist: `conversations` (session_id PK), `leads`, and `appointments`. Date/datetime values from the LLM are normalized by `_parse_date` / `_parse_datetime` before insertion.

### Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SUPABASE_DB_URL` | Yes | asyncpg connection string for Postgres |
| `OPENAI_API_KEY` | Yes | OpenAI API access (a default exists in `config.py` — remove it and set via `.env`) |
| `RESEND_API_KEY` | No | Email sending (stub `TODO`s exist in `tools.py`) |
| `SALES_EMAIL` | No | Sales alert destination |
| `ALLOWED_ORIGIN` | No | CORS origin (default: `http://localhost:5173`) |
| `N8N_WEBHOOK_URL` | No | Optional n8n webhook fired on new leads |
| `SUPABASE_URL` / `SUPABASE_KEY` | No | Only needed if using `utils/supabase/client.py` |

> **Security note**: `config.py` contains a hardcoded `openai_api_key` default. That key should be removed from source and always supplied via `.env`.

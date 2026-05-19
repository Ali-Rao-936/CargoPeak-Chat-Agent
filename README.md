# Cargo Peak Chatbot Agent

An AI-powered chatbot for [Cargo Peak](https://cargopeakuae.com), a UAE-based logistics company. Built with FastAPI and OpenAI's function-calling API, it qualifies shipping leads and books consultation appointments through a natural conversational flow.

## Features

- Conversational lead qualification (one question at a time)
- Tool-based actions: saves leads and appointments directly to the database
- Automated emails to customers and the sales team via Resend
- Full conversation history persisted in Supabase (PostgreSQL)
- Optional n8n webhook on new lead capture

## Tech Stack

| Layer | Tech |
|-------|------|
| API | FastAPI + uvicorn |
| AI | OpenAI `gpt-4o-mini` with function calling |
| Database | Supabase (asyncpg) |
| Email | Resend |
| Config | pydantic-settings |

## Project Structure

```
├── main.py          # FastAPI app, routes, lifespan DB pool
├── agent.py         # OpenAI agentic loop (up to 5 iterations)
├── tools.py         # Tool schemas + implementations (capture_lead, book_appointment)
├── db.py            # asyncpg pool, conversation/lead/appointment queries
├── config.py        # pydantic-settings loaded from .env
├── email_service.py # Resend email templates (customer + sales alerts)
├── chat_test.py     # Interactive CLI tester
└── utils/
    └── supabase/    # Supabase REST client (not used in main flow)
```

## Setup

**1. Clone and install dependencies**

```bash
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
```

Fill in your `.env`:

```env
OPENAI_API_KEY=sk-...
SUPABASE_DB_URL=postgresql://postgres:[password]@[host]:5432/postgres
RESEND_API_KEY=re_...          # optional — emails are skipped if blank
SALES_EMAIL=sales@example.com  # where lead alerts go
ALLOWED_ORIGIN=http://localhost:5173
N8N_WEBHOOK_URL=               # optional
```

**3. Create database tables**

Run this SQL in your Supabase project:

```sql
CREATE TABLE conversations (
  session_id TEXT PRIMARY KEY,
  messages   JSONB NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE leads (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   TEXT,
  full_name    TEXT,
  email        TEXT,
  phone        TEXT,
  origin       TEXT,
  destination  TEXT,
  pieces       INTEGER,
  length_cm    NUMERIC,
  width_cm     NUMERIC,
  height_cm    NUMERIC,
  weight_kg    NUMERIC,
  service_type TEXT,
  ready_date   DATE,
  notes        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE appointments (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id             TEXT,
  full_name              TEXT,
  email                  TEXT,
  phone                  TEXT,
  preferred_datetime_iso TIMESTAMPTZ,
  topic                  TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**4. Run the server**

```bash
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`.

## Usage

**Chat endpoint**

```
POST /api/chat
```

```json
{
  "session_id": "user-abc-123",
  "messages": [
    { "role": "user", "content": "Hi, I want to ship boxes from Dubai to Riyadh" }
  ]
}
```

Response:

```json
{
  "reply": "Great, Dubai to Riyadh 🚚 — one of our regular routes. About how many boxes are we talking?",
  "actions": []
}
```

**Interactive CLI tester** (requires the server running in another terminal)

```bash
python chat_test.py
```

**Health check**

```
GET /health
GET /db-check
```

## Request Flow

```
POST /api/chat
  → main.py: validates request, calls run_agent()
    → agent.py: agentic loop (max 5 iterations)
        → OpenAI gpt-4o-mini + TOOL_SCHEMAS
        → tool_calls → execute_tool() → DB insert + email + n8n
        → stop → return text
  → main.py: saves conversation to DB, returns ChatResponse
```

## Adding a Tool

1. Add the OpenAI function schema to `TOOL_SCHEMAS` in `tools.py`
2. Implement the async function
3. Register it in `_TOOL_REGISTRY`

The agent loop calls `execute_tool(name, args, session_id)` automatically.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `SUPABASE_DB_URL` | Yes | asyncpg PostgreSQL connection string |
| `RESEND_API_KEY` | No | Resend API key for emails |
| `SALES_EMAIL` | No | Destination for lead/appointment alerts |
| `ALLOWED_ORIGIN` | No | CORS origin (default: `http://localhost:5173`) |
| `N8N_WEBHOOK_URL` | No | Webhook fired on new lead capture |
| `SUPABASE_URL` / `SUPABASE_KEY` | No | Only needed for `utils/supabase/client.py` |

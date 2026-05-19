import asyncpg
import json
from typing import Optional
from config import settings
from datetime import date, datetime



# Global connection pool (initialized at startup)
pool: Optional[asyncpg.Pool] = None

def _parse_date(value) -> Optional[date]:
    """Convert an ISO date string ('YYYY-MM-DD' or full ISO datetime) to a date object."""
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            # Handles both '2026-05-25' and '2026-05-25T10:00:00+04:00'
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
    return None

def _parse_datetime(value) -> Optional[datetime]:
    """Convert an ISO datetime string to a datetime object."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None



async def init_db():
    """Open the connection pool. Called once at FastAPI startup."""
    global pool
    pool = await asyncpg.create_pool(
        settings.supabase_db_url,
        min_size=1,
        max_size=5,
        command_timeout=30,
    )
    print("✅ Database pool created")


async def close_db():
    """Close the pool gracefully. Called at FastAPI shutdown."""
    global pool
    if pool:
        await pool.close()
        print("✅ Database pool closed")


# ---------- Conversations ----------

async def save_conversation(session_id: str, messages: list) -> None:
    """Upsert a conversation — insert if new, update if it exists."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversations (session_id, messages, updated_at)
            VALUES ($1, $2::jsonb, now())
            ON CONFLICT (session_id) 
            DO UPDATE SET messages = $2::jsonb, updated_at = now()
            """,
            session_id,
            json.dumps(messages),
        )


async def get_conversation(session_id: str) -> Optional[list]:
    """Fetch a stored conversation by session ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT messages FROM conversations WHERE session_id = $1",
            session_id,
        )
        return row["messages"] if row else None


# ---------- Leads ----------

async def insert_lead(session_id: str, data: dict) -> str:
    """Insert a lead, return its UUID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO leads (
              session_id, full_name, email, phone, 
              origin, destination, 
              pieces, length_cm, width_cm, height_cm, weight_kg,
              service_type, ready_date, notes
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id
            """,
            session_id,
            data.get("full_name"),
            data.get("email"),
            data.get("phone"),
            data.get("origin"),
            data.get("destination"),
            data.get("pieces"),
            data.get("length_cm"),
            data.get("width_cm"),
            data.get("height_cm"),
            data.get("weight_kg"),
            data.get("service_type"),
            _parse_date(data.get("ready_date")), 
            data.get("notes"),
        )
        return str(row["id"])

# ---------- Appointments ----------

async def insert_appointment(session_id: str, data: dict) -> str:
    """Insert an appointment, return its UUID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO appointments (
              session_id, full_name, email, phone, 
              preferred_datetime_iso, topic
            )
            VALUES ($1, $2, $3, $4, $5::timestamptz, $6)
            RETURNING id
            """,
            session_id,
            data.get("full_name"),
            data.get("email"),
            data.get("phone"),
            _parse_datetime(data.get("preferred_datetime_iso")),
            data.get("topic"),
        )
        return str(row["id"])
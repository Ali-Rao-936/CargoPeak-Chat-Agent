from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import db
from agent import run_agent
import traceback

# ----- Lifespan: startup / shutdown -----


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield
    await db.close_db()


app = FastAPI(title="Cargo Peak Chatbot Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://www.cargopeakuae.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # allows OPTIONS preflight + POST
    allow_headers=["*"],  # allows Content-Type, etc.
)


# ----- Request / response models -----


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str
    actions: list[str]


# ----- Routes -----


@app.get("/")
async def root():
    return {"message": "Cargo Peak Chatbot API is running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cargo-peak-chatbot-api"}


@app.get("/db-check")
async def db_check():
    async with db.pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
    return {"db": "connected", "result": result}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    try:
        msgs = [{"role": m.role, "content": m.content} for m in body.messages]

        reply = await run_agent(msgs, body.session_id)

        final_messages = msgs + [{"role": "assistant", "content": reply}]
        await db.save_conversation(body.session_id, final_messages)

        return ChatResponse(reply=reply, actions=[])
    except Exception as e:
        print("=" * 60)
        print(f"❌ ERROR IN /api/chat: {type(e).__name__}: {e}")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        raise

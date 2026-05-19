"""
Interactive chat tester for the FastAPI chatbot.
Type messages, see replies, the script auto-builds the conversation array.

Usage (in a SECOND terminal with venv active, while uvicorn runs in the first):
    python chat_test.py

Commands while running:
    /new    - start a fresh conversation (new session_id)
    /show   - print the full conversation array
    /quit   - exit (or use Ctrl+C)
"""
import asyncio
import json
import uuid
import httpx


API_URL = "http://localhost:8000/api/chat"


def new_session() -> tuple[str, list]:
    """Start a fresh conversation."""
    sid = f"test-{uuid.uuid4().hex[:8]}"
    print(f"\n💬 New conversation — session_id: {sid}")
    print("─" * 60)
    return sid, []


async def main():
    session_id, messages = new_session()

    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            try:
                user_input = input("\n🧑 You: ").strip()
                if not user_input:
                    continue

                # Commands
                if user_input == "/quit":
                    print("👋 Bye!")
                    break
                if user_input == "/new":
                    session_id, messages = new_session()
                    continue
                if user_input == "/show":
                    print(json.dumps(messages, indent=2))
                    continue

                # Append user message
                messages.append({"role": "user", "content": user_input})

                # Send to FastAPI
                response = await client.post(API_URL, json={
                    "session_id": session_id,
                    "messages": messages,
                })
                response.raise_for_status()
                data = response.json()

                reply = data["reply"]
                actions = data.get("actions", [])

                # Display
                print(f"\n🤖 Bot: {reply}")
                if actions:
                    print(f"      ⚡ Tools fired: {', '.join(actions)}")

                # Append assistant message for next turn
                messages.append({"role": "assistant", "content": reply})

            except KeyboardInterrupt:
                print("\n👋 Bye!")
                break
            except httpx.HTTPStatusError as e:
                print(f"\n❌ HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                print(f"\n❌ Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
"""
Tools the chatbot can call — OpenAI function-calling format.
"""
import httpx
import db
from config import settings
from email_service import email_service


# =========================================================
# Tool schemas — sent to OpenAI with every request
# =========================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "capture_lead",
            "description": (
               "REQUIRED ACTION: Save the customer's cargo shipping inquiry to "
            "the database and notify the sales team. You MUST call this "
            "function the moment you have collected full_name, email, AND "
            "phone — do not delay, do not just acknowledge in text. "
            "Calling this function is the ONLY way to actually save the "
            "lead. Pass every shipment detail you've gathered "
            "(origin, destination, pieces, dimensions, weight, service_type, "
            "ready_date) as arguments — partial info is fine, just don't "
            "skip the call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name":   {"type": "string", "description": "Customer's full name"},
                    "email":       {"type": "string", "description": "Customer's email address"},
                    "phone":       {"type": "string", "description": "Customer's phone with country code, e.g. +971501234567"},
                    "origin":      {"type": "string", "description": "Pickup city/country, e.g. 'Dubai, UAE'"},
                    "destination": {"type": "string", "description": "Delivery city/country, e.g. 'London, UK'"},
                    "pieces":      {"type": "integer", "description": "Number of boxes/pallets/items"},
                    "length_cm":   {"type": "number", "description": "Length per piece in centimeters"},
                    "width_cm":    {"type": "number", "description": "Width per piece in centimeters"},
                    "height_cm":   {"type": "number", "description": "Height per piece in centimeters"},
                    "weight_kg":   {"type": "number", "description": "Total weight in kilograms"},
                    "service_type": {
                        "type": "string",
                        "enum": ["air", "sea", "land", "door_to_door", "other"],
                        "description": "Type of cargo service requested",
                    },
                    "ready_date":  {"type": "string", "description": "ISO date (YYYY-MM-DD) when goods are ready for pickup"},
                    "notes":       {"type": "string", "description": "Any extra context from the conversation"},
                },
                "required": ["full_name", "email", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book a consultation call when the customer asks to speak with a human "
                "specialist. Call this ONLY after collecting full name, email, and their "
                "preferred date/time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "email":     {"type": "string"},
                    "phone":     {"type": "string"},
                    "preferred_datetime_iso": {
                        "type": "string",
                        "description": "ISO 8601 datetime with Dubai offset, e.g. '2026-05-22T14:00:00+04:00'",
                    },
                    "topic":     {"type": "string", "description": "What the customer wants to discuss"},
                },
                "required": ["full_name", "email", "preferred_datetime_iso"],
            },
        },
    },
]


# =========================================================
# Implementations
# =========================================================

async def _capture_lead_impl(session_id: str, args: dict) -> dict:
    lead_id = await db.insert_lead(session_id, args)

    customer_ok = await email_service.send_customer_lead_confirmation(args)
    sales_ok = await email_service.send_sales_lead_alert(args)
    print(f"{'✅' if customer_ok else '⚠️ '} Customer confirmation email sent={customer_ok}")
    print(f"{'✅' if sales_ok else '⚠️ '} Sales alert email sent={sales_ok}")

    if settings.n8n_webhook_url:
        async with httpx.AsyncClient(timeout=5) as c:
            try:
                await c.post(settings.n8n_webhook_url,
                             json={"event": "new_lead", "lead_id": lead_id, **args})
            except Exception as e:
                print(f"⚠️  n8n webhook failed (non-fatal): {e}")

    return {"status": "lead_saved", "lead_id": lead_id,
            "customer_email_sent": customer_ok, "sales_alerted": sales_ok}


async def _book_appointment_impl(session_id: str, args: dict) -> dict:
    appt_id = await db.insert_appointment(session_id, args)

    customer_ok = await email_service.send_customer_appointment_confirmation(args)
    sales_ok = await email_service.send_sales_appointment_alert(args)
    print(f"{'✅' if customer_ok else '⚠️ '} Appointment confirmation email sent={customer_ok}")
    print(f"{'✅' if sales_ok else '⚠️ '} Appointment alert email sent={sales_ok}")

    return {"status": "appointment_booked", "appointment_id": appt_id,
            "customer_email_sent": customer_ok, "sales_alerted": sales_ok}


_TOOL_REGISTRY = {
    "capture_lead": _capture_lead_impl,
    "book_appointment": _book_appointment_impl,
}


async def execute_tool(name: str, args: dict, session_id: str) -> dict:
    impl = _TOOL_REGISTRY.get(name)
    if impl is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return await impl(session_id, args)
    except Exception as e:
        print(f"❌ Tool {name} failed: {e}")
        return {"error": f"tool execution failed: {str(e)}"}
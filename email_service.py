"""
Email service using Resend. All methods are async, return bool, and never raise.
Emails are best-effort: failures are logged but never break the chat flow.
"""
import asyncio
import resend
from config import settings


def _customer_html_wrapper(body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;">
  <div style="max-width:600px;margin:32px auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
    <div style="background:#1e40af;padding:32px 24px;text-align:center;">
      <h1 style="color:#ffffff;margin:0;font-size:26px;letter-spacing:-0.5px;">Cargo Peak</h1>
      <p style="color:#bfdbfe;margin:8px 0 0;font-size:14px;">cargopeakuae.com</p>
    </div>
    <div style="padding:32px 24px;color:#111827;font-size:15px;line-height:1.6;">
      {body_html}
    </div>
    <div style="background:#f9fafb;padding:20px 24px;border-top:1px solid #e5e7eb;font-size:13px;color:#6b7280;text-align:center;">
      Questions? Email us at
      <a href="mailto:updates@cargopeakuae.com" style="color:#1e40af;">updates@cargopeakuae.com</a>
      or call <a href="tel:+971576512345" style="color:#1e40af;">+971 57 651 2345</a>
    </div>
  </div>
</body>
</html>"""


def _table_html(data: dict) -> str:
    rows = ""
    for key, value in data.items():
        if value is None or value == "":
            continue
        label = key.replace("_", " ").title()
        rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;"
            f"font-weight:600;white-space:nowrap;color:#374151;'>{label}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#111827;'>{value}</td>"
            f"</tr>"
        )
    return (
        "<table style='border-collapse:collapse;width:100%;font-family:Arial,sans-serif;"
        "font-size:14px;'>"
        f"{rows}"
        "</table>"
    )


class EmailService:
    FROM_CUSTOMER = "Cargo Peak <hello@cargopeakuae.com>"
    FROM_INTERNAL = "CargoBot <bot@cargopeakuae.com>"
    CC_TEAM = "info@cargopeakuae.com"

    def __init__(self):
        resend.api_key = settings.resend_api_key

    async def _send(self, params: dict) -> bool:
        try:
            await asyncio.to_thread(resend.Emails.send, params)
            return True
        except Exception as e:
            print(f"❌ Email send failed ({params.get('subject', '?')}): {e}")
            return False

    async def send_customer_lead_confirmation(self, lead: dict) -> bool:
        name = lead.get("full_name", "there")
        origin = lead.get("origin")
        destination = lead.get("destination")

        route_line = ""
        if origin and destination:
            route_line = (
                f"<p>We've received your enquiry for a shipment from "
                f"<strong>{origin}</strong> to <strong>{destination}</strong>.</p>"
            )
        else:
            route_line = "<p>We've received your cargo shipping enquiry.</p>"

        body = f"""
<p>Hi {name},</p>
{route_line}
<p>One of our cargo specialists will review your details and follow up with a
tailored quote within <strong>1 hour</strong> during business hours
(Mon–Sat, 9 am – 7 pm GST).</p>
<p style="margin-top:24px;">Thanks for choosing Cargo Peak — we'll be in touch shortly! 📦</p>
"""
        return await self._send({
            "from": self.FROM_CUSTOMER,
            "to": [lead["email"]],
            "cc": [self.CC_TEAM],
            "subject": "We've received your cargo inquiry — Cargo Peak",
            "html": _customer_html_wrapper(body),
        })

    async def send_customer_appointment_confirmation(self, appt: dict) -> bool:
        name = appt.get("full_name", "there")
        dt = appt.get("preferred_datetime_iso", "TBC")
        topic = appt.get("topic", "General enquiry")

        body = f"""
<p>Hi {name},</p>
<p>Your consultation call with Cargo Peak has been booked. Here are the details:</p>
<table style="border-collapse:collapse;margin:16px 0;font-size:15px;">
  <tr>
    <td style="padding:6px 16px 6px 0;font-weight:600;color:#374151;">Date &amp; Time</td>
    <td style="padding:6px 0;color:#111827;">{dt}</td>
  </tr>
  <tr>
    <td style="padding:6px 16px 6px 0;font-weight:600;color:#374151;">Topic</td>
    <td style="padding:6px 0;color:#111827;">{topic}</td>
  </tr>
</table>
<p>Our specialist will call you at the number you provided. If you need to
reschedule, just reach out and we'll sort it out quickly.</p>
<p style="margin-top:24px;">Looking forward to speaking with you! ✅</p>
"""
        return await self._send({
            "from": self.FROM_CUSTOMER,
            "to": [appt["email"]],
            "cc": [self.CC_TEAM],
            "subject": "Your consultation is booked — Cargo Peak",
            "html": _customer_html_wrapper(body),
        })

    async def send_sales_lead_alert(self, lead: dict) -> bool:
        full_name = lead.get("full_name", "Unknown")
        origin = lead.get("origin") or "N/A"
        destination = lead.get("destination") or "N/A"

        html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <h2 style="color:#111827;margin-bottom:4px;">🚚 New Lead</h2>
  <p style="color:#6b7280;margin-top:0;font-size:14px;">
    Submitted via CargoBot — reply to this email to contact the customer directly.
  </p>
  {_table_html(lead)}
</div>
"""
        return await self._send({
            "from": self.FROM_INTERNAL,
            "to": [settings.sales_email],
            "reply_to": lead.get("email"),
            "subject": f"🚚 New lead: {full_name} — {origin} → {destination}",
            "html": html,
        })

    async def send_sales_appointment_alert(self, appt: dict) -> bool:
        full_name = appt.get("full_name", "Unknown")

        html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <h2 style="color:#111827;margin-bottom:4px;">📅 Consultation Booked</h2>
  <p style="color:#6b7280;margin-top:0;font-size:14px;">
    Booked via CargoBot — reply to contact the customer.
  </p>
  {_table_html(appt)}
</div>
"""
        return await self._send({
            "from": self.FROM_INTERNAL,
            "to": [settings.sales_email],
            "reply_to": appt.get("email"),
            "subject": f"📅 Consultation booked: {full_name}",
            "html": html,
        })


email_service = EmailService()

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
      or call <a href="tel:+971508819829" style="color:#1e40af;">+971 50 881 9829</a>
    </div>
  </div>
</body>
</html>"""


LEAD_FIELD_LABELS = [
    ("full_name", "Full Name"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("origin", "Origin"),
    ("destination", "Destination"),
    ("service_type", "Service Type"),
    ("pieces", "Pieces"),
    ("length_cm", "Length (cm)"),
    ("width_cm", "Width (cm)"),
    ("height_cm", "Height (cm)"),
    ("weight_kg", "Weight (kg)"),
    ("ready_date", "Ready Date"),
    ("notes", "Notes"),
]

APPOINTMENT_FIELD_LABELS = [
    ("full_name", "Full Name"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("preferred_datetime_iso", "Date & Time"),
    ("topic", "Topic"),
]


def _table_html(data: dict, kind: str = "lead") -> str:
    """
    Render a dict as a styled HTML table.
    Only shows fields that exist in the labels map AND have a non-empty value.
    """
    labels = LEAD_FIELD_LABELS if kind == "lead" else APPOINTMENT_FIELD_LABELS

    rows = ""
    for key, label in labels:
        value = data.get(key)
        if value in (None, "", [], 0) and value is not False:
            # skip empty/None — but keep "0" if you ever need it (unlikely here)
            continue
        rows += f"""
        <tr>
          <td style="padding:10px 14px;font-weight:600;color:#555;background:#f3f4f6;border-bottom:1px solid #e5e7eb;width:35%;">{label}</td>
          <td style="padding:10px 14px;color:#111;border-bottom:1px solid #e5e7eb;">{value}</td>
        </tr>
        """

    if not rows:
        return '<p style="color:#6b7280;font-style:italic;">No additional details captured.</p>'

    return f"""
    <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">
      {rows}
    </table>
    """


class EmailService:
    FROM_CUSTOMER = "Cargo Peak <updates@cargopeakuae.com>"
    FROM_INTERNAL = "CargoBot <updates@cargopeakuae.com>"

    def __init__(self):
        resend.api_key = settings.resend_api_key

    async def _send(self, params: dict) -> bool:
        try:
            await asyncio.to_thread(resend.Emails.send, params)
            return True
        except Exception as e:
            print(f"❌ Email send failed ({params.get('subject', '?')}): {e}")
            return False

    ## Customer-facing emails
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
        return await self._send(
            {
                "from": self.FROM_CUSTOMER,
                "to": [lead["email"]],
                "subject": "We've received your cargo inquiry — Cargo Peak",
                "html": _customer_html_wrapper(body),
            }
        )

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
        return await self._send(
            {
                "from": self.FROM_CUSTOMER,
                "to": [appt["email"]],
                "subject": "Your consultation is booked — Cargo Peak",
                "html": _customer_html_wrapper(body),
            }
        )

    ## Internal-facing emails
    async def send_sales_lead_alert(self, lead: dict) -> bool:
        full_name = lead.get("full_name", "Unknown")
        origin = lead.get("origin") or "N/A"
        destination = lead.get("destination") or "N/A"
        email = lead.get("email", "")
        phone = lead.get("phone", "")

        html = f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#111;">
  <div style="background:#1e40af;color:#fff;padding:18px 24px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;">🚚 New Lead from CargoBot</h2>
    <p style="margin:6px 0 0 0;opacity:0.9;font-size:14px;">
      Reach out within the hour for best conversion.
    </p>
  </div>

  <div style="padding:20px 24px;background:#fff;border:1px solid #e5e7eb;border-top:none;">
    <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;margin-bottom:20px;border-radius:4px;">
      <strong>Contact:</strong> {full_name}<br>
      📧 <a href="mailto:{email}" style="color:#1e40af;text-decoration:none;">{email}</a><br>
      📞 <a href="tel:{phone}" style="color:#1e40af;text-decoration:none;">{phone}</a>
    </div>

    <h3 style="margin:0 0 12px 0;color:#1e40af;font-size:16px;">Lead Details</h3>
    {_table_html(lead, kind="lead")}

    <p style="margin-top:24px;color:#6b7280;font-size:12px;">
      Captured automatically by the CargoPeak website chatbot.
      Reply to this email to respond directly to the customer.
    </p>
  </div>
</div>
"""

        return await self._send(
            {
                "from": self.FROM_INTERNAL,
                "to": [settings.sales_email],
                "reply_to": lead.get("email"),
                "subject": f"🚚 New lead: {full_name} — {origin} → {destination}",
                "html": html,
            }
        )

    async def send_sales_appointment_alert(self, appt: dict) -> bool:
        full_name = appt.get("full_name", "Unknown")
        email = appt.get("email", "")
        phone = appt.get("phone", "")
        when = appt.get("preferred_datetime_iso", "—")

        html = f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#111;">
  <div style="background:#1e40af;color:#fff;padding:18px 24px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;">📅 New Consultation Booked</h2>
    <p style="margin:6px 0 0 0;opacity:0.9;font-size:14px;">
      Scheduled for {when} — reply to contact the customer.
    </p>
  </div>

  <div style="padding:20px 24px;background:#fff;border:1px solid #e5e7eb;border-top:none;">
    <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;margin-bottom:20px;border-radius:4px;">
      <strong>Customer:</strong> {full_name}<br>
      📧 <a href="mailto:{email}" style="color:#1e40af;text-decoration:none;">{email}</a><br>
      📞 <a href="tel:{phone}" style="color:#1e40af;text-decoration:none;">{phone}</a>
    </div>

    <h3 style="margin:0 0 12px 0;color:#1e40af;font-size:16px;">Booking Details</h3>
    {_table_html(appt, kind="appointment")}
  </div>
</div>
"""

        return await self._send(
            {
                "from": self.FROM_INTERNAL,
                "to": [settings.sales_email],
                "reply_to": appt.get("email"),
                "subject": f"📅 Consultation booked: {full_name}",
                "html": html,
            }
        )


email_service = EmailService()

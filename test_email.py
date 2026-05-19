"""
Standalone smoke-test for EmailService.
Run with: python test_email.py
Does NOT require the FastAPI server to be running.
"""
import asyncio
from email_service import email_service


async def main():
    recipient = input("Enter email to send test confirmation to: ").strip()
    if not recipient:
        print("❌ No email entered. Exiting.")
        return

    fake_lead = {
        "full_name": "Adnan Abbas",
        "email": recipient,
        "phone": "+971501234567",
        "origin": "Dubai, UAE",
        "destination": "London, UK",
        "pieces": 3,
        "length_cm": 60,
        "width_cm": 40,
        "height_cm": 30,
        "weight_kg": 45.5,
        "service_type": "air",
        "ready_date": "2026-06-01",
        "notes": "Fragile electronics — handle with care",
    }
    fake_appt = {
        "full_name": "Adnan Abbas",
        "email": recipient,
        "phone": "+971501234567",
        "preferred_datetime_iso": "2026-05-22T14:00:00+04:00",
        "topic": "Air freight quote for 3 boxes to London",
    }

    print(f"\nSending 4 test emails to {recipient} ...\n")

    results = [
        ("Customer lead confirmation",   await email_service.send_customer_lead_confirmation(fake_lead)),
        ("Sales lead alert",             await email_service.send_sales_lead_alert(fake_lead)),
        ("Customer appt confirmation",   await email_service.send_customer_appointment_confirmation(fake_appt)),
        ("Sales appointment alert",      await email_service.send_sales_appointment_alert(fake_appt)),
    ]

    print("\n─── Results ───")
    all_passed = True
    for label, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status}  {label}")
        if not ok:
            all_passed = False

    print()
    if all_passed:
        print("✅ All emails sent successfully.")
    else:
        print("⚠️  Some emails failed — check output above for details.")


if __name__ == "__main__":
    asyncio.run(main())

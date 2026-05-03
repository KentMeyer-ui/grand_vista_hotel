"""
Email Service — Resend API
Sends real emails for booking events.
"""

import os
import json
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
FROM_EMAIL     = os.environ.get('FROM_EMAIL', 'onboarding@resend.dev')
HOTEL_NAME     = 'Grand Vista Hotel'


def _send(to_email: str, subject: str, html: str) -> bool:
    """Core send function using Resend API over HTTPS."""
    try:
        if not RESEND_API_KEY:
            print(f'[email] Skipped (no credentials): {subject}')
            return False

        payload = json.dumps({
            'from':    f'{HOTEL_NAME} <{FROM_EMAIL}>',
            'to':      [to_email],
            'subject': subject,
            'html':    html,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.resend.com/emails',
            data    = payload,
            headers = {
                'Authorization': f'Bearer {RESEND_API_KEY}',
                'Content-Type':  'application/json',
            },
            method = 'POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            print(f'[email] Sent to {to_email}: {subject}')
            return True

    except Exception as e:
        print(f'[email] Failed: {e}')
        return False


def _base_template(content: str, color: str = '#c9a84c') -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#f5f5f0;font-family:'Helvetica Neue',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0;padding:40px 0;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

            <!-- Header -->
            <tr><td style="background:#0d1b2a;padding:32px 40px;text-align:center;">
              <h1 style="color:{color};font-family:Georgia,serif;font-size:28px;margin:0;letter-spacing:0.04em;">Grand Vista Hotel</h1>
              <p style="color:rgba(255,255,255,0.5);font-size:11px;letter-spacing:0.15em;text-transform:uppercase;margin:6px 0 0;">Hotel Management System</p>
            </td></tr>

            <!-- Body -->
            <tr><td style="padding:40px;">
              {content}
            </td></tr>

            <!-- Footer -->
            <tr><td style="background:#f9f6ef;padding:24px 40px;text-align:center;border-top:1px solid #e8ddc8;">
              <p style="color:#888;font-size:12px;margin:0;">Grand Vista Hotel · reservations@grandvista.com · +63 88 123 4567</p>
              <p style="color:#aaa;font-size:11px;margin:8px 0 0;">Cagayan de Oro, Philippines</p>
            </td></tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _booking_details_table(booking: dict) -> str:
    rows = [
        ('Booking Reference', f"#{booking['id']}"),
        ('Room',              f"{booking['room_number']} — {booking['type_label']}"),
        ('Check-In',          booking['check_in']),
        ('Check-Out',         booking['check_out']),
        ('Nights',            str(booking['total_nights'])),
        ('Guests',            str(booking['adults'])),
        ('Payment',           'Paid upfront' if booking['pay_now'] else 'Pay at hotel'),
        ('Risk Level',        booking.get('risk_level', '—')),
    ]
    rows_html = ''.join(f"""
        <tr>
          <td style="padding:10px 0;color:#888;font-size:13px;border-bottom:1px solid #f0ebe0;width:40%;">{k}</td>
          <td style="padding:10px 0;font-size:13px;font-weight:600;border-bottom:1px solid #f0ebe0;">{v}</td>
        </tr>
    """ for k, v in rows)
    return f'<table width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>'


# ── Email senders ─────────────────────────────────────────────────────────────

def send_booking_confirmed(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#0d1b2a;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Booking Confirmed ✓</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, your reservation has been confirmed. We look forward to welcoming you.</p>
        {details}
        <div style="margin-top:28px;padding:16px 20px;background:#f0faf4;border-left:4px solid #1a7a4a;border-radius:4px;">
          <p style="margin:0;color:#1a7a4a;font-size:13px;font-weight:600;">✓ Your booking is confirmed. No further action needed.</p>
        </div>
        <p style="margin-top:24px;color:#666;font-size:13px;">If you need to cancel, please do so at least 48 hours before check-in.</p>
    """
    return _send(guest_email, f'Booking Confirmed — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#1a7a4a'))


def send_booking_under_review(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#0d1b2a;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Booking Received — Under Review</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, we have received your booking request. Our team is currently reviewing it and will confirm shortly.</p>
        {details}
        <div style="margin-top:28px;padding:16px 20px;background:#fffbeb;border-left:4px solid #b7791f;border-radius:4px;">
          <p style="margin:0;color:#b7791f;font-size:13px;font-weight:600;">⏳ Your booking is pending staff review. You will receive another email once a decision is made.</p>
        </div>
    """
    return _send(guest_email, f'Booking Under Review — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#c9a84c'))


def send_booking_approved(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#0d1b2a;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Booking Approved ✓</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, great news — our team has reviewed and approved your booking.</p>
        {details}
        {'<div style="margin-top:16px;padding:14px 18px;background:#f0f0ff;border-left:4px solid #084298;border-radius:4px;"><p style="margin:0;color:#084298;font-size:13px;font-weight:600;">Staff Note: ' + booking.get("staff_notes","") + '</p></div>' if booking.get("staff_notes") else ''}
        <div style="margin-top:20px;padding:16px 20px;background:#f0faf4;border-left:4px solid #1a7a4a;border-radius:4px;">
          <p style="margin:0;color:#1a7a4a;font-size:13px;font-weight:600;">✓ Your booking is now confirmed. We look forward to welcoming you.</p>
        </div>
    """
    return _send(guest_email, f'Booking Approved — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#1a7a4a'))


def send_booking_rejected(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#c0392b;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Booking Not Accepted</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, unfortunately we are unable to accept your booking at this time.</p>
        {details}
        {'<div style="margin-top:16px;padding:14px 18px;background:#fef3f2;border-left:4px solid #c0392b;border-radius:4px;"><p style="margin:0;color:#c0392b;font-size:13px;">Reason: ' + booking.get("staff_notes","No reason provided.") + '</p></div>' if booking.get("staff_notes") else ''}
        <p style="margin-top:24px;color:#666;font-size:13px;">We apologize for the inconvenience. Please contact us directly if you have questions.</p>
    """
    return _send(guest_email, f'Booking Update — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#c0392b'))


def send_prepayment_required(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#0d1b2a;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Prepayment Required</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, our team has reviewed your booking and requires advance payment to confirm your reservation.</p>
        {details}
        <div style="margin-top:28px;padding:16px 20px;background:#eff6ff;border-left:4px solid #084298;border-radius:4px;">
          <p style="margin:0;color:#084298;font-size:13px;font-weight:600;">💳 Please contact us at reservations@grandvista.com or call +63 88 123 4567 to complete your payment.</p>
        </div>
        {'<p style="margin-top:16px;color:#666;font-size:13px;">Staff note: ' + booking.get("staff_notes","") + '</p>' if booking.get("staff_notes") else ''}
    """
    return _send(guest_email, f'Prepayment Required — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#084298'))


def send_noshow_recorded(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#c0392b;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Missed Check-In</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, our records show that you did not check in for your reservation on {booking['check_in']}.</p>
        {details}
        <div style="margin-top:28px;padding:16px 20px;background:#fef3f2;border-left:4px solid #c0392b;border-radius:4px;">
          <p style="margin:0;color:#c0392b;font-size:13px;">Your reservation has been marked as a no-show. If this is an error, please contact us immediately.</p>
        </div>
    """
    return _send(guest_email, f'Missed Check-In — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#c0392b'))


def send_cancelled(guest_email: str, guest_name: str, booking: dict):
    details = _booking_details_table(booking)
    content = f"""
        <h2 style="color:#0d1b2a;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Booking Cancelled</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {guest_name}, your booking has been successfully cancelled as requested.</p>
        {details}
        <p style="margin-top:24px;color:#666;font-size:13px;">We hope to welcome you another time. Feel free to make a new reservation on our website.</p>
    """
    return _send(guest_email, f'Booking Cancelled — {HOTEL_NAME} #{booking["id"]}', _base_template(content, '#c9a84c'))


def send_welcome(email: str, name: str):
    content = f"""
        <h2 style="color:#0d1b2a;font-family:Georgia,serif;font-size:26px;margin:0 0 8px;">Welcome to Grand Vista Hotel</h2>
        <p style="color:#666;font-size:14px;margin:0 0 28px;">Dear {name}, your account has been created successfully. You can now search and book rooms online.</p>
        <div style="background:#f0faf4;border-left:4px solid #1a7a4a;border-radius:4px;padding:16px 20px;margin-bottom:24px;">
          <p style="margin:0;color:#1a7a4a;font-size:13px;font-weight:600;">✓ Account registered successfully.</p>
        </div>
        <p style="color:#666;font-size:13px;">If you did not create this account, please contact us immediately at reservations@grandvista.com.</p>
    """
    return _send(email, f'Welcome to {HOTEL_NAME}', _base_template(content, '#1a7a4a'))

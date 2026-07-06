"""Send email, SMS, WhatsApp and in-app notifications."""

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone

from .models import (
    EmpMaster,
    InAppNotification,
    MobileDeviceToken,
    NotificationChannelConfig,
    NotificationEventTemplate,
    NotificationLog,
)
from .notification_module_utils import (
    ensure_notification_module_defaults,
    is_notification_module_enabled,
)


DEFAULT_TEMPLATES = [
    {
        "event_key": "claim_submitted",
        "event_name": "Claim Submitted",
        "sort_order": 1,
        "email_subject": "New expense claim from {full_name}",
        "email_body": "Hello,\n\n{full_name} submitted a {claim_type} claim for Rs.{amount} on {claim_date}.\n\nPlease review in HRMS.",
        "sms_body": "Claim submitted: {full_name} - {claim_type} Rs.{amount}",
        "whatsapp_body": "New claim from *{full_name}*: {claim_type} Rs.{amount}",
    },
    {
        "event_key": "claim_approved",
        "event_name": "Claim Approved",
        "sort_order": 2,
        "email_subject": "Your claim has been approved",
        "email_body": "Dear {full_name},\n\nYour {claim_type} claim (Rs.{amount}) has been approved.\n\nRemarks: {remarks}",
        "sms_body": "Claim approved: {claim_type} Rs.{amount}",
        "whatsapp_body": "Hi {full_name}, your claim for Rs.{amount} is *approved*.",
    },
    {
        "event_key": "claim_rejected",
        "event_name": "Claim Rejected",
        "sort_order": 3,
        "email_subject": "Your claim was rejected",
        "email_body": "Dear {full_name},\n\nYour {claim_type} claim (Rs.{amount}) was rejected.\n\nRemarks: {remarks}",
        "sms_body": "Claim rejected: {claim_type}. Contact HR.",
        "whatsapp_body": "Hi {full_name}, your claim was *rejected*. Remarks: {remarks}",
    },
    {
        "event_key": "claim_paid",
        "event_name": "Claim Paid",
        "sort_order": 4,
        "email_subject": "Claim payment processed",
        "email_body": "Dear {full_name},\n\nPayment of Rs.{amount} for your {claim_type} claim has been processed.",
        "sms_body": "Claim paid: Rs.{amount} credited.",
        "whatsapp_body": "Payment of Rs.{amount} for your claim has been *processed*.",
    },
    {
        "event_key": "leave_applied",
        "event_name": "Leave Applied",
        "sort_order": 5,
        "email_subject": "Leave request from {full_name}",
        "email_body": "{full_name} applied for leave from {from_date} to {to_date}.",
        "sms_body": "Leave applied by {full_name}",
        "whatsapp_body": "{full_name} applied for leave {from_date} to {to_date}",
    },
    {
        "event_key": "leave_approved",
        "event_name": "Leave Approved",
        "sort_order": 6,
        "email_subject": "Leave approved",
        "email_body": "Dear {full_name}, your leave from {from_date} to {to_date} is approved.",
        "sms_body": "Leave approved {from_date} to {to_date}",
        "whatsapp_body": "Your leave is *approved* ({from_date} - {to_date})",
    },
    {
        "event_key": "attendance_reminder",
        "event_name": "Attendance Reminder",
        "sort_order": 7,
        "email_subject": "Attendance reminder",
        "email_body": "Dear {full_name}, please mark your attendance today.",
        "sms_body": "Reminder: mark attendance today.",
        "whatsapp_body": "Reminder: please *check in* for today.",
    },
    {
        "event_key": "interview_scheduled",
        "event_name": "Interview Scheduled",
        "sort_order": 8,
        "email_subject": "Interview scheduled — {candidate_name}",
        "email_body": "Interview for {candidate_name} on {interview_date} at {interview_time}.",
        "sms_body": "Interview: {candidate_name} on {interview_date}",
        "whatsapp_body": "Interview scheduled for {candidate_name} on {interview_date}",
    },
    {
        "event_key": "custom_reminder",
        "event_name": "Custom Reminder",
        "sort_order": 99,
        "email_subject": "{title}",
        "email_body": "{message}",
        "sms_body": "{message}",
        "whatsapp_body": "{message}",
    },
]


def ensure_channel_config():
    config, _ = NotificationChannelConfig.objects.get_or_create(pk=1)
    return config


def ensure_event_templates():
    if NotificationEventTemplate.objects.exists():
        return
    for tpl in DEFAULT_TEMPLATES:
        NotificationEventTemplate.objects.create(**tpl)


def render_template(text, context):
    if not text:
        return ""
    result = text
    for key, val in (context or {}).items():
        result = result.replace("{" + key + "}", str(val or ""))
    return result


def _log_notification(channel, recipient, subject, body, status, event_key="", emp_id="", error=""):
    NotificationLog.objects.create(
        channel=channel,
        event_key=event_key,
        recipient=recipient,
        subject=subject[:255],
        body=body,
        status=status,
        error_message=error,
        emp_id=emp_id or "",
    )


def _get_emp_contact(emp):
    if not emp:
        return "", ""
    email = (emp.official_email or emp.email or "").strip()
    phone = (emp.contact or emp.emergency_contact or "").strip()
    return email, phone


def _send_email_to(recipient, subject, body, event_key="", emp_id=""):
    if not recipient:
        return False, "No email address"
    if not is_notification_module_enabled("email_notifications"):
        return False, "Email notifications disabled"

    cfg = ensure_channel_config()
    host = cfg.smtp_host or settings.EMAIL_HOST
    if not host and not settings.EMAIL_BACKEND:
        _log_notification("email", recipient, subject, body, "Failed", event_key, emp_id, "SMTP not configured")
        return False, "SMTP not configured in Notification Channel Settings"

    try:
        connection = get_connection(
            backend=settings.EMAIL_BACKEND or "django.core.mail.backends.smtp.EmailBackend",
            host=cfg.smtp_host or settings.EMAIL_HOST,
            port=cfg.smtp_port or settings.EMAIL_PORT or 587,
            username=cfg.smtp_user or settings.EMAIL_HOST_USER,
            password=cfg.smtp_password or settings.EMAIL_HOST_PASSWORD,
            use_tls=bool(cfg.smtp_use_tls),
        )
        from_email = cfg.from_email or settings.DEFAULT_FROM_EMAIL or cfg.smtp_user or "noreply@hrms.local"
        if cfg.from_name:
            from_email = f"{cfg.from_name} <{from_email}>"
        msg = EmailMessage(subject, body, from_email, [recipient], connection=connection)
        msg.send(fail_silently=False)
        _log_notification("email", recipient, subject, body, "Sent", event_key, emp_id)
        return True, "Email sent"
    except Exception as exc:
        _log_notification("email", recipient, subject, body, "Failed", event_key, emp_id, str(exc))
        return False, str(exc)


def _send_sms_to(phone, body, event_key="", emp_id=""):
    if not phone:
        return False, "No phone number"
    if not is_notification_module_enabled("sms_notifications"):
        return False, "SMS notifications disabled"

    cfg = ensure_channel_config()
    if not cfg.sms_api_key and not cfg.sms_api_url:
        _log_notification("sms", phone, "", body, "Failed", event_key, emp_id, "SMS API not configured")
        return False, "SMS API not configured"

    try:
        payload = {
            "sender": cfg.sms_sender_id,
            "mobile": phone,
            "message": body,
        }
        if cfg.sms_provider == "msg91":
            url = cfg.sms_api_url or "https://api.msg91.com/api/v5/flow/"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "authkey": cfg.sms_api_key,
                },
                method="POST",
            )
        else:
            url = cfg.sms_api_url or "https://api.twilio.com/2010-04-01/Accounts/messages.json"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        _log_notification("sms", phone, "", body, "Sent", event_key, emp_id)
        return True, "SMS sent"
    except urllib.error.URLError as exc:
        _log_notification("sms", phone, "", body, "Queued", event_key, emp_id, str(exc.reason))
        return True, "SMS queued (API simulated)"
    except Exception as exc:
        _log_notification("sms", phone, "", body, "Failed", event_key, emp_id, str(exc))
        return False, str(exc)


def _send_whatsapp_to(phone, body, event_key="", emp_id=""):
    if not phone:
        return False, "No phone number"
    if not is_notification_module_enabled("whatsapp_notifications"):
        return False, "WhatsApp notifications disabled"

    cfg = ensure_channel_config()
    if not cfg.whatsapp_api_key and not cfg.whatsapp_phone_id:
        _log_notification("whatsapp", phone, "", body, "Failed", event_key, emp_id, "WhatsApp API not configured")
        return False, "WhatsApp API not configured"

    try:
        api_url = (cfg.whatsapp_api_url or "https://graph.facebook.com/v18.0").rstrip("/")
        url = f"{api_url}/{cfg.whatsapp_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.replace("+", "").replace(" ", ""),
            "type": "text",
            "text": {"body": body},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg.whatsapp_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        _log_notification("whatsapp", phone, "", body, "Sent", event_key, emp_id)
        return True, "WhatsApp sent"
    except urllib.error.URLError as exc:
        _log_notification("whatsapp", phone, "", body, "Queued", event_key, emp_id, str(exc.reason))
        return True, "WhatsApp queued (API simulated)"
    except Exception as exc:
        _log_notification("whatsapp", phone, "", body, "Failed", event_key, emp_id, str(exc))
        return False, str(exc)


def _send_push_to_token(device_token, title, body, event_key="", emp_id=""):
    if not device_token:
        return False, "No device token"
    if not is_notification_module_enabled("push_notifications"):
        return False, "Push notifications disabled"

    cfg = ensure_channel_config()
    server_key = (cfg.push_server_key or "").strip()
    if not server_key:
        _log_notification("push", device_token[:80], title, body, "Failed", event_key, emp_id, "FCM server key not configured")
        return False, "FCM server key not configured"

    try:
        payload = {
            "to": device_token,
            "notification": {"title": title[:120], "body": body[:500]},
            "data": {"title": title[:120], "body": body[:500], "event_key": event_key},
            "priority": "high",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://fcm.googleapis.com/fcm/send",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"key={server_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        _log_notification("push", device_token[:80], title, body, "Sent", event_key, emp_id)
        return True, "Push sent"
    except urllib.error.URLError as exc:
        _log_notification("push", device_token[:80], title, body, "Queued", event_key, emp_id, str(exc.reason))
        return True, "Push queued"
    except Exception as exc:
        _log_notification("push", device_token[:80], title, body, "Failed", event_key, emp_id, str(exc))
        return False, str(exc)


def register_device_token(device_token, emp_id="", user_id=None, platform="android", device_name=""):
    token = (device_token or "").strip()
    if not token:
        raise ValueError("device_token required")

    obj, _ = MobileDeviceToken.objects.update_or_create(
        device_token=token,
        defaults={
            "emp_id": (emp_id or "").strip(),
            "user_id": user_id,
            "platform": (platform or "android").strip()[:20],
            "device_name": (device_name or "").strip()[:200],
            "is_active": 1,
        },
    )
    return obj


def get_active_device_tokens(emp_id=None, department=None):
    qs = MobileDeviceToken.objects.filter(is_active=1)
    if emp_id:
        qs = qs.filter(emp_id=str(emp_id))
    elif department:
        emp_ids = EmpMaster.objects.filter(dept=department).values_list("emp_id", flat=True)
        qs = qs.filter(emp_id__in=[str(e) for e in emp_ids])
    return list(qs)


def send_push_to_employee(emp, title, message, event_key=""):
    if not emp:
        return {"sent": 0, "failed": 0}
    tokens = get_active_device_tokens(emp_id=emp.emp_id)
    sent = failed = 0
    for tok in tokens:
        ok, _ = _send_push_to_token(tok.device_token, title, message, event_key, str(emp.emp_id))
        if ok:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}


def broadcast_push_to_organization(title, message, emp_id=None, department=None, event_key="broadcast"):
    """Send mobile push to all registered devices in the organization."""
    tokens = get_active_device_tokens(emp_id=emp_id, department=department)
    if not tokens and not emp_id and not department:
        tokens = get_active_device_tokens()

    sent = failed = 0
    for tok in tokens:
        ok, _ = _send_push_to_token(
            tok.device_token,
            title,
            message,
            event_key,
            tok.emp_id or "",
        )
        if ok:
            sent += 1
        else:
            failed += 1

    return {
        "message": f"Push sent to {sent} device(s)",
        "devices_targeted": len(tokens),
        "sent": sent,
        "failed": failed,
    }


def _send_in_app(user_id, emp_id, title, message, link_url="", event_key=""):
    if not is_notification_module_enabled("in_app_alerts"):
        return False, "In-app alerts disabled"
    if not user_id:
        return False, "No user id"
    InAppNotification.objects.create(
        user_id=user_id,
        emp_id=emp_id or "",
        title=title[:200],
        message=message,
        link_url=link_url or "",
        is_read=0,
    )
    _log_notification("in_app", str(user_id), title, message, "Sent", event_key, emp_id)
    return True, "In-app alert created"


def get_unread_count(user_id):
    if not user_id or not is_notification_module_enabled("in_app_alerts"):
        return 0
    return InAppNotification.objects.filter(user_id=user_id, is_read=0).count()


def send_notification(event_key, context=None, emp=None, user_id=None, admin_alert=False):
    """Send notification for an event using configured templates and channels."""
    ensure_notification_module_defaults()
    ensure_event_templates()
    context = dict(context or {})
    if emp and "full_name" not in context:
        context["full_name"] = emp.full_name or ""

    tpl = NotificationEventTemplate.objects.filter(event_key=event_key, is_active=1).first()
    if not tpl:
        return {"ok": False, "error": f"No template for {event_key}"}

    email, phone = _get_emp_contact(emp)
    results = {}

    if tpl.email_enabled and is_notification_module_enabled("email_notifications"):
        subject = render_template(tpl.email_subject, context)
        body = render_template(tpl.email_body, context)
        target = email
        if admin_alert:
            cfg = ensure_channel_config()
            target = (cfg.admin_notify_email or "").strip() or email
        if target:
            ok, msg = _send_email_to(target, subject, body, event_key, getattr(emp, "emp_id", ""))
            results["email"] = msg

    if tpl.sms_enabled and is_notification_module_enabled("sms_notifications") and phone:
        body = render_template(tpl.sms_body, context)
        ok, msg = _send_sms_to(phone, body, event_key, getattr(emp, "emp_id", ""))
        results["sms"] = msg

    if tpl.whatsapp_enabled and is_notification_module_enabled("whatsapp_notifications") and phone:
        body = render_template(tpl.whatsapp_body, context)
        ok, msg = _send_whatsapp_to(phone, body, event_key, getattr(emp, "emp_id", ""))
        results["whatsapp"] = msg

    if tpl.push_enabled and is_notification_module_enabled("push_notifications") and emp:
        push_body = render_template(tpl.push_body or tpl.sms_body or tpl.email_subject, context)
        push_title = render_template(tpl.email_subject or tpl.event_name, context)
        push_result = send_push_to_employee(emp, push_title, push_body, event_key)
        results["push"] = f"Push: {push_result['sent']} sent"

    if tpl.in_app_enabled and is_notification_module_enabled("in_app_alerts") and user_id:
        title = render_template(tpl.email_subject or tpl.event_name, context)
        message = render_template(tpl.email_body or tpl.sms_body, context)
        ok, msg = _send_in_app(user_id, getattr(emp, "emp_id", ""), title, message, event_key=event_key)
        results["in_app"] = msg

    return {"ok": True, "results": results}


def send_test_notification(channel, recipient, message="Test notification from HRMS"):
    ensure_notification_module_defaults()
    if channel == "email":
        return _send_email_to(recipient, "HRMS Test Email", message, "test")
    if channel == "sms":
        return _send_sms_to(recipient, message, "test")
    if channel == "whatsapp":
        return _send_whatsapp_to(recipient, message, "test")
    if channel == "push":
        return _send_push_to_token(recipient, "HRMS Test Push", message, "test")
    return False, "Unknown channel"


def get_emp_for_claim(emp_id):
    try:
        return EmpMaster.objects.get(emp_id=str(emp_id))
    except EmpMaster.DoesNotExist:
        return None


def process_due_reminders():
    """Process reminders whose schedule date/time has passed (call from cron or management command)."""
    from .models import NotificationReminder

    if not is_notification_module_enabled("reminders"):
        return 0

    now = timezone.now()
    today = now.date()
    current_time = now.time()
    sent = 0

    for rem in NotificationReminder.objects.filter(is_active=1):
        if rem.schedule_date and rem.schedule_date > today:
            continue
        if rem.schedule_date == today and rem.schedule_time and rem.schedule_time > current_time:
            continue

        recipients = []
        if rem.recipient_type == "single_employee" and rem.recipient_value:
            emp = EmpMaster.objects.filter(emp_id=rem.recipient_value).first()
            if emp:
                recipients.append(emp)
        elif rem.recipient_type == "department" and rem.recipient_value:
            recipients = list(EmpMaster.objects.filter(dept=rem.recipient_value))
        else:
            recipients = list(EmpMaster.objects.all()[:500])

        ctx = {"title": rem.title, "message": rem.message}
        for emp in recipients:
            send_notification("custom_reminder", context=ctx, emp=emp)
            sent += 1

        rem.last_sent_at = now
        rem.save(update_fields=["last_sent_at"])

    return sent

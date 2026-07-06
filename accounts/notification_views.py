from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    EmpMaster,
    InAppNotification,
    MobileDeviceToken,
    NotificationChannelConfig,
    NotificationEventTemplate,
    NotificationLog,
    NotificationModuleConfig,
    NotificationReminder,
)
from .notification_module_utils import (
    MODULE_KEYS,
    NOTIFICATION_MODULES,
    any_notification_sidebar_visible,
    ensure_notification_module_defaults,
    get_notification_modules_map,
    is_notification_module_enabled,
    notification_module_required,
)
from .notification_service import (
    broadcast_push_to_organization,
    ensure_channel_config,
    ensure_event_templates,
    get_unread_count,
    send_test_notification,
    send_notification,
)


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def notification_module_settings(request):
    ensure_notification_module_defaults()
    config = NotificationModuleConfig.objects.get(pk=1)

    if request.method == "POST":
        for key in MODULE_KEYS:
            setattr(config, key, 1 if request.POST.get(key) else 0)
        config.notification_settings = 1
        config.save()
        messages.success(request, "Notification module settings saved.")
        return redirect("notification_module_settings")

    modules = []
    for mod in NOTIFICATION_MODULES:
        modules.append({**mod, "enabled": is_notification_module_enabled(mod["key"])})

    return render(
        request,
        "accounts/notification_module_settings.html",
        {"config": config, "modules": modules},
    )


@login_required(login_url="login")
@notification_module_required
@permission_required("accounts.change_empmaster", raise_exception=True)
def notification_channel_settings(request):
    cfg = ensure_channel_config()

    if request.method == "POST":
        cfg.smtp_host = request.POST.get("smtp_host", "").strip()
        cfg.smtp_port = int(request.POST.get("smtp_port", "587") or 587)
        cfg.smtp_user = request.POST.get("smtp_user", "").strip()
        if request.POST.get("smtp_password"):
            cfg.smtp_password = request.POST.get("smtp_password", "").strip()
        cfg.smtp_use_tls = 1 if request.POST.get("smtp_use_tls") else 0
        cfg.from_email = request.POST.get("from_email", "").strip()
        cfg.from_name = request.POST.get("from_name", "").strip()
        cfg.sms_provider = request.POST.get("sms_provider", "msg91").strip()
        cfg.sms_api_key = request.POST.get("sms_api_key", "").strip()
        cfg.sms_api_secret = request.POST.get("sms_api_secret", "").strip()
        cfg.sms_sender_id = request.POST.get("sms_sender_id", "").strip()
        cfg.sms_api_url = request.POST.get("sms_api_url", "").strip()
        cfg.whatsapp_provider = request.POST.get("whatsapp_provider", "meta").strip()
        cfg.whatsapp_api_key = request.POST.get("whatsapp_api_key", "").strip()
        cfg.whatsapp_api_secret = request.POST.get("whatsapp_api_secret", "").strip()
        cfg.whatsapp_phone_id = request.POST.get("whatsapp_phone_id", "").strip()
        cfg.whatsapp_api_url = request.POST.get("whatsapp_api_url", "").strip()
        cfg.push_provider = request.POST.get("push_provider", "fcm").strip()
        cfg.push_server_key = request.POST.get("push_server_key", "").strip()
        cfg.push_project_id = request.POST.get("push_project_id", "").strip()
        cfg.push_sender_id = request.POST.get("push_sender_id", "").strip()
        cfg.admin_notify_email = request.POST.get("admin_notify_email", "").strip()
        cfg.save()
        messages.success(request, "Channel settings saved.")
        return redirect("notification_channel_settings")

    return render(
        request,
        "accounts/notification_channel_settings.html",
        {"cfg": cfg, "modules": get_notification_modules_map()},
    )


@login_required(login_url="login")
@notification_module_required
def notification_center(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("my_notifications")

    ensure_event_templates()
    logs = NotificationLog.objects.all()[:20]
    stats = NotificationLog.objects.values("channel").annotate(total=Count("id"))
    channel_stats = {row["channel"]: row["total"] for row in stats}
    sent_today = NotificationLog.objects.filter(
        created_at__date=timezone.now().date(), status="Sent"
    ).count()

    if request.method == "POST" and request.user.has_perm("accounts.change_empmaster"):
        action = request.POST.get("action", "test")
        if action == "broadcast_push":
            title = request.POST.get("push_title", "").strip()
            message = request.POST.get("push_message", "").strip()
            department = request.POST.get("push_department", "").strip() or None
            if not title or not message:
                messages.error(request, "Push title and message are required.")
            elif not is_notification_module_enabled("push_notifications"):
                messages.error(request, "Mobile push is disabled in Notification Settings.")
            else:
                result = broadcast_push_to_organization(
                    title=title,
                    message=message,
                    department=department,
                    event_key="dashboard_broadcast",
                )
                messages.success(request, result["message"])
            return redirect("notification_center")

        channel = request.POST.get("test_channel", "email")
        recipient = request.POST.get("test_recipient", "").strip()
        message = request.POST.get("test_message", "Test from HRMS Notification Center").strip()
        ok, msg = send_test_notification(channel, recipient, message)
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect("notification_center")

    push_devices = MobileDeviceToken.objects.filter(is_active=1).count()
    push_sent = NotificationLog.objects.filter(channel="push", status="Sent").count()

    return render(
        request,
        "accounts/notification_center.html",
        {
            "logs": logs,
            "channel_stats": channel_stats,
            "sent_today": sent_today,
            "modules": get_notification_modules_map(),
            "template_count": NotificationEventTemplate.objects.filter(is_active=1).count(),
            "reminder_count": NotificationReminder.objects.filter(is_active=1).count(),
            "push_devices": push_devices,
            "push_sent_total": push_sent,
            "push_enabled": is_notification_module_enabled("push_notifications"),
            "departments": (
                EmpMaster.objects.exclude(dept__isnull=True)
                .exclude(dept="")
                .values_list("dept", flat=True)
                .distinct()
            ),
            "recent_devices": MobileDeviceToken.objects.filter(is_active=1)[:10],
        },
    )


@login_required(login_url="login")
@notification_module_required
@permission_required("accounts.change_empmaster", raise_exception=True)
def mobile_push_dashboard(request):
    if not is_notification_module_enabled("push_notifications"):
        messages.error(request, "Mobile push is disabled. Enable it in Notification Settings.")
        return redirect("notification_module_settings")

    cfg = ensure_channel_config()
    devices = MobileDeviceToken.objects.filter(is_active=1)
    logs = NotificationLog.objects.filter(channel="push")[:50]

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "broadcast":
            title = request.POST.get("title", "").strip()
            message = request.POST.get("message", "").strip()
            department = request.POST.get("department", "").strip() or None
            if not title or not message:
                messages.error(request, "Title and message are required.")
            else:
                result = broadcast_push_to_organization(
                    title=title, message=message, department=department
                )
                messages.success(request, result["message"])
            return redirect("mobile_push_dashboard")

    api_base = request.build_absolute_uri("/api/")
    return render(
        request,
        "accounts/mobile_push_dashboard.html",
        {
            "cfg": cfg,
            "devices": devices[:100],
            "device_count": devices.count(),
            "logs": logs,
            "departments": (
                EmpMaster.objects.exclude(dept__isnull=True)
                .exclude(dept="")
                .values_list("dept", flat=True)
                .distinct()
            ),
            "api_base_url": api_base,
        },
    )


@login_required(login_url="login")
@notification_module_required
@permission_required("accounts.change_empmaster", raise_exception=True)
def notification_templates(request):
    ensure_event_templates()
    templates = NotificationEventTemplate.objects.all()

    if request.method == "POST":
        for tpl in templates:
            tpl.email_enabled = 1 if request.POST.get(f"email_{tpl.id}") else 0
            tpl.sms_enabled = 1 if request.POST.get(f"sms_{tpl.id}") else 0
            tpl.whatsapp_enabled = 1 if request.POST.get(f"whatsapp_{tpl.id}") else 0
            tpl.in_app_enabled = 1 if request.POST.get(f"in_app_{tpl.id}") else 0
            tpl.email_subject = request.POST.get(f"subject_{tpl.id}", tpl.email_subject).strip()
            tpl.email_body = request.POST.get(f"email_body_{tpl.id}", tpl.email_body).strip()
            tpl.sms_body = request.POST.get(f"sms_body_{tpl.id}", tpl.sms_body).strip()
            tpl.whatsapp_body = request.POST.get(
                f"whatsapp_body_{tpl.id}", tpl.whatsapp_body
            ).strip()
            tpl.is_active = 1 if request.POST.get(f"active_{tpl.id}") else 0
            tpl.save()
        messages.success(request, "Alert templates saved.")
        return redirect("notification_templates")

    return render(
        request,
        "accounts/notification_templates.html",
        {"templates": templates},
    )


@login_required(login_url="login")
@notification_module_required
def notification_reminders(request):
    if not is_notification_module_enabled("reminders"):
        messages.error(request, "Reminders module is disabled.")
        return redirect("notification_module_settings")

    reminders = NotificationReminder.objects.all()
    departments = (
        EmpMaster.objects.exclude(dept__isnull=True)
        .exclude(dept="")
        .values_list("dept", flat=True)
        .distinct()
    )

    if request.method == "POST":
        if not request.user.has_perm("accounts.change_empmaster"):
            messages.error(request, "Permission denied.")
            return redirect("notification_reminders")

        action = request.POST.get("action", "add")
        if action == "delete":
            rem = get_object_or_404(NotificationReminder, id=request.POST.get("reminder_id"))
            rem.delete()
            messages.success(request, "Reminder deleted.")
            return redirect("notification_reminders")

        if action == "toggle":
            rem = get_object_or_404(NotificationReminder, id=request.POST.get("reminder_id"))
            rem.is_active = 0 if rem.is_active else 1
            rem.save()
            return redirect("notification_reminders")

        title = request.POST.get("title", "").strip()
        message = request.POST.get("message", "").strip()
        if not title or not message:
            messages.error(request, "Title and message are required.")
            return redirect("notification_reminders")

        schedule_date = request.POST.get("schedule_date") or None
        schedule_time = request.POST.get("schedule_time") or None
        NotificationReminder.objects.create(
            title=title,
            message=message,
            channel=request.POST.get("channel", "all"),
            recipient_type=request.POST.get("recipient_type", "all_employees"),
            recipient_value=request.POST.get("recipient_value", "").strip(),
            schedule_date=schedule_date,
            schedule_time=schedule_time,
            repeat_type=request.POST.get("repeat_type", "none"),
            is_active=1,
            created_by=request.user.get_full_name() or request.user.username,
        )
        messages.success(request, "Reminder created.")
        return redirect("notification_reminders")

    return render(
        request,
        "accounts/notification_reminders.html",
        {"reminders": reminders, "departments": departments},
    )


@login_required(login_url="login")
@notification_module_required
def notification_log(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect("home")

    channel_filter = request.GET.get("channel", "")
    logs = NotificationLog.objects.all()
    if channel_filter:
        logs = logs.filter(channel=channel_filter)

    return render(
        request,
        "accounts/notification_log.html",
        {"logs": logs[:200], "channel_filter": channel_filter},
    )


@login_required(login_url="login")
def my_notifications(request):
    if not is_notification_module_enabled("in_app_alerts"):
        messages.error(request, "In-app alerts are disabled.")
        return redirect("home")

    notes = InAppNotification.objects.filter(user_id=request.user.id)
    unread = notes.filter(is_read=0).count()
    return render(
        request,
        "accounts/my_notifications.html",
        {"notifications": notes[:100], "unread_count": unread},
    )


@login_required(login_url="login")
def notification_mark_read(request, id):
    note = get_object_or_404(InAppNotification, id=id, user_id=request.user.id)
    note.is_read = 1
    note.save(update_fields=["is_read"])
    if note.link_url:
        return redirect(note.link_url)
    return redirect("my_notifications")


@login_required(login_url="login")
def notification_mark_all_read(request):
    InAppNotification.objects.filter(user_id=request.user.id, is_read=0).update(is_read=1)
    messages.success(request, "All notifications marked as read.")
    return redirect("my_notifications")

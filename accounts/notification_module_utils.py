"""Notification module on/off configuration."""

from .models import NotificationModuleConfig

NOTIFICATION_MODULES = [
    {
        "key": "email_notifications",
        "name": "Email Notifications",
        "desc": "Send alerts and reminders via SMTP email",
        "icon": "fas fa-envelope",
        "url_name": "notification_channel_settings",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "sms_notifications",
        "name": "SMS Notifications",
        "desc": "Send SMS via MSG91, Twilio or custom API",
        "icon": "fas fa-sms",
        "url_name": "notification_channel_settings",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "whatsapp_notifications",
        "name": "WhatsApp Notifications",
        "desc": "Send WhatsApp messages via Meta / Twilio API",
        "icon": "fab fa-whatsapp",
        "url_name": "notification_channel_settings",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "push_notifications",
        "name": "Mobile Push Notifications",
        "desc": "FCM push alerts to all employees — Android & iOS app",
        "icon": "fas fa-mobile-alt",
        "url_name": "mobile_push_dashboard",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "in_app_alerts",
        "name": "In-App Alerts",
        "desc": "Notification bell and inbox inside HRMS portal",
        "icon": "fas fa-bell",
        "url_name": "my_notifications",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "reminders",
        "name": "Reminders & Scheduled Alerts",
        "desc": "Schedule birthday, attendance and custom reminders",
        "icon": "fas fa-clock",
        "url_name": "notification_reminders",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "notification_settings",
        "name": "Notification Settings",
        "desc": "Enable or disable notification channels for this organization",
        "icon": "fas fa-sliders-h",
        "url_name": "notification_module_settings",
        "show_in_hub": True,
        "show_in_sidebar": True,
        "always_on_hub": True,
    },
]

MODULE_KEYS = [m["key"] for m in NOTIFICATION_MODULES]


def ensure_notification_module_defaults():
    config, _ = NotificationModuleConfig.objects.get_or_create(pk=1)
    return config


def get_notification_module_config():
    ensure_notification_module_defaults()
    return NotificationModuleConfig.objects.filter(pk=1).first()


def is_notification_module_enabled(key):
    config = get_notification_module_config()
    if not config:
        return False
    return bool(getattr(config, key, 0))


def get_notification_modules_map():
    config = get_notification_module_config()
    return {
        m["key"]: is_notification_module_enabled(m["key"]) for m in NOTIFICATION_MODULES
    }


def any_notification_sidebar_visible():
    keys = (
        "email_notifications",
        "sms_notifications",
        "whatsapp_notifications",
        "push_notifications",
        "in_app_alerts",
        "reminders",
    )
    return any(is_notification_module_enabled(k) for k in keys)


def get_notification_hub_items():
    config = get_notification_module_config()
    items = []
    for mod in NOTIFICATION_MODULES:
        if not mod.get("show_in_hub"):
            continue
        if mod.get("always_on_hub") or is_notification_module_enabled(mod["key"]):
            items.append(
                {
                    "name": mod["name"],
                    "icon": mod["icon"],
                    "desc": mod["desc"],
                    "key": mod["key"],
                    "url_name": mod.get("url_name"),
                }
            )
    if any_notification_sidebar_visible() or is_notification_module_enabled(
        "notification_settings"
    ):
        items.insert(
            0,
            {
                "name": "Notification Center",
                "icon": "fas fa-bell",
                "desc": "Dashboard — logs, test send, templates",
                "key": "notification_center",
                "url_name": "notification_center",
            },
        )
        items.append(
            {
                "name": "Alert Templates",
                "icon": "fas fa-file-alt",
                "desc": "Customize email, SMS and WhatsApp message templates",
                "key": "notification_templates",
                "url_name": "notification_templates",
            }
        )
        items.append(
            {
                "name": "Notification Log",
                "icon": "fas fa-history",
                "desc": "History of sent emails, SMS and WhatsApp messages",
                "key": "notification_log",
                "url_name": "notification_log",
            }
        )
    return items


def get_notification_sidebar_items():
    if not any_notification_sidebar_visible():
        return []

    items = [
        {
            "name": "Notification Center",
            "url_name": "notification_center",
            "icon": "fas fa-bell",
        }
    ]
    if any(
        is_notification_module_enabled(k)
        for k in ("email_notifications", "sms_notifications", "whatsapp_notifications", "push_notifications")
    ):
        items.append(
            {
                "name": "Channel Settings",
                "url_name": "notification_channel_settings",
                "icon": "fas fa-plug",
            }
        )
    if is_notification_module_enabled("push_notifications"):
        items.append(
            {
                "name": "Mobile Push",
                "url_name": "mobile_push_dashboard",
                "icon": "fas fa-mobile-alt",
            }
        )
    if is_notification_module_enabled("reminders"):
        items.append(
            {
                "name": "Reminders",
                "url_name": "notification_reminders",
                "icon": "fas fa-clock",
            }
        )
    if is_notification_module_enabled("in_app_alerts"):
        items.append(
            {
                "name": "My Alerts",
                "url_name": "my_notifications",
                "icon": "fas fa-inbox",
            }
        )
    items.append(
        {
            "name": "Alert Templates",
            "url_name": "notification_templates",
            "icon": "fas fa-file-alt",
        }
    )
    items.append(
        {
            "name": "Sent Log",
            "url_name": "notification_log",
            "icon": "fas fa-history",
        }
    )
    if is_notification_module_enabled("notification_settings"):
        items.append(
            {
                "name": "Notification Settings",
                "url_name": "notification_module_settings",
                "icon": "fas fa-sliders-h",
            }
        )
    return items


def notification_module_required(view_func):
    from functools import wraps
    from django.contrib import messages
    from django.shortcuts import redirect

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not any_notification_sidebar_visible() and not is_notification_module_enabled(
            "notification_settings"
        ):
            messages.error(
                request, "Notification Center is disabled in Notification Settings."
            )
            if request.user.is_staff or request.user.is_superuser:
                return redirect("notification_module_settings")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper

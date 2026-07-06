from django.db import migrations, models


DEFAULT_TEMPLATES = [
    ("claim_submitted", "Claim Submitted", 1),
    ("claim_approved", "Claim Approved", 2),
    ("claim_rejected", "Claim Rejected", 3),
    ("claim_paid", "Claim Paid", 4),
    ("leave_applied", "Leave Applied", 5),
    ("leave_approved", "Leave Approved", 6),
    ("attendance_reminder", "Attendance Reminder", 7),
    ("interview_scheduled", "Interview Scheduled", 8),
    ("custom_reminder", "Custom Reminder", 99),
]


def seed_notification_data(apps, schema_editor):
    NotificationModuleConfig = apps.get_model("accounts", "NotificationModuleConfig")
    NotificationChannelConfig = apps.get_model("accounts", "NotificationChannelConfig")
    NotificationEventTemplate = apps.get_model("accounts", "NotificationEventTemplate")

    NotificationModuleConfig.objects.get_or_create(
        pk=1,
        defaults={
            "email_notifications": 0,
            "sms_notifications": 0,
            "whatsapp_notifications": 0,
            "in_app_alerts": 1,
            "reminders": 0,
            "notification_settings": 1,
        },
    )
    NotificationChannelConfig.objects.get_or_create(pk=1)

    if NotificationEventTemplate.objects.exists():
        return
    for key, name, order in DEFAULT_TEMPLATES:
        NotificationEventTemplate.objects.create(
            event_key=key,
            event_name=name,
            sort_order=order,
            email_enabled=1,
            in_app_enabled=1,
            email_subject=f"HRMS Alert — {name}",
            email_body=f"This is an automated alert for: {name}.",
            sms_body=f"HRMS: {name}",
            whatsapp_body=f"HRMS alert: {name}",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0032_recruitment_integration"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationModuleConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_notifications", models.IntegerField(default=0)),
                ("sms_notifications", models.IntegerField(default=0)),
                ("whatsapp_notifications", models.IntegerField(default=0)),
                ("in_app_alerts", models.IntegerField(default=1)),
                ("reminders", models.IntegerField(default=0)),
                ("notification_settings", models.IntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "notification_module_config",
                "verbose_name": "Notification Module Config",
            },
        ),
        migrations.CreateModel(
            name="NotificationChannelConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("smtp_host", models.CharField(blank=True, default="", max_length=255)),
                ("smtp_port", models.IntegerField(default=587)),
                ("smtp_user", models.CharField(blank=True, default="", max_length=255)),
                ("smtp_password", models.CharField(blank=True, default="", max_length=255)),
                ("smtp_use_tls", models.IntegerField(default=1)),
                ("from_email", models.CharField(blank=True, default="", max_length=255)),
                ("from_name", models.CharField(blank=True, default="", max_length=255)),
                ("sms_provider", models.CharField(blank=True, default="msg91", max_length=50)),
                ("sms_api_key", models.CharField(blank=True, default="", max_length=500)),
                ("sms_api_secret", models.CharField(blank=True, default="", max_length=500)),
                ("sms_sender_id", models.CharField(blank=True, default="", max_length=20)),
                ("sms_api_url", models.CharField(blank=True, default="", max_length=500)),
                ("whatsapp_provider", models.CharField(blank=True, default="meta", max_length=50)),
                ("whatsapp_api_key", models.CharField(blank=True, default="", max_length=500)),
                ("whatsapp_api_secret", models.CharField(blank=True, default="", max_length=500)),
                ("whatsapp_phone_id", models.CharField(blank=True, default="", max_length=100)),
                ("whatsapp_api_url", models.CharField(blank=True, default="https://graph.facebook.com/v18.0", max_length=500)),
                ("admin_notify_email", models.CharField(blank=True, default="", max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notification_channel_config"},
        ),
        migrations.CreateModel(
            name="NotificationEventTemplate",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_key", models.CharField(max_length=80, unique=True)),
                ("event_name", models.CharField(max_length=150)),
                ("email_enabled", models.IntegerField(default=1)),
                ("sms_enabled", models.IntegerField(default=0)),
                ("whatsapp_enabled", models.IntegerField(default=0)),
                ("in_app_enabled", models.IntegerField(default=1)),
                ("email_subject", models.CharField(blank=True, default="", max_length=255)),
                ("email_body", models.TextField(blank=True, default="")),
                ("sms_body", models.CharField(blank=True, default="", max_length=500)),
                ("whatsapp_body", models.TextField(blank=True, default="")),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "notification_event_template",
                "ordering": ["sort_order", "event_name"],
            },
        ),
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(max_length=20)),
                ("event_key", models.CharField(blank=True, default="", max_length=80)),
                ("recipient", models.CharField(max_length=255)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                ("body", models.TextField(blank=True, default="")),
                ("status", models.CharField(default="Pending", max_length=20)),
                ("error_message", models.TextField(blank=True, default="")),
                ("emp_id", models.CharField(blank=True, default="", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "notification_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NotificationReminder",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("channel", models.CharField(default="all", max_length=30)),
                ("recipient_type", models.CharField(default="all_employees", max_length=30)),
                ("recipient_value", models.CharField(blank=True, default="", max_length=255)),
                ("schedule_date", models.DateField(blank=True, null=True)),
                ("schedule_time", models.TimeField(blank=True, null=True)),
                ("repeat_type", models.CharField(default="none", max_length=20)),
                ("is_active", models.IntegerField(default=1)),
                ("last_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "notification_reminder",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="InAppNotification",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField()),
                ("emp_id", models.CharField(blank=True, default="", max_length=50)),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("link_url", models.CharField(blank=True, default="", max_length=500)),
                ("is_read", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "in_app_notification",
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(seed_notification_data, migrations.RunPython.noop),
    ]

# Mobile push notifications (FCM)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0038_extra_ot_slab_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationmoduleconfig",
            name="push_notifications",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificationchannelconfig",
            name="push_provider",
            field=models.CharField(blank=True, default="fcm", max_length=50),
        ),
        migrations.AddField(
            model_name="notificationchannelconfig",
            name="push_server_key",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="notificationchannelconfig",
            name="push_project_id",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="notificationchannelconfig",
            name="push_sender_id",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="notificationeventtemplate",
            name="push_enabled",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificationeventtemplate",
            name="push_body",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.CreateModel(
            name="MobileDeviceToken",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(blank=True, null=True)),
                ("emp_id", models.CharField(blank=True, default="", max_length=50)),
                ("device_token", models.CharField(max_length=512, unique=True)),
                ("platform", models.CharField(blank=True, default="android", max_length=20)),
                ("device_name", models.CharField(blank=True, default="", max_length=200)),
                ("is_active", models.IntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "mobile_device_token",
                "ordering": ["-updated_at"],
            },
        ),
    ]

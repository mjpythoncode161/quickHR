from django.db import migrations, models
import django.db.models.deletion


def seed_recruitment_integration(apps, schema_editor):
    HrModuleConfig = apps.get_model("accounts", "HrModuleConfig")
    HrModuleConfig.objects.filter(pk=1).update(recruitment=0)

    RecruitmentSettings = apps.get_model("accounts", "RecruitmentSettings")
    RecruitmentPlatform = apps.get_model("accounts", "RecruitmentPlatform")

    settings_obj, _ = RecruitmentSettings.objects.get_or_create(
        pk=1,
        defaults={"auto_receive_applications": 1},
    )
    if not settings_obj.webhook_token:
        import secrets

        settings_obj.webhook_token = secrets.token_urlsafe(32)
        settings_obj.save()

    if RecruitmentPlatform.objects.exists():
        return

    platforms = [
        ("linkedin", "LinkedIn Jobs", "https://api.linkedin.com/v2/jobs", 1),
        ("naukri", "Naukri.com", "https://api.naukri.com/jobposting/v1", 2),
        ("indeed", "Indeed", "https://apis.indeed.com/ads/v1", 3),
        ("monster", "Monster", "https://api.monster.com/v1/jobs", 4),
        ("glassdoor", "Glassdoor", "https://api.glassdoor.com/api/api.htm", 5),
        ("foundit", "Foundit (Monster India)", "https://api.foundit.in/v1/jobs", 6),
        ("internshala", "Internshala", "https://api.internshala.com/v1", 7),
        ("shine", "Shine.com", "https://api.shine.com/v1/jobs", 8),
        ("custom", "Custom / Other API", "", 99),
    ]
    for key, name, url, order in platforms:
        RecruitmentPlatform.objects.create(
            platform_key=key,
            platform_name=name,
            api_url=url,
            sort_order=order,
            is_enabled=0,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0031_claim_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="hrmoduleconfig",
            name="recruitment",
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name="RecruitmentSettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("webhook_token", models.CharField(blank=True, default="", max_length=128)),
                ("auto_receive_applications", models.IntegerField(default=1)),
                ("notify_email", models.CharField(blank=True, default="", max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "recruitment_settings"},
        ),
        migrations.CreateModel(
            name="RecruitmentPlatform",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform_key", models.CharField(max_length=50, unique=True)),
                ("platform_name", models.CharField(max_length=100)),
                ("is_enabled", models.IntegerField(default=0)),
                ("api_key", models.CharField(blank=True, default="", max_length=500)),
                ("api_secret", models.CharField(blank=True, default="", max_length=500)),
                ("company_id", models.CharField(blank=True, default="", max_length=255)),
                ("api_url", models.CharField(blank=True, default="", max_length=500)),
                ("auto_post_jobs", models.IntegerField(default=0)),
                ("sort_order", models.IntegerField(default=0)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "recruitment_platform", "ordering": ["sort_order", "platform_name"]},
        ),
        migrations.CreateModel(
            name="JobPlatformPost",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_job_id", models.CharField(blank=True, default="", max_length=255)),
                ("external_url", models.CharField(blank=True, default="", max_length=500)),
                ("status", models.CharField(default="Pending", max_length=30)),
                ("sync_message", models.TextField(blank=True, default="")),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="platform_posts", to="accounts.jobposting")),
                ("platform", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_posts", to="accounts.recruitmentplatform")),
            ],
            options={"db_table": "job_platform_post", "unique_together": {("job", "platform")}},
        ),
        migrations.RunPython(seed_recruitment_integration, migrations.RunPython.noop),
    ]

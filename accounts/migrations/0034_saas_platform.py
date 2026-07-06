from django.db import migrations, models


def seed_saas(apps, schema_editor):
    SaasPlatformConfig = apps.get_model("accounts", "SaasPlatformConfig")
    SaasPricingPlan = apps.get_model("accounts", "SaasPricingPlan")
    SaasProduct = apps.get_model("accounts", "SaasProduct")
    SaasService = apps.get_model("accounts", "SaasService")

    SaasPlatformConfig.objects.get_or_create(
        pk=1,
        defaults={
            "platform_name": "QuickHR",
            "tagline": "Complete HRMS SaaS for modern organizations",
            "hero_title": "All-in-One HRMS Cloud Platform",
            "hero_subtitle": (
                "Attendance, payroll, recruitment, claims, notifications & more — "
                "one platform for your entire workforce."
            ),
            "about_body": (
                "QuickHR is a cloud HRMS built for Indian businesses. Automate HR operations, "
                "empower employees with self-service, and scale with flexible SaaS pricing."
            ),
            "footer_text": "© QuickHR HRMS. All rights reserved.",
        },
    )

    if not SaasPricingPlan.objects.exists():
        plans = [
            ("starter", "Starter", 999, 9990, 25, 1),
            ("professional", "Professional", 2499, 24990, 100, 2),
            ("enterprise", "Enterprise", 4999, 49990, 500, 3),
        ]
        for key, name, m, y, emp, order in plans:
            SaasPricingPlan.objects.create(
                plan_key=key,
                plan_name=name,
                price_monthly=m,
                price_yearly=y,
                max_employees=emp,
                sort_order=order,
                is_popular=1 if key == "professional" else 0,
                description=f"Up to {emp} employees",
                features=f"Up to {emp} employees\nAll core HR modules\nCloud hosting\nSupport included",
            )

    if not SaasProduct.objects.exists():
        items = [
            ("hrms-core", "HRMS Core", "fas fa-users", 1),
            ("payroll", "Payroll", "fas fa-calculator", 2),
            ("recruitment", "Recruitment", "fas fa-user-tie", 3),
        ]
        for slug, title, icon, order in items:
            SaasProduct.objects.create(
                slug=slug, title=title, icon=icon, sort_order=order, short_desc=title, description=title
            )

    if not SaasService.objects.exists():
        for title, order in [("Implementation", 1), ("Training", 2), ("Support", 3)]:
            SaasService.objects.create(title=title, sort_order=order, short_desc=title, description=title)


class Migration(migrations.Migration):

    dependencies = [("accounts", "0033_notification_center")]

    operations = [
        migrations.CreateModel(
            name="SaasPlatformConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform_name", models.CharField(default="QuickHR", max_length=150)),
                ("tagline", models.CharField(default="Complete HRMS for modern organizations", max_length=255)),
                ("hero_title", models.CharField(default="All-in-One HRMS SaaS Platform", max_length=255)),
                ("hero_subtitle", models.TextField(default="Attendance, payroll, recruitment, claims & more — one cloud platform for your entire workforce.")),
                ("about_title", models.CharField(default="About QuickHR", max_length=200)),
                ("about_body", models.TextField(blank=True, default="")),
                ("support_email", models.CharField(default="support@quickhr.in", max_length=255)),
                ("support_phone", models.CharField(blank=True, default="", max_length=30)),
                ("footer_text", models.CharField(blank=True, default="", max_length=255)),
                ("is_maintenance", models.IntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "saas_platform_config"},
        ),
        migrations.CreateModel(
            name="SaasPricingPlan",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plan_key", models.CharField(max_length=50, unique=True)),
                ("plan_name", models.CharField(max_length=100)),
                ("price_monthly", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("price_yearly", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("currency", models.CharField(default="INR", max_length=10)),
                ("max_employees", models.IntegerField(default=50)),
                ("description", models.TextField(blank=True, default="")),
                ("features", models.TextField(blank=True, default="")),
                ("is_popular", models.IntegerField(default=0)),
                ("is_active", models.IntegerField(default=1)),
                ("sort_order", models.IntegerField(default=0)),
            ],
            options={"db_table": "saas_pricing_plan", "ordering": ["sort_order", "price_monthly"]},
        ),
        migrations.CreateModel(
            name="SaasProduct",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("icon", models.CharField(default="fas fa-cube", max_length=80)),
                ("short_desc", models.CharField(blank=True, default="", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.IntegerField(default=1)),
            ],
            options={"db_table": "saas_product", "ordering": ["sort_order", "title"]},
        ),
        migrations.CreateModel(
            name="SaasService",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("icon", models.CharField(default="fas fa-concierge-bell", max_length=80)),
                ("short_desc", models.CharField(blank=True, default="", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.IntegerField(default=1)),
            ],
            options={"db_table": "saas_service", "ordering": ["sort_order", "title"]},
        ),
        migrations.CreateModel(
            name="SaasOrganization",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("org_name", models.CharField(max_length=200)),
                ("org_slug", models.SlugField(max_length=100, unique=True)),
                ("admin_name", models.CharField(blank=True, default="", max_length=200)),
                ("admin_email", models.CharField(blank=True, default="", max_length=255)),
                ("admin_phone", models.CharField(blank=True, default="", max_length=20)),
                ("status", models.CharField(default="trial", max_length=20)),
                ("max_employees", models.IntegerField(default=50)),
                ("trial_ends_at", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="organizations", to="accounts.saaspricingplan")),
            ],
            options={"db_table": "saas_organization", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SaasContactInquiry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=200)),
                ("email", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, default="", max_length=20)),
                ("company", models.CharField(blank=True, default="", max_length=200)),
                ("subject", models.CharField(blank=True, default="", max_length=200)),
                ("message", models.TextField()),
                ("plan_interest", models.CharField(blank=True, default="", max_length=100)),
                ("status", models.CharField(default="new", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "saas_contact_inquiry", "ordering": ["-created_at"]},
        ),
        migrations.RunPython(seed_saas, migrations.RunPython.noop),
    ]

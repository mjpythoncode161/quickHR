from decimal import Decimal

from django.db import migrations, models


def seed_business_plan(apps, schema_editor):
    SaasPricingPlan = apps.get_model("accounts", "SaasPricingPlan")
    SaasPlatformConfig = apps.get_model("accounts", "SaasPlatformConfig")

    SaasPricingPlan.objects.get_or_create(
        plan_key="business",
        defaults={
            "plan_name": "Business",
            "price_monthly": Decimal("0"),
            "price_yearly": Decimal("0"),
            "max_employees": 9999,
            "description": "Pay per employee — monthly or yearly",
            "features": "GPS & selfie check-in\nAll HR modules\nPer-employee pricing\nMonthly or yearly billing",
            "sort_order": 1,
            "is_active": 1,
        },
    )

    cfg = SaasPlatformConfig.objects.filter(pk=1).first()
    if cfg:
        updates = {}
        if not getattr(cfg, "price_per_employee_monthly", None):
            updates["price_per_employee_monthly"] = Decimal("1000")
        if not getattr(cfg, "min_paid_employees", None):
            updates["min_paid_employees"] = 10
        if not getattr(cfg, "yearly_months_billed", None):
            updates["yearly_months_billed"] = 10
        if updates:
            for k, v in updates.items():
                setattr(cfg, k, v)
            cfg.save(update_fields=list(updates.keys()))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0039_mobile_push"),
    ]

    operations = [
        migrations.AddField(
            model_name="saasplatformconfig",
            name="price_per_employee_monthly",
            field=models.DecimalField(decimal_places=2, default=1000, max_digits=10),
        ),
        migrations.AddField(
            model_name="saasplatformconfig",
            name="min_paid_employees",
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name="saasplatformconfig",
            name="yearly_months_billed",
            field=models.IntegerField(
                default=10,
                help_text="Months charged on yearly plan (e.g. 10 = pay for 10, get 12)",
            ),
        ),
        migrations.AddField(
            model_name="saassubscription",
            name="employee_count",
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name="saassubscription",
            name="billing_period",
            field=models.CharField(default="monthly", max_length=10),
        ),
        migrations.AddField(
            model_name="saassubscription",
            name="price_per_employee",
            field=models.DecimalField(decimal_places=2, default=1000, max_digits=10),
        ),
        migrations.RunPython(seed_business_plan, migrations.RunPython.noop),
    ]

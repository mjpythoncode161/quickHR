from django.db import migrations, models


def seed_extra_ot(apps, schema_editor):
    ExtraOtConfig = apps.get_model("accounts", "ExtraOtConfig")
    ExtraOtConfig.objects.get_or_create(
        pk=1,
        defaults={
            "enabled": 0,
            "ot_rate_mode": "multiplier",
            "ot_multiplier": 2.0,
            "ot_hourly_rate": 0,
            "working_days_per_month": 26,
        },
    )
    PayrollModuleConfig = apps.get_model("accounts", "PayrollModuleConfig")
    cfg, _ = PayrollModuleConfig.objects.get_or_create(pk=1)
    if not getattr(cfg, "extra_ot_working", None):
        cfg.extra_ot_working = 1
        cfg.save(update_fields=["extra_ot_working"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0036_saas_lead_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="payrollmoduleconfig",
            name="extra_ot_working",
            field=models.IntegerField(default=1),
        ),
        migrations.CreateModel(
            name="ExtraOtConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.IntegerField(default=0)),
                ("ot_rate_mode", models.CharField(default="multiplier", max_length=20)),
                ("ot_multiplier", models.DecimalField(decimal_places=2, default=2.0, max_digits=6)),
                ("ot_hourly_rate", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("working_days_per_month", models.IntegerField(default=26)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "extra_ot_config",
                "verbose_name": "Extra OT Config",
            },
        ),
        migrations.RunPython(seed_extra_ot, migrations.RunPython.noop),
    ]

from django.db import migrations, models


def seed_hr_modules(apps, schema_editor):
    HrModuleConfig = apps.get_model("accounts", "HrModuleConfig")
    HrModuleConfig.objects.get_or_create(pk=1, defaults={"claims": 0})


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0029_shift_rotation"),
    ]

    operations = [
        migrations.CreateModel(
            name="HrModuleConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("claims", models.IntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "hr_module_config", "verbose_name": "HR Module Config"},
        ),
        migrations.CreateModel(
            name="ExpenseClaim",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("emp_id", models.CharField(max_length=50)),
                ("full_name", models.CharField(blank=True, default="", max_length=255)),
                ("claim_type", models.CharField(max_length=100)),
                ("claim_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("description", models.TextField(blank=True, default="")),
                ("receipt_note", models.CharField(blank=True, default="", max_length=255)),
                ("status", models.IntegerField(default=0)),
                ("admin_remarks", models.TextField(blank=True, default="")),
                ("applied_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_by", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={"db_table": "expense_claim", "ordering": ["-applied_at"]},
        ),
        migrations.RunPython(seed_hr_modules, migrations.RunPython.noop),
    ]

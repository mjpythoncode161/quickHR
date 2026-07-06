from django.db import migrations, models


def seed_salary_structure(apps, schema_editor):
    Config = apps.get_model("accounts", "SalaryStructureConfig")
    Rule = apps.get_model("accounts", "SalaryComponentRule")
    Config.objects.get_or_create(
        pk=1,
        defaults={
            "salary_base_mode": "gross",
            "salary_field_label": "Gross Salary (₹)",
            "show_basic_row": 1,
        },
    )
    if Rule.objects.exists():
        return
    defaults = [
        ("Basic Salary", "pct_gross", 40, "Earning", 1),
        ("HRA", "pct_basic", 40, "Earning", 2),
        ("Conveyance", "fixed", 19200, "Earning", 3),
        ("Medical Allowance", "fixed", 15000, "Earning", 4),
        ("Special Allowance", "remaining", 0, "Earning", 5),
        ("PF", "pct_basic", 12, "Deduction", 6),
    ]
    for name, method, rate, item_type, order in defaults:
        Rule.objects.create(
            component_name=name,
            calc_method=method,
            rate_value=rate,
            item_type=item_type,
            sort_order=order,
            is_active=1,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0026_recruitment"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalaryStructureConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("salary_base_mode", models.CharField(default="gross", max_length=20)),
                ("salary_field_label", models.CharField(default="Gross Salary (₹)", max_length=100)),
                ("show_basic_row", models.IntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "salary_structure_config"},
        ),
        migrations.CreateModel(
            name="SalaryComponentRule",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("component_name", models.CharField(max_length=100)),
                ("calc_method", models.CharField(default="fixed", max_length=20)),
                ("rate_value", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("item_type", models.CharField(default="Earning", max_length=20)),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.IntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "salary_component_rule", "ordering": ["sort_order", "id"]},
        ),
        migrations.RunPython(seed_salary_structure, migrations.RunPython.noop),
    ]

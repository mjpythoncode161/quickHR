from django.db import migrations, models


def seed_payroll_modules(apps, schema_editor):
    PayrollModuleConfig = apps.get_model("accounts", "PayrollModuleConfig")
    PayrollModuleConfig.objects.get_or_create(
        pk=1,
        defaults={
            "employee_salary_setup": 1,
            "salary_structure": 1,
            "deductions": 0,
            "employer_contributions": 0,
            "attendance_integration": 1,
            "payroll_processing": 0,
            "statutory_compliance": 0,
            "payslip": 1,
            "payroll_reports": 0,
            "payroll_approvals": 0,
            "payroll_settings": 1,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0027_salary_structure"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayrollModuleConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_salary_setup", models.IntegerField(default=1)),
                ("salary_structure", models.IntegerField(default=1)),
                ("deductions", models.IntegerField(default=0)),
                ("employer_contributions", models.IntegerField(default=0)),
                ("attendance_integration", models.IntegerField(default=1)),
                ("payroll_processing", models.IntegerField(default=0)),
                ("statutory_compliance", models.IntegerField(default=0)),
                ("payslip", models.IntegerField(default=1)),
                ("payroll_reports", models.IntegerField(default=0)),
                ("payroll_approvals", models.IntegerField(default=0)),
                ("payroll_settings", models.IntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "payroll_module_config",
                "verbose_name": "Payroll Module Config",
            },
        ),
        migrations.RunPython(seed_payroll_modules, migrations.RunPython.noop),
    ]

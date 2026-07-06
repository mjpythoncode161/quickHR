from django.db import migrations, models


DEFAULT_ROLES = [
    {
        "name": "Admin",
        "legacy_type": 1,
        "group_name": "admin",
        "is_staff": 1,
        "description": "Full system access — employees, attendance, payroll, and settings.",
    },
    {
        "name": "Employee",
        "legacy_type": 2,
        "group_name": "employee",
        "is_staff": 0,
        "description": "Self-service — check in/out, own attendance, leaves, and payslip.",
    },
    {
        "name": "Account",
        "legacy_type": 3,
        "group_name": "account",
        "is_staff": 1,
        "description": "Finance access — payslip, reports, and account-related modules.",
    },
]


def seed_default_roles(apps, schema_editor):
    RoleMaster = apps.get_model("accounts", "RoleMaster")
    for role in DEFAULT_ROLES:
        RoleMaster.objects.update_or_create(
            legacy_type=role["legacy_type"],
            defaults={
                "name": role["name"],
                "group_name": role["group_name"],
                "is_staff": role["is_staff"],
                "description": role["description"],
                "is_active": 1,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_biometric_id_and_api_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoleMaster",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("legacy_type", models.IntegerField(unique=True)),
                ("group_name", models.CharField(max_length=100)),
                ("is_staff", models.IntegerField(default=0)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.IntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "role_master",
                "ordering": ["legacy_type"],
            },
        ),
        migrations.RunPython(seed_default_roles, migrations.RunPython.noop),
    ]

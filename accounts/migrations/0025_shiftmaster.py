from django.db import migrations, models


from datetime import time as time_cls


def seed_default_shifts(apps, schema_editor):
    ShiftMaster = apps.get_model("accounts", "ShiftMaster")
    defaults = [
        ("General", time_cls(9, 30), time_cls(18, 30), 10, "Standard office shift"),
        ("Morning", time_cls(7, 0), time_cls(15, 0), 10, "Morning shift"),
        ("Evening", time_cls(14, 0), time_cls(22, 0), 10, "Evening shift"),
        ("Night", time_cls(22, 0), time_cls(6, 0), 15, "Night shift"),
    ]
    for name, ci, co, grace, desc in defaults:
        ShiftMaster.objects.get_or_create(
            shift_name=name,
            defaults={
                "check_in": ci,
                "check_out": co,
                "grace_minutes": grace,
                "description": desc,
                "is_active": 1,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0024_management_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShiftMaster",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shift_name", models.CharField(max_length=100, unique=True)),
                ("check_in", models.TimeField()),
                ("check_out", models.TimeField()),
                ("grace_minutes", models.IntegerField(default=10)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.IntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "shift_master",
                "ordering": ["shift_name"],
            },
        ),
        migrations.RunPython(seed_default_shifts, migrations.RunPython.noop),
    ]

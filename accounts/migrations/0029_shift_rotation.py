from django.db import migrations, models
import datetime


def seed_shift_rotation(apps, schema_editor):
    ShiftRotationConfig = apps.get_model("accounts", "ShiftRotationConfig")
    ShiftRotationConfig.objects.get_or_create(
        pk=1,
        defaults={
            "enabled": 0,
            "cycle_days": 7,
            "rotation_start_date": datetime.date.today(),
            "stagger_employees": 1,
        },
    )
    ShiftMaster = apps.get_model("accounts", "ShiftMaster")
    order_map = {"General": 0, "Morning": 1, "Evening": 2, "Night": 3}
    for name, order in order_map.items():
        ShiftMaster.objects.filter(shift_name=name).update(rotation_order=order)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0028_payroll_module_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="shiftmaster",
            name="rotation_order",
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name="ShiftRotationConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.IntegerField(default=0)),
                ("cycle_days", models.IntegerField(default=7)),
                ("rotation_start_date", models.DateField(blank=True, null=True)),
                ("stagger_employees", models.IntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "shift_rotation_config",
                "verbose_name": "Shift Rotation Config",
            },
        ),
        migrations.RunPython(seed_shift_rotation, migrations.RunPython.noop),
    ]

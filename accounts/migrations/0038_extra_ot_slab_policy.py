# Extra OT slab & policy fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0037_extra_ot_working"),
    ]

    operations = [
        migrations.AddField(
            model_name="extraotconfig",
            name="calc_policy",
            field=models.CharField(default="shift_overtime", max_length=30),
        ),
        migrations.AddField(
            model_name="extraotconfig",
            name="hours_basis",
            field=models.CharField(default="ot_only", max_length=20),
        ),
        migrations.AddField(
            model_name="extraotconfig",
            name="half_day_threshold_hours",
            field=models.DecimalField(decimal_places=2, default=2.0, max_digits=5),
        ),
        migrations.AddField(
            model_name="extraotconfig",
            name="full_day_threshold_hours",
            field=models.DecimalField(decimal_places=2, default=8.0, max_digits=5),
        ),
    ]

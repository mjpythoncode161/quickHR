from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0040_per_employee_pricing"),
    ]

    operations = [
        migrations.AddField(
            model_name="saasplatformconfig",
            name="trial_days",
            field=models.IntegerField(default=7),
        ),
        migrations.AddField(
            model_name="saasplatformconfig",
            name="trial_max_employees",
            field=models.IntegerField(default=25),
        ),
        migrations.AddField(
            model_name="saasplatformconfig",
            name="free_max_employees",
            field=models.IntegerField(default=2),
        ),
    ]

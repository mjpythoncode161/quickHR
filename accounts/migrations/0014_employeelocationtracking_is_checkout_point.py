from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_auto_20260326_1216"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeelocationtracking",
            name="is_checkout_point",
            field=models.BooleanField(default=False),
        ),
    ]

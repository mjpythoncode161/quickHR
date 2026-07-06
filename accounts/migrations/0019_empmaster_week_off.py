from django.db import migrations, models


def add_week_off_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "week_off" not in columns:
            cursor.execute(
                "ALTER TABLE emp_master ADD COLUMN week_off VARCHAR(50) DEFAULT '5,6'"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0018_empmaster_photo_selfie"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="week_off",
                    field=models.CharField(
                        blank=True, default="5,6", max_length=50, null=True
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_week_off_column, migrations.RunPython.noop),
            ],
        ),
    ]

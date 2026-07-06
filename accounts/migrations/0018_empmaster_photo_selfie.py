from django.db import migrations, models


def add_photo_selfie_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "photo_selfie" not in columns:
            cursor.execute(
                "ALTER TABLE emp_master ADD COLUMN photo_selfie INTEGER DEFAULT 1"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0017_empmaster_late_attendance_penalty"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="photo_selfie",
                    field=models.IntegerField(blank=True, default=1, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_photo_selfie_column, migrations.RunPython.noop),
            ],
        ),
    ]

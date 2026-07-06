from django.db import migrations, models


def add_location_status_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(attendance_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "location_status" not in columns:
            cursor.execute(
                "ALTER TABLE attendance_master ADD COLUMN location_status VARCHAR(50)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_empmaster_week_off"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="attendancemaster",
                    name="location_status",
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_location_status_column, migrations.RunPython.noop
                ),
            ],
        ),
    ]

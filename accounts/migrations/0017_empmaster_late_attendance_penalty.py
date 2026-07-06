from django.db import migrations, models


def add_late_attendance_penalty_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "late_attendance_penalty" not in columns:
            cursor.execute(
                "ALTER TABLE emp_master ADD COLUMN late_attendance_penalty INTEGER DEFAULT 1"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_empmaster_extended_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="late_attendance_penalty",
                    field=models.IntegerField(blank=True, default=1, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_late_attendance_penalty_column, migrations.RunPython.noop
                ),
            ],
        ),
    ]

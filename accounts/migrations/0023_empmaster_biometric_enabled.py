from django.db import migrations, models


def add_biometric_enabled_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "biometric_enabled" not in columns:
            cursor.execute(
                "ALTER TABLE emp_master ADD COLUMN biometric_enabled INTEGER DEFAULT 0"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_rolemaster"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="biometric_enabled",
                    field=models.IntegerField(blank=True, default=0, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_biometric_enabled_column, migrations.RunPython.noop
                ),
            ],
        ),
    ]

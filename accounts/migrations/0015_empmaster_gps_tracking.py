from django.db import migrations, models


def add_gps_tracking_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "gps_tracking" not in columns:
            cursor.execute(
                "ALTER TABLE emp_master ADD COLUMN gps_tracking INTEGER DEFAULT 1"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_employeelocationtracking_is_checkout_point"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="gps_tracking",
                    field=models.IntegerField(blank=True, default=1, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_gps_tracking_column, migrations.RunPython.noop
                ),
            ],
        ),
    ]

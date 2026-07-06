from django.db import migrations, models


def add_biometric_id_column(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        columns = {row[1] for row in cursor.fetchall()}
        if "biometric_id" not in columns:
            cursor.execute(
                "ALTER TABLE emp_master ADD COLUMN biometric_id VARCHAR(100)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_attendancemaster_location_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="biometric_id",
                    field=models.CharField(
                        blank=True, max_length=100, null=True, unique=True
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_biometric_id_column, migrations.RunPython.noop
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApiSettings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("api_token", models.CharField(blank=True, default="", max_length=128)),
                ("api_enabled", models.IntegerField(default=1)),
                ("biometric_enabled", models.IntegerField(default=1)),
                ("device_name", models.CharField(blank=True, default="", max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "API Settings",
                "verbose_name_plural": "API Settings",
                "db_table": "api_settings",
            },
        ),
    ]

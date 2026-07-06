from django.db import migrations, models


NEW_COLUMNS = [
    ("employee_code", "VARCHAR(100)"),
    ("marital_status", "VARCHAR(50)"),
    ("official_email", "VARCHAR(255)"),
    ("address_line1", "VARCHAR(255)"),
    ("address_line2", "VARCHAR(255)"),
    ("city", "VARCHAR(100)"),
    ("district", "VARCHAR(100)"),
    ("state", "VARCHAR(100)"),
    ("country", "VARCHAR(100)"),
    ("pin_code", "VARCHAR(20)"),
    ("education", "VARCHAR(255)"),
    ("work_experience", "VARCHAR(255)"),
    ("employment_status", "VARCHAR(50)"),
    ("shift", "VARCHAR(100)"),
    ("work_mode", "VARCHAR(50)"),
    ("pan_no", "VARCHAR(20)"),
    ("aadhar_no", "VARCHAR(20)"),
    ("passport_no", "VARCHAR(50)"),
    ("driving_license", "VARCHAR(50)"),
    ("notice_period_days", "INTEGER"),
]


def add_extended_employee_columns(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(emp_master)")
        existing = {row[1] for row in cursor.fetchall()}
        for name, col_type in NEW_COLUMNS:
            if name not in existing:
                cursor.execute(
                    f"ALTER TABLE emp_master ADD COLUMN {name} {col_type}"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_empmaster_gps_tracking"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="empmaster",
                    name="employee_code",
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="marital_status",
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="official_email",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="address_line1",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="address_line2",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="city",
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="district",
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="state",
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="country",
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="pin_code",
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="education",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="work_experience",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="employment_status",
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="shift",
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="work_mode",
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="pan_no",
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="aadhar_no",
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="passport_no",
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="driving_license",
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name="empmaster",
                    name="notice_period_days",
                    field=models.IntegerField(blank=True, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_extended_employee_columns, migrations.RunPython.noop
                ),
            ],
        ),
    ]

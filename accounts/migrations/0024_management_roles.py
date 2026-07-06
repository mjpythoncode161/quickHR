from django.db import migrations


def reseed_management_roles(apps, schema_editor):
    RoleMaster = apps.get_model("accounts", "RoleMaster")
    roles = [
        {
            "legacy_type": 1,
            "name": "HR Admin",
            "group_name": "hr_admin",
            "is_staff": 1,
            "is_active": 1,
            "description": "Full HRMS access — employees, attendance, leaves, payroll, and settings.",
        },
        {
            "legacy_type": 2,
            "name": "Employee (No Web Login)",
            "group_name": "employee",
            "is_staff": 0,
            "is_active": 0,
            "description": "Not used for web login. Employees are records only (EmpMaster).",
        },
        {
            "legacy_type": 3,
            "name": "Payroll Admin",
            "group_name": "payroll_admin",
            "is_staff": 1,
            "is_active": 1,
            "description": "Payroll and payslip management, finance reports.",
        },
        {
            "legacy_type": 4,
            "name": "Department Head / HOD",
            "group_name": "hod",
            "is_staff": 1,
            "is_active": 1,
            "description": "Department-level attendance, leave approvals, and team reports.",
        },
        {
            "legacy_type": 5,
            "name": "Reporting Manager",
            "group_name": "reporting_manager",
            "is_staff": 1,
            "is_active": 1,
            "description": "Team attendance, leave approvals, and reports for direct reports.",
        },
        {
            "legacy_type": 6,
            "name": "Team Leader / Supervisor",
            "group_name": "team_leader",
            "is_staff": 1,
            "is_active": 1,
            "description": "Supervise team check-in, attendance, and leave requests.",
        },
    ]
    for role in roles:
        RoleMaster.objects.update_or_create(
            legacy_type=role["legacy_type"],
            defaults={
                "name": role["name"],
                "group_name": role["group_name"],
                "is_staff": role["is_staff"],
                "is_active": role["is_active"],
                "description": role["description"],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0023_empmaster_biometric_enabled"),
    ]

    operations = [
        migrations.RunPython(reseed_management_roles, migrations.RunPython.noop),
    ]

from django.contrib.auth.models import Group, User

from .models import EmpMaster, RoleMaster, Users

# Web portal roles only — employees use mobile app / biometric, not Users login.
DEFAULT_ROLES = [
    {
        "name": "HR Admin",
        "legacy_type": 1,
        "group_name": "hr_admin",
        "is_staff": 1,
        "description": "Full HRMS access — employees, attendance, leaves, payroll, and settings.",
    },
    {
        "name": "Employee (No Web Login)",
        "legacy_type": 2,
        "group_name": "employee",
        "is_staff": 0,
        "description": "Legacy — not used for web login. Employees are records only (EmpMaster).",
        "is_active": 0,
    },
    {
        "name": "Payroll Admin",
        "legacy_type": 3,
        "group_name": "payroll_admin",
        "is_staff": 1,
        "description": "Payroll and payslip management, finance reports.",
    },
    {
        "name": "Department Head / HOD",
        "legacy_type": 4,
        "group_name": "hod",
        "is_staff": 1,
        "description": "Department-level attendance, leave approvals, and team reports.",
    },
    {
        "name": "Reporting Manager",
        "legacy_type": 5,
        "group_name": "reporting_manager",
        "is_staff": 1,
        "description": "Team attendance, leave approvals, and reports for direct reports.",
    },
    {
        "name": "Team Leader / Supervisor",
        "legacy_type": 6,
        "group_name": "team_leader",
        "is_staff": 1,
        "description": "Supervise team check-in, attendance, and leave requests.",
    },
]

ROLE_BADGE_CLASSES = {
    1: "primary",
    3: "warning",
    4: "info",
    5: "success",
    6: "secondary",
}


def ensure_default_roles():
    for role in DEFAULT_ROLES:
        defaults = {
            "name": role["name"],
            "group_name": role["group_name"],
            "is_staff": role["is_staff"],
            "description": role["description"],
            "is_active": role.get("is_active", 1),
        }
        RoleMaster.objects.update_or_create(
            legacy_type=role["legacy_type"],
            defaults=defaults,
        )
        if defaults["is_active"]:
            Group.objects.get_or_create(name=role["group_name"])


def get_active_management_roles():
    ensure_default_roles()
    return RoleMaster.objects.filter(is_active=1).exclude(legacy_type=2).order_by(
        "legacy_type"
    )


def get_management_legacy_types():
    return list(get_active_management_roles().values_list("legacy_type", flat=True))


def get_role_for_type(legacy_type):
    ensure_default_roles()
    return RoleMaster.objects.filter(legacy_type=legacy_type, is_active=1).first()


def get_role_label(legacy_type):
    role = RoleMaster.objects.filter(legacy_type=legacy_type).first()
    if role:
        return role.name
    labels = {1: "HR Admin", 3: "Payroll Admin", 4: "HOD", 5: "Reporting Manager", 6: "Team Leader"}
    return labels.get(legacy_type, "Unknown")


def get_role_badge_class(legacy_type):
    return ROLE_BADGE_CLASSES.get(legacy_type, "secondary")


def find_emp_by_login_id(login_id):
    """Find EmpMaster by phone, emp_id, or employee code."""
    login_id = (login_id or "").strip()
    if not login_id:
        return None

    emp = EmpMaster.objects.filter(contact=login_id).first()
    if emp:
        return emp

    emp = EmpMaster.objects.filter(emp_id=login_id).first()
    if emp:
        return emp

    emp = EmpMaster.objects.filter(employee_code=login_id).first()
    if emp:
        return emp

    try:
        normalized = str(int(login_id))
        emp = EmpMaster.objects.filter(emp_id=normalized).first()
        if emp:
            return emp
    except (ValueError, TypeError):
        pass

    return None


def find_emp_for_auth_user(auth_user):
    """Link a Django user to their EmpMaster record."""
    if not auth_user:
        return None

    username = (auth_user.username or "").strip()
    if username:
        emp = find_emp_by_login_id(username)
        if emp:
            return emp

    email = (getattr(auth_user, "email", None) or "").strip()
    if email:
        emp = EmpMaster.objects.filter(email__iexact=email).first()
        if emp:
            return emp
        emp = EmpMaster.objects.filter(official_email__iexact=email).first()
        if emp:
            return emp

    return None


def resolve_auth_user_from_login(login_id):
    """Resolve Django auth user from phone, employee ID, or email."""
    login_id = (login_id or "").strip()
    if not login_id:
        return None

    if "@" in login_id:
        user = User.objects.filter(email__iexact=login_id).first()
        if user:
            return user

    user = User.objects.filter(username=login_id).first()
    if user:
        return user

    emp = find_emp_by_login_id(login_id)
    if emp and (emp.contact or "").strip():
        user = User.objects.filter(username=emp.contact.strip()).first()
        if user:
            return user

    legacy = Users.objects.filter(contact=login_id).first()
    if not legacy and "@" in login_id:
        legacy = Users.objects.filter(email__iexact=login_id).first()
    if legacy:
        return find_auth_user(legacy)

    return None


def is_employee_portal_user(auth_user):
    """True when user is an employee (EmpMaster) using the web portal."""
    if not auth_user or not auth_user.is_authenticated:
        return False
    if auth_user.is_superuser or auth_user.is_staff:
        legacy = find_legacy_user(auth_user)
        if legacy and legacy.type != 2:
            return False
    legacy = find_legacy_user(auth_user)
    if legacy and legacy.type != 2:
        return False
    return find_emp_for_auth_user(auth_user) is not None


def ensure_employee_auth_account(emp, plain_password=None):
    """
    Create or activate Django login for an employee.
    Username = mobile number; password defaults to last 4 digits of mobile.
    """
    contact = (emp.contact or "").strip()
    if not contact or len(contact) != 10 or not contact.isdigit():
        return None

    email = (emp.email or emp.official_email or "").strip()
    full_name = (emp.full_name or "").strip()
    name_parts = full_name.split(" ", 1) if full_name else ["", ""]
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    default_password = plain_password or contact[-4:]

    user = User.objects.filter(username=contact).first()
    if user:
        user.is_active = True
        user.is_staff = False
        if email and not user.email:
            user.email = email
        if first_name and not user.first_name:
            user.first_name = first_name
        if last_name and not user.last_name:
            user.last_name = last_name
        user.save()
        if plain_password:
            user.set_password(plain_password)
            user.save(update_fields=["password"])
        return user

    user = User.objects.create_user(
        username=contact,
        email=email or "",
        password=default_password,
        first_name=first_name,
        last_name=last_name,
    )
    user.is_staff = False
    user.is_active = True
    user.save(update_fields=["is_staff", "is_active"])
    return user


def find_legacy_user(auth_user):
    if not auth_user or not auth_user.is_authenticated:
        return None
    contact = (auth_user.username or "").strip()
    email = (getattr(auth_user, "email", None) or "").strip()
    if contact:
        legacy = Users.objects.filter(contact=contact).first()
        if legacy:
            return legacy
    if email:
        return Users.objects.filter(email=email).first()
    return None


def find_auth_user(legacy_user):
    if not legacy_user:
        return None
    contact = (legacy_user.contact or "").strip()
    email = (legacy_user.email or "").strip()
    if contact:
        user = User.objects.filter(username=contact).first()
        if user:
            return user
    if email:
        return User.objects.filter(email=email).first()
    return None


def can_access_web_portal(auth_user):
    """Management roles and linked employees may use the web dashboard."""
    if not auth_user or not auth_user.is_authenticated:
        return False
    if auth_user.is_superuser:
        return True

    legacy = find_legacy_user(auth_user)
    if legacy:
        if legacy.type == 2:
            return find_emp_for_auth_user(auth_user) is not None
        role = get_role_for_type(legacy.type)
        if role:
            return bool(role.is_staff)
        return legacy.type in get_management_legacy_types()

    if find_emp_for_auth_user(auth_user):
        return True

    return bool(auth_user.is_staff)


def sync_user_role(legacy_user, legacy_type=None):
    """Apply role to legacy user and linked Django auth account."""
    if not legacy_user:
        return False

    ensure_default_roles()

    if legacy_type is not None:
        legacy_user.type = int(legacy_type)
        legacy_user.save(update_fields=["type"])

    if legacy_user.type == 2:
        auth_user = find_auth_user(legacy_user)
        if auth_user:
            auth_user.is_staff = False
            auth_user.is_active = False
            auth_user.save(update_fields=["is_staff", "is_active"])
            auth_user.groups.clear()
        return False

    role = get_role_for_type(legacy_user.type)
    if not role:
        return False

    Group.objects.get_or_create(name=role.group_name)
    auth_user = find_auth_user(legacy_user)
    if auth_user:
        auth_user.is_staff = bool(role.is_staff)
        auth_user.is_active = True
        auth_user.save(update_fields=["is_staff", "is_active"])
        auth_user.groups.clear()
        group = Group.objects.get(name=role.group_name)
        auth_user.groups.add(group)

    return True

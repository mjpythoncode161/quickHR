from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .models import (
    DeptMaster,
    DesigMaster,
    EmpMaster,
    AttendanceMaster,
    AttendanceReq,
    LeaveRequest,
    HolidayMaster,
    EmpItemMaster,
    EmpTemp,
    Users,
    SaasPricingPlan,
    SystemSettings,
    ApiSettings,
    RoleMaster,
    ShiftMaster,
)
from .forms import departmentForm, designationForm, employeeForm
from .context_processors import save_company_logo
from .api_settings_utils import get_api_settings, regenerate_api_token
from .salary_utils import (
    compute_emp_item_amount,
    get_salary_config,
    get_salary_structure_for_form,
    get_other_emp_items,
    calculate_salary_breakdown,
    component_to_dict,
    get_active_salary_components,
    build_breakdown_for_employee,
    get_payslip_line_items,
)
from .payroll_module_utils import (
    get_payroll_hub_items,
    get_payroll_module_config,
    is_module_enabled,
)
from .hr_module_utils import get_hr_hub_items
from .notification_module_utils import get_notification_hub_items
from .shift_utils import (
    ensure_default_shifts,
    get_active_shifts,
    get_scheduled_check_in,
    get_scheduled_check_out,
    get_late_grace_minutes,
    get_shift_label,
    calc_late_minutes,
    attendance_status_for_check_in,
    employee_late_penalty_enabled,
    fmt_late_display,
)
from .role_utils import (
    ensure_default_roles,
    sync_user_role,
    get_role_label,
    get_role_badge_class,
    get_active_management_roles,
    get_management_legacy_types,
    can_access_web_portal,
    find_emp_for_auth_user,
    find_emp_by_login_id,
    resolve_auth_user_from_login,
    ensure_employee_auth_account,
)
from .saas_utils import create_saas_lead
from .subscription_pricing import get_pricing_config
from .subscription_utils import (
    can_add_employee,
    count_employees,
    employee_limit_message,
    geo_location_enabled,
    get_employee_limit,
    get_subscribe_url,
    get_subscription_context,
    has_paid_subscription,
    provision_free_organization,
    provision_trial_organization,
    setup_company_owner_account,
)
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse

# Create your views here.


def _debug_session_log(location, message, data, hypothesis_id, run_id="notif-debug"):
    # #region agent log
    import json
    import os
    import time

    from django.conf import settings

    log_path = os.path.normpath(os.path.join(settings.BASE_DIR, "..", "debug-72a37d.log"))
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(
                    {
                        "sessionId": "72a37d",
                        "location": location,
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                        "hypothesisId": hypothesis_id,
                        "runId": run_id,
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion


def _save_base64_photo(photo_data, prefix):
    """Save a base64 data-URL image under MEDIA_ROOT; return relative path."""
    import base64
    import os
    import uuid

    from django.conf import settings

    if not photo_data or not photo_data.startswith("data:image/"):
        return ""
    try:
        header, imgstr = photo_data.split(";base64,", 1)
        ext = header.split("/")[-1].lower()
        if ext not in ("jpeg", "jpg", "png", "webp"):
            ext = "jpeg"
        filename = f"{prefix}_{uuid.uuid4().hex}.{ext}"
        rel_path = os.path.join("attendance_photos", filename).replace("\\", "/")
        abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(base64.b64decode(imgstr))
        return rel_path
    except Exception:
        return ""


def _format_inr(amount):
    return f"{float(amount):,.2f}"


def _scheduled_hours_per_day(employee):
    from datetime import datetime, timedelta

    scheduled_in = get_scheduled_check_in(employee)
    scheduled_out = get_scheduled_check_out(employee)
    if scheduled_in and scheduled_out:
        today = datetime.today().date()
        ci = datetime.combine(today, scheduled_in)
        co = datetime.combine(today, scheduled_out)
        if co <= ci:
            co += timedelta(days=1)
        return round((co - ci).total_seconds() / 3600, 2)
    return 8.0


def _amount_in_words(amount):
    ones = [
        "",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
    ]
    tens = [
        "",
        "",
        "Twenty",
        "Thirty",
        "Forty",
        "Fifty",
        "Sixty",
        "Seventy",
        "Eighty",
        "Ninety",
    ]

    def two_digit(n):
        if n < 20:
            return ones[n]
        return (tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")).strip()

    def three_digit(n):
        if n < 100:
            return two_digit(n)
        return (
            ones[n // 100]
            + " Hundred"
            + (" " + two_digit(n % 100) if n % 100 else "")
        ).strip()

    n = int(round(float(amount)))
    if n == 0:
        return "Rupees Zero only"

    parts = []
    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    remainder = n

    if crore:
        parts.append(three_digit(crore) + " Crore")
    if lakh:
        parts.append(two_digit(lakh) + " Lakh")
    if thousand:
        parts.append(two_digit(thousand) + " Thousand")
    if remainder:
        parts.append(three_digit(remainder))

    return "Rupees " + " ".join(parts) + " only"


@login_required(login_url="login")
def home(request):
    from datetime import date, datetime

    today = date.today()
    month_start = today.replace(day=1)

    is_admin_dashboard = (
        request.user.is_superuser
        or request.user.is_staff
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    upcoming_holidays = HolidayMaster.objects.filter(holiday_date__gte=today).order_by(
        "holiday_date"
    )[:5]

    context = {
        "is_admin_dashboard": is_admin_dashboard,
        "upcoming_holidays": upcoming_holidays,
        "today": today.strftime("%Y-%m-%d"),
        **get_subscription_context(),
    }

    if is_admin_dashboard:
        context.update(
            {
                "total_employees": EmpMaster.objects.count(),
                "today_attendance": AttendanceMaster.objects.filter(att_date=today).count(),
                "pending_leaves": LeaveRequest.objects.filter(leave_status=0).count(),
                "pending_registrations": EmpTemp.objects.filter(status="PENDING").count(),
            }
        )
    else:
        own_emp = find_emp_for_auth_user(request.user)

        my_attendance_month = 0
        total_late = 0
        total_leave = 0
        today_attendance_record = None
        check_in_iso = ""

        if own_emp:
            emp_id = int(own_emp.emp_id)
            month_qs = AttendanceMaster.objects.filter(
                emp_id=emp_id,
                att_date__gte=month_start,
                att_date__lte=today,
            )
            my_attendance_month = month_qs.filter(
                attendance_status__in=["Present", "Late", "Half Day"]
            ).count()
            total_late = month_qs.filter(attendance_status="Late").count()
            total_leave = LeaveRequest.objects.filter(emp_id=emp_id).count()
            today_attendance_record = AttendanceMaster.objects.filter(
                emp_id=emp_id, att_date=today
            ).first()
            if today_attendance_record and today_attendance_record.check_in:
                check_in_iso = datetime.combine(
                    today, today_attendance_record.check_in
                ).isoformat()

        context.update(
            {
                "own_emp": own_emp,
                "my_attendance_month": my_attendance_month,
                "total_late": total_late,
                "total_leave": total_leave,
                "today_attendance_record": today_attendance_record,
                "check_in_iso": check_in_iso,
                "month_name": today.strftime("%B %Y"),
            }
        )

    return render(request, "accounts/index.html", context)


def get_employee_by_mobile(request):
    """AJAX endpoint to fetch employee details from User table by mobile number"""
    mobile = request.GET.get("mobile", "")
    if mobile:
        # Check User table (username is phone number)
        try:
            user = User.objects.get(username=mobile)
            data = {
                "found": True,
                "full_name": f"{user.first_name} {user.last_name}".strip() or "",
                "email": user.email or "",
                "dob": "",
                "gender": "",
                "address": "",
                "father_name": "",
                "emergency_contact": "",
                "blood_group": "",
                "bank_name": "",
                "branch_name": "",
                "account_name": "",
                "account_number": "",
                "ifsc_code": "",
            }
            return JsonResponse(data)
        except User.DoesNotExist:
            return JsonResponse({"found": False})
    return JsonResponse({"found": False})


def designation_add(request):
    if request.method == "POST":
        dept_name = request.POST.get("department_name", "")
        desig_name = request.POST.get("designation_name", "")
        if dept_name and desig_name:
            desig = DesigMaster()
            desig.dept_name = dept_name
            desig.desig_name = desig_name
            desig.save()
            messages.success(request, "Designation successfully added")
            return redirect("designation_list")
        else:
            messages.error(request, "All fields are required")
    departments = DeptMaster.objects.all()
    return render(
        request, "accounts/designation_add.html", {"departments": departments}
    )


def department_list(request):
    form = DeptMaster.objects.all()
    context = {"form": form}
    return render(request, "accounts/department_list.html", context)


def department_add(request):
    if request.method == "POST":
        dept_name = request.POST.get("department_name", "")
        if dept_name:
            dept = DeptMaster()
            dept.dept_name = dept_name
            dept.save()
            messages.success(request, "Department successfully added")
            return redirect("department_list")
        else:
            messages.error(request, "Department name is required")
    return render(request, "accounts/department_add.html")


def department_edit(request, id):
    obj = get_object_or_404(DeptMaster, id=id)
    if request.method == "POST":
        dept_name = request.POST.get("dept_name", "")
        if dept_name:
            obj.dept_name = dept_name
            obj.save()
            messages.success(request, "Department updated successfully")
            return redirect("department_list")
        else:
            messages.error(request, "Department name is required")
    form = departmentForm(instance=obj)
    context = {"form": form}
    return render(request, "accounts/department_edit.html", context)


def department_delete(request, id):
    obj = get_object_or_404(DeptMaster, id=id)
    obj.delete()
    messages.success(request, "Department deleted successfully")
    return redirect("department_list")


@login_required(login_url="login")
@permission_required("accounts.view_empmaster", raise_exception=True)
def employee_list(request):
    # Check if user is a restricted employee (not admin/superuser)
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    if is_restricted_user:
        # For restricted users, show only their own employee record
        # Match by username (phone number) with contact field
        employees = EmpMaster.objects.filter(contact=request.user.username)
    else:
        # For admins/managers, show all employees
        employees = EmpMaster.objects.all()

    context = {"employees": employees, "is_restricted_user": is_restricted_user}
    return render(request, "accounts/employee_list.html", context)


@login_required(login_url="login")
@permission_required("accounts.view_empmaster", raise_exception=True)
def employee_view(request, id):
    employee = get_object_or_404(EmpMaster, id=id)
    scheduled_in = get_scheduled_check_in(employee)
    scheduled_out = get_scheduled_check_out(employee)
    context = {
        "employee": employee,
        "week_off_display": _format_week_off_display(employee),
        "shift_label": get_shift_label(employee),
        "scheduled_in": scheduled_in,
        "scheduled_out": scheduled_out,
        "can_edit_employee": request.user.has_perm("accounts.change_empmaster"),
    }
    return render(request, "accounts/employee_view.html", context)


DEFAULT_WEEK_OFF = "5,6"
WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _parse_week_off_days(emp):
    raw = getattr(emp, "week_off", None) if emp else None
    if not raw:
        return {5, 6}
    days = set()
    for part in str(raw).split(","):
        part = part.strip()
        if part.isdigit():
            num = int(part)
            if 0 <= num <= 6:
                days.add(num)
    return days if days else {5, 6}


def _week_off_from_post(post):
    selected = post.getlist("week_off")
    valid = sorted(
        {int(d) for d in selected if str(d).isdigit() and 0 <= int(d) <= 6}
    )
    return ",".join(str(d) for d in valid) if valid else DEFAULT_WEEK_OFF


def _format_week_off_display(emp):
    days = sorted(_parse_week_off_days(emp))
    return ", ".join(WEEKDAY_SHORT[d] for d in days)


def _emp_id_as_int(emp_id):
    try:
        return int(emp_id)
    except (ValueError, TypeError):
        return None


def _build_attendance_grid_for_employee(emp, month, year):
    """Daily status cells for attendance grid report (per-employee week off)."""
    import calendar
    from datetime import date, timedelta

    num_days = calendar.monthrange(year, month)[1]
    week_off_days = _parse_week_off_days(emp)
    emp_id_int = _emp_id_as_int(emp.emp_id)

    att_by_day = {}
    if emp_id_int is not None:
        qs = AttendanceMaster.objects.filter(
            emp_id=emp_id_int, att_date__month=month, att_date__year=year
        )
    else:
        qs = AttendanceMaster.objects.filter(
            full_name=emp.full_name, att_date__month=month, att_date__year=year
        )
    for att in qs:
        att_by_day[att.att_date.day] = att

    holidays = {
        h.holiday_date.day
        for h in HolidayMaster.objects.filter(
            holiday_date__month=month, holiday_date__year=year
        )
    }

    leave_by_day = {}
    if emp_id_int is not None:
        for leave in LeaveRequest.objects.filter(
            emp_id=emp_id_int,
            leave_status=1,
            start_date__lte=date(year, month, num_days),
            end_date__gte=date(year, month, 1),
        ):
            d = leave.start_date
            while d <= leave.end_date:
                if d.month == month and d.year == year:
                    leave_by_day[d.day] = leave
                d += timedelta(days=1)

    days_status = []
    for day in range(1, num_days + 1):
        day_date = date(year, month, day)
        weekday = day_date.weekday()

        if day in holidays:
            days_status.append(
                {"day": day, "status": "PH", "class": "hrms-att-cell hrms-att-ph"}
            )
        elif weekday in week_off_days:
            days_status.append(
                {"day": day, "status": "WO", "class": "hrms-att-cell hrms-att-wo"}
            )
        elif day in leave_by_day:
            leave = leave_by_day[day]
            if getattr(leave, "is_paid", 1):
                days_status.append(
                    {"day": day, "status": "PL", "class": "hrms-att-cell hrms-att-pl"}
                )
            else:
                days_status.append(
                    {"day": day, "status": "UPL", "class": "hrms-att-cell hrms-att-upl"}
                )
        elif day in att_by_day:
            att = att_by_day[day]
            raw = (att.attendance_status or "").strip()
            if raw == "Absent":
                code, css = "A", "text-danger font-weight-bold"
            elif raw == "Half Day":
                code, css = "HD", "text-warning font-weight-bold"
            elif raw == "Late":
                code, css = "L", "text-info font-weight-bold"
            elif raw == "On Leave":
                code, css = "PL", "hrms-att-cell hrms-att-pl"
            else:
                code, css = "P", "text-success font-weight-bold"
            days_status.append({"day": day, "status": code, "class": css})
        elif day_date <= date.today():
            days_status.append(
                {"day": day, "status": "A", "class": "text-danger font-weight-bold"}
            )
        else:
            days_status.append(
                {"day": day, "status": "-", "class": "text-muted"}
            )

    return days_status, _format_week_off_display(emp)


def _count_working_days_in_month(emp, year, month):
    import calendar
    from datetime import date

    week_off = _parse_week_off_days(emp)
    num_days = calendar.monthrange(int(year), int(month))[1]
    working = 0
    for day in range(1, num_days + 1):
        if date(int(year), int(month), day).weekday() not in week_off:
            working += 1
    return working


def _suggested_employee_code(emp_id):
    try:
        return f"EMP{int(emp_id):04d}"
    except (ValueError, TypeError):
        return f"EMP-{emp_id}"


def _next_auto_emp_id():
    from django.db.models import IntegerField, Max
    from django.db.models.functions import Cast

    max_id = (
        EmpMaster.objects.aggregate(max_id=Max(Cast("emp_id", IntegerField())))[
            "max_id"
        ]
        or 0
    )
    return str(max_id + 1)


def _format_employee_address(post):
    parts = [
        post.get("address_line1", "").strip(),
        post.get("address_line2", "").strip(),
        post.get("city", "").strip(),
        post.get("district", "").strip(),
        post.get("state", "").strip(),
        post.get("country", "").strip(),
        post.get("pin_code", "").strip(),
    ]
    return ", ".join(p for p in parts if p)


def _biometric_id_taken(biometric_id, exclude_emp_id=None):
    bio = (biometric_id or "").strip()
    if not bio:
        return False
    qs = EmpMaster.objects.filter(biometric_id=bio)
    if exclude_emp_id is not None:
        qs = qs.exclude(emp_id=str(exclude_emp_id))
    return qs.exists()


def _populate_employee_from_post(emp, request):
    post = request.POST
    addr = _format_employee_address(post)

    emp.contact = post.get("mobile_no", "").strip()
    emp.full_name = post.get("full_name", "").strip()
    emp.email = post.get("email", "").strip()
    emp.official_email = post.get("official_email", "").strip()
    emp.dob = post.get("dob") or None
    emp.gender = post.get("gender", "")
    emp.marital_status = post.get("marital_status", "")
    emp.employee_code = post.get("employee_code", "").strip()
    emp.biometric_enabled = 1 if post.get("biometric_enabled", "0") == "1" else 0
    if emp.biometric_enabled:
        emp.biometric_id = post.get("biometric_id", "").strip() or None
    else:
        emp.biometric_id = None
    emp.address_line1 = post.get("address_line1", "").strip()
    emp.address_line2 = post.get("address_line2", "").strip()
    emp.city = post.get("city", "").strip()
    emp.district = post.get("district", "").strip()
    emp.state = post.get("state", "").strip()
    emp.country = post.get("country", "").strip()
    emp.pin_code = post.get("pin_code", "").strip()
    emp.present_addr = addr
    emp.perm_addr = addr
    emp.join_date = post.get("joining_date") or None
    emp.end_date = post.get("end_date") or None
    emp.emp_type = ""
    emp.check_in = post.get("check_in") or None
    emp.check_out = post.get("check_out") or None
    emp.dept = post.get("department_name", "")
    emp.desig = post.get("designation_name", "")
    emp.salary_type = post.get("salary_type", "Monthly")
    emp.salary_amt = post.get("salary_amount", "")
    emp.education = post.get("education", "").strip()
    emp.work_experience = post.get("work_experience", "").strip()
    emp.employment_status = post.get("employment_status", "Active")
    emp.shift = post.get("shift", "").strip()
    emp.work_mode = post.get("work_mode", "").strip()
    emp.pan_no = post.get("pan_no", "").strip()
    emp.aadhar_no = post.get("aadhar_no", "").strip()
    emp.passport_no = post.get("passport_no", "").strip()
    emp.driving_license = post.get("driving_license", "").strip()
    notice = post.get("notice_period_days", "").strip()
    emp.notice_period_days = int(notice) if notice.isdigit() else None
    emp.full_abs_fine = post.get("full_day_absence_fine", "") or None
    emp.half_abd_fine = post.get("half_day_absence_fine", "") or None
    emp.yearly_leaves = post.get("yearly_leave_limit", "") or None
    emp.bank_name = post.get("bank_name", "")
    emp.branch_name = post.get("branch_name", "")
    emp.account_name = post.get("account_name", "")
    emp.account_no = post.get("account_number", "")
    emp.ifsc_code = post.get("ifsc_code", "")
    emp.gps_tracking = 1 if post.get("gps_tracking", "1") == "1" else 0
    emp.late_attendance_penalty = (
        1 if post.get("late_attendance_penalty", "1") == "1" else 0
    )
    emp.photo_selfie = 1 if post.get("photo_selfie", "1") == "1" else 0
    emp.week_off = _week_off_from_post(post)
    emp.blood_group = post.get("blood_group", "")
    emp.father_name = post.get("father_name", "")
    emp.emergency_contact = post.get("emergency_contact", "").strip()
    emp.total_yearly_leaves = emp.yearly_leaves or "0"
    emp.profile_photo = emp.profile_photo or ""


def _employee_salary_context(emp_id=None):
    emp_items = list(EmpItemMaster.objects.filter(emp_id=emp_id)) if emp_id else []
    salary_ctx = get_salary_structure_for_form(emp_items or None)
    return {
        **salary_ctx,
        "other_emp_items": get_other_emp_items(emp_items) if emp_items else [],
    }


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def employee_add(request):
    departments = DeptMaster.objects.all()
    designations = DesigMaster.objects.all()
    prefill = None
    reg_id = request.GET.get("reg_id") or request.POST.get("reg_id")
    candidate_id = request.GET.get("candidate_id") or request.POST.get("candidate_id")
    if reg_id:
        try:
            prefill = EmpTemp.objects.get(id=reg_id)
        except EmpTemp.DoesNotExist:
            reg_id = None
    elif candidate_id:
        try:
            from .models import RecruitmentCandidate

            cand = RecruitmentCandidate.objects.get(id=candidate_id)

            class _CandPrefill:
                contact = cand.phone
                full_name = cand.full_name
                email = cand.email
                dob = cand.dob
                gender = cand.gender
                father_name = ""
                emergency_contact = ""
                blood_group = ""
                address = ""
                bank_name = ""
                branch_name = ""
                account_name = cand.full_name
                account_number = ""
                ifsc_code = ""

            prefill = _CandPrefill()
        except Exception:
            candidate_id = None

    def render_form():
        next_id = _next_auto_emp_id()
        salary_ctx = get_salary_structure_for_form()
        return render(
            request,
            "accounts/employee_add.html",
            {
                "departments": departments,
                "designations": designations,
                "prefill": prefill,
                "reg_id": reg_id,
                "candidate_id": candidate_id,
                "next_emp_id": next_id,
                "suggested_emp_code": _suggested_employee_code(next_id),
                "week_off_days": {5, 6},
                "weekday_short": WEEKDAY_SHORT,
                "shifts": get_active_shifts(),
                "other_emp_items": [],
                **salary_ctx,
                **get_subscription_context(),
            },
        )

    if not can_add_employee(request.user):
        from .subscription_utils import _debug_sub_log

        _debug_sub_log(
            "views.py:employee_add",
            "employee limit reached",
            {
                "count": count_employees(),
                "limit": get_employee_limit(),
                "paid": has_paid_subscription(),
            },
        )
        messages.warning(request, employee_limit_message())
        return redirect(get_subscribe_url())

    if request.method == "POST":
        mobile_no = request.POST.get("mobile_no", "").strip()
        email = request.POST.get("email", "").strip()
        full_name = request.POST.get("full_name", "").strip()

        if not mobile_no or len(mobile_no) != 10 or not mobile_no.isdigit():
            messages.error(request, "Mobile number must be exactly 10 digits")
            return render_form()

        salary_type = request.POST.get("salary_type", "").strip()
        if salary_type not in ("Monthly", "Hourly"):
            messages.error(request, "Please select a valid salary type (Monthly or Hourly).")
            return render_form()

        if not reg_id:
            if Users.objects.filter(contact=mobile_no).exists():
                messages.error(
                    request, "This mobile number is already used by a portal user account"
                )
                return render_form()
            if Users.objects.filter(email=email).exists():
                messages.error(
                    request, "This email is already used by a portal user account"
                )
                return render_form()

        emp = EmpMaster()
        _populate_employee_from_post(emp, request)
        emp.emp_id = _next_auto_emp_id()
        if not emp.employee_code:
            emp.employee_code = _suggested_employee_code(emp.emp_id)
        if _biometric_id_taken(emp.biometric_id):
            messages.error(request, "Biometric ID is already assigned to another employee.")
            return render_form()
        if emp.biometric_enabled and not emp.biometric_id:
            messages.error(request, "Biometric ID is required when Biometric is On.")
            return render_form()
        emp.save()

        ensure_employee_auth_account(emp)

        # Save Additional Details (EmpItemMaster)
        item_names = request.POST.getlist("item_name[]")
        item_amts = request.POST.getlist("item_amt[]")
        item_amt_types = request.POST.getlist("item_amt_type[]")
        item_types = request.POST.getlist("item_type[]")

        for i in range(len(item_names)):
            if item_names[i]:  # Only save if name is provided
                emp_item = EmpItemMaster()
                emp_item.emp_id = emp.emp_id
                emp_item.item_name = item_names[i]
                emp_item.item_amt = item_amts[i] if item_amts[i] else None
                emp_item.item_amt_type = (
                    item_amt_types[i] if item_amt_types[i] else None
                )
                emp_item.item_type = item_types[i] if item_types[i] else None
                emp_item.save()

        # If coming from registration approval, mark EmpTemp as approved (no web login)
        reg_id = request.POST.get("reg_id")
        if reg_id:
            try:
                reg_request = EmpTemp.objects.get(id=reg_id)
                if reg_request.status == "PENDING":
                    reg_request.status = "APPROVED"
                    reg_request.save()
            except EmpTemp.DoesNotExist:
                pass

        candidate_id_post = request.POST.get("candidate_id")
        if candidate_id_post:
            try:
                from django.utils import timezone
                from .models import RecruitmentCandidate

                cand = RecruitmentCandidate.objects.get(id=candidate_id_post)
                cand.status = "Hired"
                cand.save(update_fields=["status"])
                joining = getattr(cand, "joining", None)
                if joining:
                    joining.emp_id = str(emp.emp_id)
                    joining.status = "Completed"
                    joining.completed_at = timezone.now()
                    joining.save()
            except Exception:
                pass

        messages.success(
            request,
            "Employee successfully added. Login with mobile number or Employee ID. "
            "Default password: last 4 digits of mobile.",
        )
        return redirect("employee_list")

    return render_form()


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def employee_edit(request, id):
    obj = get_object_or_404(EmpMaster, id=id)

    if request.method == "POST":
        _populate_employee_from_post(obj, request)
        if _biometric_id_taken(obj.biometric_id, exclude_emp_id=obj.emp_id):
            messages.error(request, "Biometric ID is already assigned to another employee.")
            departments = DeptMaster.objects.all()
            designations = DesigMaster.objects.all()
            return render(
                request,
                "accounts/employee_edit.html",
                {
                    "employee": obj,
                    "departments": departments,
                    "designations": designations,
                    "week_off_days": _parse_week_off_days(obj),
                    "weekday_short": WEEKDAY_SHORT,
                    "shifts": get_active_shifts(),
                    **_employee_salary_context(obj.emp_id),
                },
            )
        if obj.biometric_enabled and not obj.biometric_id:
            messages.error(request, "Biometric ID is required when Biometric is On.")
            departments = DeptMaster.objects.all()
            designations = DesigMaster.objects.all()
            return render(
                request,
                "accounts/employee_edit.html",
                {
                    "employee": obj,
                    "departments": departments,
                    "designations": designations,
                    "week_off_days": _parse_week_off_days(obj),
                    "weekday_short": WEEKDAY_SHORT,
                    "shifts": get_active_shifts(),
                    **_employee_salary_context(obj.emp_id),
                },
            )
        obj.save()
        ensure_employee_auth_account(obj)

        # Handle Additional Details (EmpItemMaster)
        # Delete existing items for this employee
        EmpItemMaster.objects.filter(emp_id=obj.emp_id).delete()

        # Save new items
        item_names = request.POST.getlist("item_name[]")
        item_amts = request.POST.getlist("item_amt[]")
        item_amt_types = request.POST.getlist("item_amt_type[]")
        item_types = request.POST.getlist("item_type[]")

        for i in range(len(item_names)):
            if item_names[i]:  # Only save if name is provided
                emp_item = EmpItemMaster()
                emp_item.emp_id = obj.emp_id
                emp_item.item_name = item_names[i]
                emp_item.item_amt = item_amts[i] if item_amts[i] else None
                emp_item.item_amt_type = (
                    item_amt_types[i] if item_amt_types[i] else None
                )
                emp_item.item_type = item_types[i] if item_types[i] else None
                emp_item.save()

        messages.success(request, "Employee updated successfully")
        return redirect("employee_list")

    departments = DeptMaster.objects.all()
    designations = DesigMaster.objects.all()
    context = {
        "employee": obj,
        "departments": departments,
        "designations": designations,
        "week_off_days": _parse_week_off_days(obj),
        "weekday_short": WEEKDAY_SHORT,
        "shifts": get_active_shifts(),
        **_employee_salary_context(obj.emp_id),
    }
    return render(request, "accounts/employee_edit.html", context)


@login_required(login_url="login")
@permission_required("accounts.delete_empmaster", raise_exception=True)
def employee_delete(request, id):
    obj = get_object_or_404(EmpMaster, id=id)
    obj.delete()
    messages.success(request, "Employee deleted")
    return redirect("employee_list")


def designation_list(request):
    designations = DesigMaster.objects.all()
    context = {"designations": designations}
    return render(request, "accounts/designation_list.html", context)


def designation_edit(request, id):
    obj = get_object_or_404(DesigMaster, id=id)
    if request.method == "POST":
        dept = request.POST.get("department_name", "")
        name = request.POST.get("designation_name", "")
        obj.dept_name = dept
        obj.desig_name = name
        obj.save()
        messages.success(request, "Designation updated")
        return redirect("designation_list")
    context = {"designation": obj}
    return render(request, "accounts/designation_edit.html", context)


def designation_delete(request, id):
    obj = get_object_or_404(DesigMaster, id=id)
    obj.delete()
    messages.success(request, "Designation deleted")
    return redirect("designation_list")


# ==================== ATTENDANCE ====================
@login_required(login_url="login")
def attendance_list(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )
    if is_restricted_user:
        emp = find_emp_for_auth_user(request.user)
        if emp:
            try:
                attendance = AttendanceMaster.objects.filter(
                    emp_id=int(emp.emp_id)
                ).order_by("-att_date")
            except ValueError:
                attendance = AttendanceMaster.objects.none()
        else:
            attendance = AttendanceMaster.objects.none()
    else:
        attendance = AttendanceMaster.objects.all().order_by("-att_date")

    # Apply filters from GET params
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if date_from:
        attendance = attendance.filter(att_date__gte=date_from)
    if date_to:
        attendance = attendance.filter(att_date__lte=date_to)
    if status_filter:
        attendance = attendance.filter(attendance_status__iexact=status_filter)

    attendance = _attach_gps_status(attendance)

    context = {
        "attendance": attendance,
        "is_restricted_user": is_restricted_user,
        "date_from": date_from,
        "date_to": date_to,
        "status_filter": status_filter,
    }
    return render(request, "accounts/attendance_list.html", context)


@login_required(login_url="login")
def attendance_detail(request, id):
    """View a single attendance record with check-in info and movement map."""
    import json as _json

    att = get_object_or_404(AttendanceMaster, id=id)

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    # Restricted users can only view their own records
    if is_restricted_user:
        emp = find_emp_for_auth_user(request.user)
        if not emp:
            messages.error(request, "Access denied!")
            return redirect("attendance_list")
        try:
            if att.emp_id != int(emp.emp_id):
                messages.error(request, "Access denied!")
                return redirect("attendance_list")
        except ValueError:
            messages.error(request, "Access denied!")
            return redirect("attendance_list")

    locations = _get_location_records(att.emp_id, att.att_date)
    location_points = _build_location_points(locations)
    gps_code = _infer_location_status(att)
    gps_label, gps_badge = LOCATION_STATUS_META.get(gps_code, ("Unknown", "secondary"))

    context = {
        "att": att,
        "location_points_json": _json.dumps(location_points),
        "location_count": len(location_points),
        "is_restricted_user": is_restricted_user,
        "gps_status_label": gps_label,
        "gps_status_badge": gps_badge,
        "checkin_photo_url": _resolve_attendance_photo_url(att.photo),
        "checkout_photo_url": _resolve_attendance_photo_url(att.out_photo),
    }
    return render(request, "accounts/attendance_detail.html", context)


def _get_own_employee(request):
    return find_emp_for_auth_user(request.user)


def _employee_gps_enabled(emp):
    if not geo_location_enabled():
        return False
    if emp is None:
        return True
    val = getattr(emp, "gps_tracking", None)
    if val is None:
        return True
    try:
        return int(val) != 0
    except (TypeError, ValueError):
        return True


LOCATION_STATUS_META = {
    "gps_ok": ("GPS Captured", "success"),
    "gps_off_account": ("GPS Off (Admin Setting)", "secondary"),
    "gps_off_mobile": ("GPS Off (Mobile)", "danger"),
    "gps_denied": ("Location Permission Denied", "danger"),
    "gps_unavailable": ("GPS Unavailable", "warning"),
    "gps_timeout": ("GPS Signal Timeout", "warning"),
    "gps_missing": ("GPS Not Captured", "warning"),
}


def _coords_valid(lat, lng):
    try:
        return not (float(lat) == 0 and float(lng) == 0)
    except (TypeError, ValueError):
        return False


def _resolve_location_status(gps_enabled, lat, lng, posted_status=""):
    posted = (posted_status or "").strip()
    if posted in LOCATION_STATUS_META:
        return posted
    if not gps_enabled:
        return "gps_off_account"
    if _coords_valid(lat, lng):
        return "gps_ok"
    return "gps_missing"


def _infer_location_status(att):
    stored = getattr(att, "location_status", None) or ""
    if stored in LOCATION_STATUS_META:
        return stored
    try:
        emp = EmpMaster.objects.get(emp_id=str(att.emp_id))
        gps_on = _employee_gps_enabled(emp)
    except EmpMaster.DoesNotExist:
        gps_on = True
    if not gps_on:
        return "gps_off_account"
    if _coords_valid(att.latitude, att.longitude):
        return "gps_ok"
    return "gps_missing"


def _resolve_attendance_photo_url(photo_path):
    from django.conf import settings

    if not photo_path:
        return ""
    path = str(photo_path).strip()
    if not path:
        return ""
    if path.startswith(("http://", "https://", "data:")):
        return path
    if path.startswith("/"):
        return path
    return f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"


def _attach_gps_status(attendance_qs):
    rows = list(attendance_qs)
    for att in rows:
        code = _infer_location_status(att)
        label, badge = LOCATION_STATUS_META.get(code, ("Unknown", "secondary"))
        att.gps_status_code = code
        att.gps_status_label = label
        att.gps_status_badge = badge
        att.checkin_photo_url = _resolve_attendance_photo_url(att.photo)
        att.checkout_photo_url = _resolve_attendance_photo_url(att.out_photo)
        att.has_selfie = bool(att.checkin_photo_url or att.checkout_photo_url)
    return rows


def _attach_location_counts(attendance_rows):
    for att in attendance_rows:
        att.location_count = _get_location_records(att.emp_id, att.att_date).count()
    return attendance_rows


def _employee_late_penalty_enabled(emp):
    return employee_late_penalty_enabled(emp)


def _employee_photo_selfie_enabled(emp):
    if emp is None:
        return True
    val = getattr(emp, "photo_selfie", None)
    if val is None:
        return True
    try:
        return int(val) != 0
    except (TypeError, ValueError):
        return True


def _attendance_status_for_check_in(emp, check_in_time, att_date):
    return attendance_status_for_check_in(emp, check_in_time, att_date)


def _resolve_office_check_in(emp):
    return get_scheduled_check_in(emp)


def _employee_tracking_id(emp):
    try:
        return str(int(emp.emp_id))
    except (ValueError, TypeError):
        return str(emp.emp_id)


def _tracking_emp_id_variants(emp_id):
    values = {str(emp_id)}
    try:
        values.add(str(int(emp_id)))
    except (ValueError, TypeError):
        pass

    try:
        emp = EmpMaster.objects.get(emp_id=str(emp_id))
        values.add(_employee_tracking_id(emp))
        values.add(str(emp.emp_id))
    except EmpMaster.DoesNotExist:
        pass

    try:
        numeric = int(emp_id)
        for emp in EmpMaster.objects.all():
            try:
                if int(emp.emp_id) == numeric:
                    values.add(_employee_tracking_id(emp))
                    values.add(str(emp.emp_id))
                    break
            except (ValueError, TypeError):
                continue
    except (ValueError, TypeError):
        pass

    return list(values)


def _haversine_meters(lat1, lng1, lat2, lng2):
    from math import asin, cos, radians, sin, sqrt

    r = 6371000
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _get_location_records(emp_id, session_date):
    from .models import EmployeeLocationTracking

    return EmployeeLocationTracking.objects.filter(
        emp_id__in=_tracking_emp_id_variants(emp_id),
        session_date=session_date,
    ).order_by("timestamp")


def _build_location_points(locations):
    return [
        {
            "lat": float(loc.latitude),
            "lng": float(loc.longitude),
            "timestamp": loc.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "is_checkin": loc.is_checkin_point,
            "is_checkout": getattr(loc, "is_checkout_point", False),
        }
        for loc in locations
    ]


def _has_active_checkin(emp, session_date):
    try:
        emp_id_int = int(emp.emp_id)
    except (ValueError, TypeError):
        return False
    return AttendanceMaster.objects.filter(
        emp_id=emp_id_int,
        att_date=session_date,
        check_out__isnull=True,
    ).exists()


def _save_tracking_point(
    user,
    emp,
    latitude,
    longitude,
    session_date,
    is_checkin=False,
    is_checkout=False,
):
    from datetime import timedelta
    from decimal import Decimal, InvalidOperation

    from django.utils import timezone

    from .models import EmployeeLocationTracking

    try:
        lat = float(latitude)
        lng = float(longitude)
    except (TypeError, ValueError):
        return False

    if lat == 0 and lng == 0:
        return False

    emp_key = _employee_tracking_id(emp)

    if is_checkin and EmployeeLocationTracking.objects.filter(
        emp_id=emp_key, session_date=session_date, is_checkin_point=True
    ).exists():
        return False

    if is_checkout and EmployeeLocationTracking.objects.filter(
        emp_id=emp_key, session_date=session_date, is_checkout_point=True
    ).exists():
        return False

    if not is_checkin and not is_checkout:
        recent = (
            EmployeeLocationTracking.objects.filter(
                emp_id=emp_key,
                session_date=session_date,
            )
            .order_by("-timestamp")
            .first()
        )
        if recent:
            age = timezone.now() - recent.timestamp
            dist = _haversine_meters(
                float(recent.latitude),
                float(recent.longitude),
                lat,
                lng,
            )
            if age < timedelta(minutes=2) and dist < 30:
                return False
            if age < timedelta(minutes=3) and dist < 50:
                return False

    try:
        EmployeeLocationTracking.objects.create(
            user_id=user.id if user else 0,
            emp_id=emp_key,
            full_name=emp.full_name or "",
            latitude=Decimal(str(round(lat, 8))),
            longitude=Decimal(str(round(lng, 8))),
            session_date=session_date,
            is_checkin_point=is_checkin,
            is_checkout_point=is_checkout,
        )
    except (InvalidOperation, ValueError):
        return False
    return True


def _employee_attendance_state(own_emp):
    from datetime import date

    today = date.today()
    today_attendance = AttendanceMaster.objects.filter(
        emp_id=int(own_emp.emp_id), att_date=today
    ).first()
    checkout_mode = bool(
        today_attendance and today_attendance.check_in and not today_attendance.check_out
    )
    attendance_completed = bool(
        today_attendance and today_attendance.check_in and today_attendance.check_out
    )
    return today, today_attendance, checkout_mode, attendance_completed


def _handle_employee_attendance_post(request, own_emp, action):
    from datetime import date as date_cls, datetime, timedelta
    from decimal import Decimal

    redirect_name = "employee_checkout" if action == "check_out" else "employee_checkin"
    photo_data = request.POST.get("photo_data", "").strip()
    latitude = request.POST.get("latitude", "0") or "0"
    longitude = request.POST.get("longitude", "0") or "0"
    location_status_post = request.POST.get("location_status", "").strip()
    today = date_cls.today()
    now_time = datetime.now().time()
    emp_id_int = int(own_emp.emp_id)
    selfie_enabled = _employee_photo_selfie_enabled(own_emp)

    if selfie_enabled and not photo_data:
        messages.error(request, "Selfie is required. Please capture your photo.")
        return redirect(redirect_name)

    gps_enabled = _employee_gps_enabled(own_emp)
    loc_status = _resolve_location_status(
        gps_enabled, latitude, longitude, location_status_post
    )
    if gps_enabled and not _coords_valid(latitude, longitude):
        err_msgs = {
            "gps_denied": "Location permission denied. Enable GPS/Location in mobile settings.",
            "gps_unavailable": "GPS is off on your mobile. Turn on Location and try again.",
            "gps_timeout": "GPS signal timeout. Move to open area and retry.",
            "gps_off_mobile": "GPS is off on your mobile. Turn on Location and try again.",
        }
        messages.error(
            request,
            err_msgs.get(loc_status, "Location is required. Please enable GPS on your mobile."),
        )
        return redirect(redirect_name)

    if not gps_enabled:
        latitude = "0"
        longitude = "0"
        loc_status = "gps_off_account"

    if action == "check_out":
        att = AttendanceMaster.objects.filter(
            emp_id=emp_id_int, att_date=today, check_out__isnull=True
        ).first()
        if not att:
            messages.error(request, "No active check-in found for today.")
            return redirect("employee_checkin")

        att.check_out = now_time
        att.out_photo = (
            _save_base64_photo(photo_data, "checkout") if selfie_enabled and photo_data else None
        )
        att.out_lati = latitude
        att.out_long = longitude
        ci = datetime.combine(today, att.check_in)
        co = datetime.combine(today, now_time)
        if co < ci:
            co += timedelta(days=1)
        att.worked_hours = round(Decimal(str((co - ci).total_seconds() / 3600)), 2)
        att.worked_day = "Full Day"
        att.save()
        if gps_enabled:
            _save_tracking_point(
                request.user,
                own_emp,
                latitude,
                longitude,
                today,
                is_checkout=True,
            )
        messages.success(request, "Checked out successfully!")
        return redirect("attendance_list")

    existing = AttendanceMaster.objects.filter(emp_id=emp_id_int, att_date=today).first()
    if existing:
        if existing.check_out:
            messages.error(request, "You have already completed attendance for today.")
        else:
            messages.info(request, "You are already checked in. Please check out.")
            return redirect("employee_checkout")
        return redirect("employee_checkin")

    AttendanceMaster.objects.create(
        emp_id=emp_id_int,
        full_name=own_emp.full_name or "",
        att_date=today,
        check_in=now_time,
        attendance_status=_attendance_status_for_check_in(own_emp, now_time, today),
        worked_day="",
        latitude=latitude,
        longitude=longitude,
        location_status=loc_status,
        photo=_save_base64_photo(photo_data, "checkin") if selfie_enabled and photo_data else None,
        out_lati="0",
        out_long="0",
    )
    if gps_enabled:
        _save_tracking_point(
            request.user,
            own_emp,
            latitude,
            longitude,
            today,
            is_checkin=True,
        )
    messages.success(request, "Checked in successfully!")
    return redirect("attendance_list")


def _employee_attendance_page(request, page_mode):
    own_emp = _get_own_employee(request)
    if own_emp is None:
        messages.error(
            request, "Access denied! No employee record linked to your account."
        )
        return redirect("home")

    if request.method == "POST":
        return _handle_employee_attendance_post(request, own_emp, page_mode)

    today, today_attendance, checkout_mode, attendance_completed = (
        _employee_attendance_state(own_emp)
    )

    if page_mode == "check_in":
        if attendance_completed:
            messages.info(request, "Today's attendance is already completed.")
            return redirect("attendance_list")
        if checkout_mode:
            messages.info(request, "You are already checked in. Use Check Out.")
            return redirect("employee_checkout")
    elif page_mode == "check_out":
        if attendance_completed:
            messages.info(request, "Today's attendance is already completed.")
            return redirect("attendance_list")
        if not checkout_mode:
            messages.warning(request, "Please check in first.")
            return redirect("employee_checkin")

    return render(
        request,
        "accounts/employee_checkin.html",
        {
            "own_emp": own_emp,
            "today": today.strftime("%Y-%m-%d"),
            "today_attendance": today_attendance,
            "checkout_mode": checkout_mode,
            "attendance_completed": attendance_completed,
            "page_mode": page_mode,
            "gps_enabled": _employee_gps_enabled(own_emp),
            "selfie_enabled": _employee_photo_selfie_enabled(own_emp),
            "gps_locked_free_plan": not geo_location_enabled(),
        },
    )


@login_required(login_url="login")
def employee_checkin(request):
    return _employee_attendance_page(request, "check_in")


@login_required(login_url="login")
def employee_checkout(request):
    return _employee_attendance_page(request, "check_out")


@login_required(login_url="login")
def attendance_add(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    # Check permissions: Either have add_attendancemaster permission OR be a restricted user
    if not (
        request.user.has_perm("accounts.add_attendancemaster") or is_restricted_user
    ):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("You don't have permission to add attendance records.")

    # For restricted users, resolve their own employee record
    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)

    # Customers (no EmpMaster record) must not access employee attendance
    if is_restricted_user and own_emp is None:
        messages.error(
            request, "Access denied! No employee record linked to your account."
        )
        return redirect("home")

    if is_restricted_user:
        return redirect("employee_checkin")

    if request.method == "POST":
        from datetime import date as date_cls, datetime

        emp_id = request.POST.get("emp_id", "")
        att_date = request.POST.get("att_date", "")
        check_in = request.POST.get("check_in", "")
        check_out = request.POST.get("check_out", "") or None
        attendance_status = request.POST.get("attendance_status", "")
        worked_day = request.POST.get("worked_day", "")
        latitude = request.POST.get("latitude", "0")
        longitude = request.POST.get("longitude", "0")
        location_status_post = request.POST.get("location_status", "").strip()

        # --- Validation: One attendance record per employee per day ---
        if emp_id and att_date:
            duplicate = AttendanceMaster.objects.filter(
                emp_id=int(emp_id), att_date=att_date
            ).exists()
            if duplicate:
                messages.error(
                    request,
                    "Attendance for this employee on the selected date has already been added. "
                    "If you need to add a check-out time, please use the Edit option.",
                )
                return redirect("attendance_add")

        # Get employee name from emp_id
        emp = None
        try:
            emp = EmpMaster.objects.get(emp_id=emp_id)
            full_name = emp.full_name
            if emp and check_in and att_date and attendance_status == "Present":
                from datetime import datetime as dt_cls

                att_date_obj = (
                    att_date
                    if hasattr(att_date, "year")
                    else date_cls.fromisoformat(str(att_date))
                )
                if isinstance(check_in, str):
                    fmt = "%H:%M:%S" if len(check_in.split(":")) > 2 else "%H:%M"
                    check_in_time = dt_cls.strptime(check_in, fmt).time()
                else:
                    check_in_time = check_in
                attendance_status = _attendance_status_for_check_in(
                    emp, check_in_time, att_date_obj
                )
        except EmpMaster.DoesNotExist:
            full_name = ""
        except Exception:
            full_name = emp.full_name if emp else ""

        att = AttendanceMaster()
        att.emp_id = int(emp_id) if emp_id else 0
        att.full_name = full_name
        att.att_date = att_date
        att.check_in = check_in
        att.check_out = check_out
        att.attendance_status = attendance_status
        att.worked_day = worked_day or ("Full Day" if check_out else "")
        att.latitude = latitude
        att.longitude = longitude
        gps_on = _employee_gps_enabled(emp) if emp else True
        att.location_status = _resolve_location_status(
            gps_on, latitude, longitude, location_status_post
        )
        att.out_lati = "0"
        att.out_long = "0"

        if check_in and check_out:
            from datetime import timedelta
            from decimal import Decimal

            fmt = "%H:%M:%S" if len(str(check_in).split(":")) > 2 else "%H:%M"
            ci = datetime.strptime(str(check_in), fmt).time()
            co = datetime.strptime(
                str(check_out),
                "%H:%M:%S" if len(str(check_out).split(":")) > 2 else "%H:%M",
            ).time()
            ci_dt = datetime.combine(date_cls.today(), ci)
            co_dt = datetime.combine(date_cls.today(), co)
            if co_dt <= ci_dt:
                co_dt += timedelta(days=1)
            att.worked_hours = round(
                Decimal(str((co_dt - ci_dt).total_seconds() / 3600)), 2
            )

        att.save()

        messages.success(request, "Attendance added successfully")
        return redirect("attendance_list")

    from datetime import date

    employees = EmpMaster.objects.all()
    context = {
        "employees": employees,
        "today": date.today().strftime("%Y-%m-%d"),
        "is_restricted_user": is_restricted_user,
        "own_emp": own_emp,
    }
    return render(request, "accounts/attendance_add.html", context)


@login_required(login_url="login")
def attendance_edit(request, id):
    """
    Allow adding a missed check-out time to an existing attendance record.
    Only allowed when check_out is currently blank/null.
    """
    from datetime import datetime, date as date_cls

    attendance = get_object_or_404(AttendanceMaster, id=id)

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    # Restricted users can only edit their own record
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")
        try:
            if attendance.emp_id != int(own_emp.emp_id):
                messages.error(
                    request, "You can only edit your own attendance records."
                )
                return redirect("attendance_list")
        except ValueError:
            messages.error(request, "Access denied!")
            return redirect("attendance_list")

    # Only allow editing if check_out is missing
    if attendance.check_out:
        messages.warning(
            request, "Check-out time has already been recorded for this attendance."
        )
        return redirect("attendance_list")

    # Restricted users can only check out for today's record
    if is_restricted_user and attendance.att_date != date_cls.today():
        messages.error(
            request, "Check-out can only be recorded for today's attendance."
        )
        return redirect("attendance_list")

    if request.method == "POST":
        check_out = request.POST.get("check_out", "").strip()
        if not check_out:
            messages.error(request, "Please enter a valid check-out time.")
        else:
            # Parse and validate check_out > check_in
            try:
                check_out_time = datetime.strptime(check_out, "%H:%M").time()
                if check_out_time <= attendance.check_in:
                    messages.error(
                        request, "Check-out time must be after check-in time."
                    )
                else:
                    attendance.check_out = check_out_time
                    # Calculate worked hours
                    from decimal import Decimal

                    ci = datetime.combine(date_cls.today(), attendance.check_in)
                    co = datetime.combine(date_cls.today(), check_out_time)
                    diff = (co - ci).total_seconds() / 3600
                    attendance.worked_hours = round(Decimal(str(diff)), 2)
                    attendance.save()
                    messages.success(request, "Check-out time updated successfully.")
                    return redirect("attendance_list")
            except ValueError:
                messages.error(request, "Invalid check-out time format.")

    context = {
        "attendance": attendance,
    }
    return render(request, "accounts/attendance_edit.html", context)


def attendance_req_list(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )
    if is_restricted_user:
        emp = find_emp_for_auth_user(request.user)
        if emp:
            requests = AttendanceReq.objects.filter(emp_id=emp.emp_id).order_by(
                "-created_at"
            )
        else:
            requests = AttendanceReq.objects.none()
    else:
        requests = AttendanceReq.objects.all().order_by("-created_at")
    context = {"requests": requests, "is_restricted_user": is_restricted_user}
    return render(request, "accounts/attendance_req_list.html", context)


def attendance_req_status_update(request, id):
    if request.method == "POST":
        try:
            req = AttendanceReq.objects.get(id=id)
            status = request.POST.get("status", "Pending")
            req.approval_status = status
            req.save()
            messages.success(request, "Attendance request status updated successfully")
        except AttendanceReq.DoesNotExist:
            messages.error(request, "Attendance request not found")
    return redirect("attendance_req_list")


def attendance_req_add(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)

    if request.method == "POST":
        if is_restricted_user:
            emp_id = str(own_emp.emp_id) if own_emp else ""
        else:
            emp_id = request.POST.get("emp_id", "")
        reg_date = request.POST.get("reg_date", "")
        check_in = request.POST.get("check_in", "")
        check_out = request.POST.get("check_out", "")
        reason = request.POST.get("reason", "")
        attachment = request.POST.get("attachment", "")
        status = request.POST.get("status", "Pending")

        # Get employee name from emp_id
        try:
            emp = EmpMaster.objects.get(emp_id=emp_id)
            full_name = emp.full_name
        except:
            full_name = ""

        req = AttendanceReq()
        req.emp_id = emp_id
        req.full_name = full_name
        req.reg_date = reg_date
        req.check_in = check_in
        req.check_out = check_out
        req.reason = reason
        req.attachment = attachment or ""
        req.approval_status = "Pending"
        req.status = status
        req.save()

        messages.success(request, "Attendance request submitted successfully")
        return redirect("attendance_req_list")

    from datetime import date

    if is_restricted_user:
        employees = [own_emp] if own_emp else []
    else:
        employees = EmpMaster.objects.all()
    context = {
        "employees": employees,
        "today": date.today().strftime("%Y-%m-%d"),
        "is_restricted_user": is_restricted_user,
        "own_emp": own_emp,
    }
    return render(request, "accounts/attendance_req_add.html", context)


# ==================== LEAVES ====================
@login_required(login_url="login")
def leave_list(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if own_emp:
            try:
                leaves = LeaveRequest.objects.filter(emp_id=int(own_emp.emp_id)).order_by(
                    "-applied_at"
                )
            except ValueError:
                leaves = LeaveRequest.objects.none()
        else:
            leaves = LeaveRequest.objects.none()
    else:
        if not request.user.has_perm("accounts.view_leaverequest"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        leaves = LeaveRequest.objects.all().order_by("-applied_at")

    context = {
        "leaves": leaves,
        "is_restricted_user": is_restricted_user,
    }
    return render(request, "accounts/leave_list.html", context)


@login_required(login_url="login")
def leave_add(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")
    elif not request.user.has_perm("accounts.add_leaverequest"):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied

    if request.method == "POST":
        if is_restricted_user:
            emp_id = str(own_emp.emp_id)
        else:
            emp_id = request.POST.get("emp_id", "")
        leave_type = request.POST.get("leave_type", "")
        start_date = request.POST.get("start_date", "")
        end_date = request.POST.get("end_date", "")
        leave_duration = request.POST.get("leave_duration", "")
        reason = request.POST.get("reason", "")
        is_paid = request.POST.get("is_paid", "1")

        # Get employee name from emp_id
        try:
            emp = EmpMaster.objects.get(emp_id=emp_id)
            full_name = emp.full_name
            yearly_leaves = emp.yearly_leaves or 0
        except:
            full_name = ""
            yearly_leaves = 0

        leave = LeaveRequest()
        leave.emp_id = int(emp_id) if emp_id else 0
        leave.full_name = full_name
        leave.leave_type = leave_type
        leave.start_date = start_date
        leave.end_date = end_date
        leave.leave_duration = leave_duration
        leave.reason = reason
        leave.is_paid = int(is_paid)
        leave.leave_status = 0  # Pending
        leave.yearly_leaves = yearly_leaves
        leave.total_leaves = 0
        leave.save()

        messages.success(request, "Leave request submitted successfully")
        return redirect("leave_list")

    employees = [own_emp] if is_restricted_user else EmpMaster.objects.all()
    context = {
        "employees": employees,
        "is_restricted_user": is_restricted_user,
        "own_emp": own_emp,
    }
    return render(request, "accounts/leave_add.html", context)


def leave_approval_list(request):
    # Show all leave requests for approval management
    leaves = LeaveRequest.objects.all().order_by("-applied_at")
    context = {"leaves": leaves}
    return render(request, "accounts/leave_approval_list.html", context)


def leave_status_update(request, id):
    if request.method == "POST":
        try:
            leave = LeaveRequest.objects.get(id=id)
            status = request.POST.get("status", "0")
            leave.leave_status = int(status)
            leave.save()
            messages.success(request, "Leave status updated successfully")
        except LeaveRequest.DoesNotExist:
            messages.error(request, "Leave request not found")
    return redirect("leave_approval_list")


def leave_approve(request, id):
    try:
        leave = LeaveRequest.objects.get(id=id)
        leave.leave_status = 1  # Approved
        leave.save()
        messages.success(request, "Leave request approved successfully")
    except LeaveRequest.DoesNotExist:
        messages.error(request, "Leave request not found")
    return redirect("leave_approval_list")


def leave_reject(request, id):
    try:
        leave = LeaveRequest.objects.get(id=id)
        leave.leave_status = 2  # Rejected
        leave.save()
        messages.success(request, "Leave request rejected")
    except LeaveRequest.DoesNotExist:
        messages.error(request, "Leave request not found")
    return redirect("leave_approval_list")


# ==================== HOLIDAY ====================
@login_required(login_url="login")
def holiday_list(request):
    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )
    holidays = HolidayMaster.objects.all().order_by("holiday_date")
    context = {"holidays": holidays, "is_restricted_user": is_restricted_user}
    return render(request, "accounts/holiday_list.html", context)


@login_required(login_url="login")
@permission_required("accounts.add_holidaymaster", raise_exception=True)
def holiday_add(request):
    if request.method == "POST":
        title = request.POST.get("holiday_title", "")
        date = request.POST.get("holiday_date", "")
        if title and date:
            holiday = HolidayMaster()
            holiday.holiday_tital = title
            holiday.holiday_date = date
            holiday.save()
            messages.success(request, "Holiday added successfully")
            return redirect("holiday_list")
    return render(request, "accounts/holiday_add.html")


def holiday_delete(request, id):
    obj = get_object_or_404(HolidayMaster, id=id)
    obj.delete()
    messages.success(request, "Holiday deleted")
    return redirect("holiday_list")


# ==================== SHIFT MANAGEMENT ====================
@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def shift_list(request):
    from datetime import date

    from .shift_rotation_utils import (
        get_employee_rotation_schedule,
        get_employees_on_shift,
        get_rotation_periods,
        get_shift_rotation_config,
        is_shift_rotation_enabled,
    )

    ensure_default_shifts()

    if request.method == "POST" and request.POST.get("action") == "assign_shift":
        emp_pk = request.POST.get("employee_id", "").strip()
        shift_name = request.POST.get("shift_name", "").strip()
        if emp_pk and shift_name:
            emp = EmpMaster.objects.filter(id=emp_pk).first()
            if emp:
                emp.shift = shift_name
                emp.save(update_fields=["shift"])
                messages.success(
                    request,
                    f"{emp.full_name or emp.emp_id} assigned to {shift_name} shift.",
                )
            else:
                messages.error(request, "Employee not found.")
        else:
            messages.error(request, "Select employee and shift.")
        return redirect("shift_list")

    today = date.today()
    rotation_on = is_shift_rotation_enabled()
    rotation_config = get_shift_rotation_config()
    all_employees = list(EmpMaster.objects.all().order_by("full_name", "emp_id"))
    shifts = ShiftMaster.objects.all().order_by("rotation_order", "shift_name")
    rotation_periods = get_rotation_periods(5) if rotation_on else []

    shift_rows = []
    for shift in shifts:
        static_employees = [
            e for e in all_employees if (e.shift or "").strip() == shift.shift_name
        ]
        effective_employees = (
            get_employees_on_shift(shift.shift_name, today, all_employees)
            if rotation_on
            else static_employees
        )
        shift_rows.append(
            {
                "shift": shift,
                "static_employees": static_employees,
                "effective_employees": effective_employees,
                "emp_count": len(effective_employees),
                "static_count": len(static_employees),
            }
        )

    rotation_roster = []
    if rotation_on:
        for emp in all_employees:
            rotation_roster.append(
                {
                    "emp": emp,
                    "profile_shift": (emp.shift or "").strip() or "—",
                    "schedule": get_employee_rotation_schedule(emp, rotation_periods),
                }
            )

    unassigned = [e for e in all_employees if not (e.shift or "").strip()]

    active_shifts = [s for s in shifts if s.is_active]

    return render(
        request,
        "accounts/shift_list.html",
        {
            "shift_rows": shift_rows,
            "all_employees": all_employees,
            "active_shifts": active_shifts,
            "rotation_on": rotation_on,
            "rotation_config": rotation_config,
            "rotation_periods": rotation_periods,
            "rotation_roster": rotation_roster,
            "unassigned": unassigned,
            "today": today,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def shift_add(request):
    if request.method == "POST":
        name = request.POST.get("shift_name", "").strip()
        check_in = request.POST.get("check_in", "").strip()
        check_out = request.POST.get("check_out", "").strip()
        grace = request.POST.get("grace_minutes", "10").strip()
        description = request.POST.get("description", "").strip()
        is_active = 1 if request.POST.get("is_active") == "1" else 0

        if not name or not check_in or not check_out:
            messages.error(request, "Shift name, check-in and check-out are required.")
            return render(request, "accounts/shift_add.html")

        if ShiftMaster.objects.filter(shift_name=name).exists():
            messages.error(request, "Shift name already exists.")
            return render(request, "accounts/shift_add.html")

        rotation_order = int(request.POST.get("rotation_order", "10") or 10)
        ShiftMaster.objects.create(
            shift_name=name,
            check_in=check_in,
            check_out=check_out,
            grace_minutes=int(grace or 10),
            description=description,
            is_active=is_active,
            rotation_order=rotation_order,
        )
        messages.success(request, "Shift added successfully.")
        return redirect("shift_list")

    return render(request, "accounts/shift_add.html")


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def shift_edit(request, id):
    shift = get_object_or_404(ShiftMaster, id=id)
    if request.method == "POST":
        name = request.POST.get("shift_name", "").strip()
        check_in = request.POST.get("check_in", "").strip()
        check_out = request.POST.get("check_out", "").strip()
        grace = request.POST.get("grace_minutes", "10").strip()
        description = request.POST.get("description", "").strip()
        is_active = 1 if request.POST.get("is_active") == "1" else 0

        if not name or not check_in or not check_out:
            messages.error(request, "Shift name, check-in and check-out are required.")
            return render(request, "accounts/shift_edit.html", {"shift": shift})

        if (
            ShiftMaster.objects.filter(shift_name=name)
            .exclude(id=shift.id)
            .exists()
        ):
            messages.error(request, "Shift name already exists.")
            return render(request, "accounts/shift_edit.html", {"shift": shift})

        old_name = shift.shift_name
        shift.shift_name = name
        shift.check_in = check_in
        shift.check_out = check_out
        shift.grace_minutes = int(grace or 10)
        shift.description = description
        shift.is_active = is_active
        try:
            shift.rotation_order = int(request.POST.get("rotation_order", shift.rotation_order) or 0)
        except (TypeError, ValueError):
            pass
        shift.save()

        if old_name != name:
            EmpMaster.objects.filter(shift=old_name).update(shift=name)

        messages.success(request, "Shift updated successfully.")
        return redirect("shift_list")

    return render(request, "accounts/shift_edit.html", {"shift": shift})


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def shift_delete(request, id):
    shift = get_object_or_404(ShiftMaster, id=id)
    if EmpMaster.objects.filter(shift=shift.shift_name).exists():
        messages.error(
            request,
            f"Cannot delete — {shift.shift_name} is assigned to employees. Reassign them first.",
        )
        return redirect("shift_list")
    shift.delete()
    messages.success(request, "Shift deleted.")
    return redirect("shift_list")


@login_required(login_url="login")
def late_coming_report(request):
    """Track late arrivals with shift schedule comparison."""
    from datetime import date

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    ensure_default_shifts()
    today = date.today()
    default_from = date(today.year, today.month, 1).isoformat()
    default_to = today.isoformat()

    date_from = request.GET.get("date_from", default_from).strip()
    date_to = request.GET.get("date_to", default_to).strip()
    employee_id = request.GET.get("employee_id", "").strip()
    shift_filter = request.GET.get("shift", "").strip()

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")

    emp_by_id = {}
    for emp in EmpMaster.objects.all():
        try:
            emp_by_id[int(emp.emp_id)] = emp
        except (ValueError, TypeError):
            pass

    attendance_qs = AttendanceMaster.objects.all().order_by("-att_date", "-check_in")
    if date_from:
        attendance_qs = attendance_qs.filter(att_date__gte=date_from)
    if date_to:
        attendance_qs = attendance_qs.filter(att_date__lte=date_to)
    if is_restricted_user:
        try:
            attendance_qs = attendance_qs.filter(emp_id=int(own_emp.emp_id))
        except (ValueError, TypeError):
            attendance_qs = AttendanceMaster.objects.none()
    elif employee_id:
        try:
            attendance_qs = attendance_qs.filter(emp_id=int(employee_id))
        except (ValueError, TypeError):
            pass

    rows = []
    total_late_minutes = 0
    late_employees = set()

    for att in attendance_qs:
        emp = emp_by_id.get(att.emp_id)
        if not emp:
            continue
        if shift_filter and get_shift_label(emp, att.att_date) != shift_filter:
            continue
        if not att.check_in:
            continue

        late_mins = calc_late_minutes(emp, att.check_in, att.att_date)
        is_late = late_mins > 0 or (att.attendance_status or "").strip() == "Late"
        if not is_late:
            continue

        if late_mins <= 0 and (att.attendance_status or "").strip() == "Late":
            scheduled = get_scheduled_check_in(emp, att.att_date)
            try:
                from datetime import datetime
                office_dt = datetime.combine(att.att_date, scheduled)
                cin_dt = datetime.combine(att.att_date, att.check_in)
                late_mins = max(
                    0,
                    int((cin_dt - office_dt).total_seconds() / 60)
                    - get_late_grace_minutes(emp, att.att_date),
                )
            except (TypeError, ValueError):
                late_mins = 0

        total_late_minutes += late_mins
        late_employees.add(att.emp_id)
        rows.append(
            {
                "att": att,
                "emp": emp,
                "shift_label": get_shift_label(emp, att.att_date),
                "scheduled_in": get_scheduled_check_in(emp, att.att_date),
                "late_minutes": late_mins,
                "late_display": fmt_late_display(late_mins),
                "penalty_on": employee_late_penalty_enabled(emp),
            }
        )

    context = {
        "rows": rows,
        "date_from": date_from,
        "date_to": date_to,
        "selected_employee": employee_id,
        "shift_filter": shift_filter,
        "is_restricted_user": is_restricted_user,
        "employees": EmpMaster.objects.all().order_by("full_name"),
        "shifts": get_active_shifts(),
        "total_late_count": len(rows),
        "total_late_minutes": total_late_minutes,
        "total_late_display": fmt_late_display(total_late_minutes),
        "unique_late_employees": len(late_employees),
    }
    return render(request, "accounts/late_coming_report.html", context)


# ==================== PAYSLIP ====================
@login_required(login_url="login")
def payslip_generate(request):
    payroll_config = get_payroll_module_config()
    if not is_module_enabled(payroll_config, "payslip"):
        messages.error(request, "Payslip module is disabled in Payroll Settings.")
        if request.user.is_staff or request.user.is_superuser:
            return redirect("payroll_module_settings")
        return redirect("home")

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")

    employees = EmpMaster.objects.all()
    payslip_data = None

    if request.method == "POST":
        if is_restricted_user:
            employee_id = str(own_emp.emp_id)
        else:
            employee_id = request.POST.get("employee_id", "")
        month = request.POST.get("month", "")
        year = request.POST.get("year", "")

        if employee_id and month and year:
            try:
                employee = EmpMaster.objects.get(emp_id=employee_id)

                # Get month name
                month_names = [
                    "",
                    "January",
                    "February",
                    "March",
                    "April",
                    "May",
                    "June",
                    "July",
                    "August",
                    "September",
                    "October",
                    "November",
                    "December",
                ]
                month_name = month_names[int(month)]

                salary_type = (employee.salary_type or "Monthly").strip()
                rate_or_salary = float(employee.salary_amt) if employee.salary_amt else 0
                scheduled_hours_per_day = _scheduled_hours_per_day(employee)

                # Calculate attendance for the month
                import calendar as cal_module
                from datetime import date
                from django.db.models import Sum

                # Safe int conversion for emp_id (handles both numeric "1" and "EMP001" style)
                try:
                    emp_id_int = int(employee_id)
                except (ValueError, TypeError):
                    emp_id_int = None

                if emp_id_int is not None:
                    attendance_qs = AttendanceMaster.objects.filter(
                        emp_id=emp_id_int,
                        att_date__month=int(month),
                        att_date__year=int(year),
                    )
                else:
                    attendance_qs = AttendanceMaster.objects.filter(
                        full_name=employee.full_name,
                        att_date__month=int(month),
                        att_date__year=int(year),
                    )

                attendance_count = attendance_qs.count()
                total_worked_hours = float(
                    attendance_qs.aggregate(total=Sum("worked_hours"))["total"] or 0
                )

                # Total calendar days in the month (for proration)
                total_days_in_month = cal_module.monthrange(int(year), int(month))[1]
                working_days_in_month = _count_working_days_in_month(
                    employee, int(year), int(month)
                )

                if salary_type.lower() == "hourly":
                    basic_salary = round(rate_or_salary * total_worked_hours, 2)
                    expected_hours = scheduled_hours_per_day * working_days_in_month
                    proration_factor = (
                        min(1.0, total_worked_hours / expected_hours)
                        if expected_hours > 0 and total_worked_hours > 0
                        else 0
                    )
                    prorated_basic = basic_salary
                else:
                    basic_salary = rate_or_salary
                    attendance_integration_on = is_module_enabled(
                        payroll_config, "attendance_integration"
                    )
                    if attendance_integration_on:
                        proration_factor = (
                            attendance_count / working_days_in_month
                            if working_days_in_month > 0 and attendance_count > 0
                            else 0
                        )
                    else:
                        proration_factor = 1.0
                    prorated_basic = round(basic_salary * proration_factor, 2)

                emp_items = list(EmpItemMaster.objects.filter(emp_id=employee_id))
                payslip_items = get_payslip_line_items(employee_id)

                salary_config = get_salary_config()
                base_mode = (
                    salary_config.salary_base_mode if salary_config else "gross"
                )
                monthly_base = basic_salary
                salary_breakdown = build_breakdown_for_employee(
                    monthly_base, emp_items, base_mode=base_mode
                )

                # #region agent log
                try:
                    import json as _json
                    import time as _time
                    from pathlib import Path as _Path

                    _log = {
                        "sessionId": "72a37d",
                        "hypothesisId": "PS1",
                        "location": "views.py:payslip_generate",
                        "message": "payslip_calc",
                        "data": {
                            "emp_id": employee_id,
                            "monthly_base": monthly_base,
                            "base_mode": base_mode,
                            "proration_factor": proration_factor,
                            "breakdown_gross": salary_breakdown.get("gross"),
                            "breakdown_basic": salary_breakdown.get("basic"),
                            "item_count": len(payslip_items),
                            "attendance_integration": is_module_enabled(
                                payroll_config, "attendance_integration"
                            ),
                        },
                        "timestamp": int(_time.time() * 1000),
                    }
                    _lp = _Path(__file__).resolve().parent.parent.parent / "debug-72a37d.log"
                    with open(_lp, "a", encoding="utf-8") as _fh:
                        _fh.write(_json.dumps(_log) + "\n")
                except Exception:
                    pass
                # #endregion

                # Separate earnings and deductions (all prorated)
                earnings_list = []
                deductions_list = []
                total_earnings = 0
                total_deductions = 0

                for item in payslip_items:
                    calculated_amt = compute_emp_item_amount(
                        item,
                        monthly_base,
                        proration_factor,
                        salary_breakdown,
                    )

                    item_data = {
                        "name": item.item_name,
                        "amount": round(calculated_amt, 2),
                    }

                    if item.item_type == "Earning":
                        earnings_list.append(item_data)
                        total_earnings += calculated_amt
                    elif item.item_type == "Deduction":
                        deductions_list.append(item_data)
                        total_deductions += calculated_amt

                prorated_basic = round(
                    salary_breakdown.get("basic", monthly_base) * proration_factor, 2
                )

                late_days = attendance_qs.filter(attendance_status="Late").count()
                if (
                    is_module_enabled(payroll_config, "attendance_integration")
                    and _employee_late_penalty_enabled(employee)
                    and late_days > 0
                ):
                    late_fine_per_day = float(employee.half_abd_fine or 0)
                    if late_fine_per_day > 0:
                        late_penalty_total = late_fine_per_day * late_days
                        deductions_list.append(
                            {
                                "name": f"Late Attendance ({late_days} day{'s' if late_days != 1 else ''})",
                                "amount": round(late_penalty_total, 2),
                            }
                        )
                        total_deductions += late_penalty_total

                # Calculate gross and net salary on prorated amounts
                has_basic_item = any(
                    "basic" in (item.item_name or "").lower()
                    for item in payslip_items
                    if item.item_type == "Earning"
                )
                if has_basic_item:
                    gross_salary = total_earnings
                else:
                    gross_salary = prorated_basic + total_earnings
                net_salary = gross_salary - total_deductions

                # Leave days in selected month (approved)
                leave_days = 0
                if emp_id_int is not None:
                    leave_days = LeaveRequest.objects.filter(
                        emp_id=emp_id_int,
                        leave_status=1,
                        start_date__month=int(month),
                        start_date__year=int(year),
                    ).count()

                lop_days = max(0, working_days_in_month - attendance_count - leave_days)
                paid_days = max(0, working_days_in_month - lop_days)

                earnings_display = []
                if not has_basic_item:
                    earnings_display.append(
                        {
                            "name": "Basic Salary"
                            if salary_type.lower() != "hourly"
                            else f"Hourly Pay ({total_worked_hours:.2f} hrs × ₹{rate_or_salary:.2f})",
                            "amount": round(prorated_basic, 2),
                            "amount_fmt": _format_inr(prorated_basic),
                        }
                    )
                for item in earnings_list:
                    earnings_display.append(
                        {
                            "name": item["name"],
                            "amount": item["amount"],
                            "amount_fmt": _format_inr(item["amount"]),
                        }
                    )

                deductions_display = [
                    {
                        "name": item["name"],
                        "amount": item["amount"],
                        "amount_fmt": _format_inr(item["amount"]),
                    }
                    for item in deductions_list
                ]

                max_rows = max(len(earnings_display), len(deductions_display), 1)
                salary_rows = []
                for i in range(max_rows):
                    salary_rows.append(
                        {
                            "earning": earnings_display[i]
                            if i < len(earnings_display)
                            else None,
                            "deduction": deductions_display[i]
                            if i < len(deductions_display)
                            else None,
                        }
                    )

                payslip_data = {
                    "employee": employee,
                    "employee_code": (
                        employee.employee_code or employee.emp_id
                    ),
                    "week_off_display": _format_week_off_display(employee),
                    "month": month_name,
                    "year": year,
                    "month_num": month,
                    "attendance_days": attendance_count,
                    "total_days": working_days_in_month,
                    "calendar_days": total_days_in_month,
                    "paid_days": paid_days,
                    "leave_days": leave_days,
                    "lop_days": lop_days,
                    "basic_salary_full": round(basic_salary, 2),
                    "basic_salary": round(prorated_basic, 2),
                    "salary_type": salary_type,
                    "total_worked_hours": round(total_worked_hours, 2),
                    "scheduled_hours_per_day": scheduled_hours_per_day,
                    "earnings_list": earnings_list,
                    "deductions_list": deductions_list,
                    "earnings_display": earnings_display,
                    "deductions_display": deductions_display,
                    "salary_rows": salary_rows,
                    "total_earnings": round(total_earnings, 2),
                    "gross_salary": round(gross_salary, 2),
                    "gross_salary_fmt": _format_inr(gross_salary),
                    "total_deductions": round(total_deductions, 2),
                    "total_deductions_fmt": _format_inr(total_deductions),
                    "net_salary": round(net_salary, 2),
                    "net_salary_fmt": _format_inr(net_salary),
                    "amount_in_words": _amount_in_words(net_salary),
                }
            except EmpMaster.DoesNotExist:
                messages.error(request, "Employee not found")

    from datetime import date

    context = {
        "employees": employees if not is_restricted_user else [own_emp],
        "payslip": payslip_data,
        "is_restricted_user": is_restricted_user,
        "own_emp": own_emp,
        "selected_month": request.POST.get("month", "") if request.method == "POST" else "",
        "selected_year": request.POST.get("year", "") if request.method == "POST" else "",
        "selected_employee": request.POST.get("employee_id", "") if request.method == "POST" else "",
        "month_choices": list(range(1, 13)),
        "year_choices": list(range(2024, 2029)),
        "report_date": date.today().strftime("%d-%b-%Y"),
    }
    return render(request, "accounts/payslip_generate.html", context)


# ==================== COMPANY SETTINGS ====================
@login_required(login_url="login")
def company_settings(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to access settings.")
        return redirect("home")

    company = SystemSettings.objects.first()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        contact = request.POST.get("contact", "").strip()
        address = request.POST.get("address", "").strip()

        if not name:
            messages.error(request, "Company name is required.")
        else:
            if not company:
                company = SystemSettings(
                    name=name,
                    email=email,
                    contact=contact,
                    address=address,
                    cover_img="",
                )
            else:
                company.name = name
                company.email = email
                company.contact = contact
                company.address = address

            logo_file = request.FILES.get("logo")
            if logo_file:
                logo_path = save_company_logo(logo_file)
                company.cover_img = logo_path

            company.save()
            messages.success(request, "Company settings saved successfully.")
            return redirect("company_settings")

    return render(request, "accounts/company_settings.html", {"company": company})


@login_required(login_url="login")
def api_settings(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to access settings.")
        return redirect("home")

    api_cfg = get_api_settings()

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "regenerate_token":
            regenerate_api_token(api_cfg)
            messages.success(request, "API token regenerated successfully.")
            return redirect("api_settings")

        api_cfg.api_enabled = 1 if request.POST.get("api_enabled") == "1" else 0
        api_cfg.biometric_enabled = (
            1 if request.POST.get("biometric_enabled") == "1" else 0
        )
        api_cfg.device_name = request.POST.get("device_name", "").strip()
        api_cfg.save()
        messages.success(request, "API settings saved successfully.")
        return redirect("api_settings")

    api_base_url = request.build_absolute_uri("/api/")
    context = {
        "api_cfg": api_cfg,
        "api_base_url": api_base_url,
        "biometric_endpoint": request.build_absolute_uri("/api/biometric/punch/"),
    }
    return render(request, "accounts/api_settings.html", context)


@login_required(login_url="login")
def settings_hub(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to access settings.")
        return redirect("home")

    sections = [
        {
            "title": "Users & Roles",
            "subtitle": "Web portal login for HR Admin, HOD, Payroll, Managers",
            "slug": "users",
            "icon": "fas fa-user-shield",
            "items": [
                {
                    "name": "User List",
                    "url_name": "user_list",
                    "icon": "fas fa-users",
                    "desc": "Portal users with management login",
                },
                {
                    "name": "Add User",
                    "url_name": "user_add",
                    "icon": "fas fa-user-plus",
                    "desc": "Create HR Admin, HOD, Payroll, Manager login",
                },
                {
                    "name": "Role Assign",
                    "url_name": "role_assign",
                    "icon": "fas fa-user-tag",
                    "desc": "Assign role to portal user",
                },
                {
                    "name": "Role Settings",
                    "url_name": "role_settings",
                    "icon": "fas fa-shield-alt",
                    "desc": "Configure management roles",
                },
            ],
        },
        {
            "title": "Company & System",
            "subtitle": "Company profile, logo, and API / biometric setup",
            "slug": "company",
            "icon": "fas fa-building",
            "items": [
                {
                    "name": "Company Settings",
                    "url_name": "company_settings",
                    "icon": "fas fa-building",
                    "desc": "Name, logo, address, contact",
                },
                {
                    "name": "API Settings",
                    "url_name": "api_settings",
                    "icon": "fas fa-plug",
                    "desc": "API token & biometric integration",
                },
            ],
        },
        {
            "title": "Organization",
            "subtitle": "Departments and job designations for employees",
            "slug": "org",
            "icon": "fas fa-sitemap",
            "items": [
                {
                    "name": "Department List",
                    "url_name": "department_list",
                    "icon": "fas fa-layer-group",
                    "desc": "Manage departments",
                },
                {
                    "name": "Designation List",
                    "url_name": "designation_list",
                    "icon": "fas fa-id-badge",
                    "desc": "Manage designations",
                },
            ],
        },
        {
            "title": "Attendance & Shifts",
            "subtitle": "Shift management and automatic rotation for attendance",
            "slug": "attendance",
            "icon": "fas fa-user-clock",
            "items": [
                {
                    "name": "Shift Rotation",
                    "url_name": "shift_rotation_settings",
                    "icon": "fas fa-sync-alt",
                    "desc": "ON/OFF automatic rotation-wise shift for attendance",
                },
                {
                    "name": "Shift Management",
                    "url_name": "shift_list",
                    "icon": "fas fa-clock",
                    "desc": "Add and edit shift timings",
                },
            ],
        },
        {
            "title": "HR Modules",
            "subtitle": "Claims and other HR features — enable in HR Module Settings",
            "slug": "hr",
            "icon": "fas fa-briefcase",
            "items": get_hr_hub_items(),
        },
        {
            "title": "Payroll",
            "subtitle": "Enable modules in Payroll Settings — configure salary, payslip and compliance",
            "slug": "payroll",
            "icon": "fas fa-calculator",
            "items": get_payroll_hub_items(),
        },
        {
            "title": "Notification Center",
            "subtitle": "Email, SMS, WhatsApp alerts, reminders and in-app notifications",
            "slug": "notifications",
            "icon": "fas fa-bell",
            "items": get_notification_hub_items(),
        },
    ]
    return render(request, "accounts/settings_hub.html", {"sections": sections})


# ==================== REPORTS ====================

DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _fmt_hhmm(minutes):
    if minutes is None or minutes <= 0:
        return "-"
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"


def _fmt_hm_total(minutes):
    minutes = max(0, int(minutes or 0))
    h, m = divmod(minutes, 60)
    return f"{h:02d}h {m:02d}m"


def _minutes_between_times(t_in, t_out, base_date):
    from datetime import datetime, timedelta

    if not t_in or not t_out:
        return 0
    ci = datetime.combine(base_date, t_in)
    co = datetime.combine(base_date, t_out)
    if co <= ci:
        co += timedelta(days=1)
    return int((co - ci).total_seconds() / 60)


def _time_to_display(t):
    if not t:
        return "-"
    return t.strftime("%H:%M")


def _scheduled_minutes_per_day(emp):
    return int(round(_scheduled_hours_per_day(emp) * 60))


def _build_monthly_attendance_report_data(emp, month, year):
    import calendar
    from datetime import date, datetime, timedelta

    num_days = calendar.monthrange(year, month)[1]
    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    month_name = month_names[month]
    month_short = month_name[:3]
    week_off_days = _parse_week_off_days(emp)
    scheduled_in = get_scheduled_check_in(emp)
    scheduled_out = get_scheduled_check_out(emp)
    scheduled_daily = _scheduled_minutes_per_day(emp)

    try:
        emp_id_int = int(emp.emp_id)
    except (ValueError, TypeError):
        emp_id_int = None

    att_by_day = {}
    if emp_id_int is not None:
        for att in AttendanceMaster.objects.filter(
            emp_id=emp_id_int, att_date__month=month, att_date__year=year
        ):
            att_by_day[att.att_date.day] = att

    holidays = {
        h.holiday_date.day
        for h in HolidayMaster.objects.filter(
            holiday_date__month=month, holiday_date__year=year
        )
    }

    leave_by_day = {}
    if emp_id_int is not None:
        for leave in LeaveRequest.objects.filter(
            emp_id=emp_id_int, leave_status=1, start_date__lte=date(year, month, num_days),
            end_date__gte=date(year, month, 1),
        ):
            d = leave.start_date
            while d <= leave.end_date:
                if d.month == month and d.year == year:
                    leave_by_day[d.day] = leave
                d += timedelta(days=1)

    days = []
    summary = {
        "present": 0,
        "absent": 0,
        "half_days": 0,
        "double_present": 0,
        "week_off": 0,
        "paid_leaves": 0,
        "unpaid_leaves": 0,
        "public_holiday": 0,
    }
    total_worked = total_late = total_early = total_overtime = 0
    working_days = 0

    for day in range(1, num_days + 1):
        day_date = date(year, month, day)
        weekday = day_date.weekday()
        day_label = f"{month_short}\n{day:02d}"
        day_name = "WO" if weekday in week_off_days else DAY_ABBR[weekday]

        status = "-"
        check_in = "-"
        check_out = "-"
        worked_m = late_m = early_m = ot_m = 0
        att = att_by_day.get(day)

        if day in holidays:
            status = "PH"
            summary["public_holiday"] += 1
        elif weekday in week_off_days:
            status = "-"
            summary["week_off"] += 1
        elif day in leave_by_day:
            leave = leave_by_day[day]
            if getattr(leave, "is_paid", 1):
                status = "PL"
                summary["paid_leaves"] += 1
            else:
                status = "UPL"
                summary["unpaid_leaves"] += 1
        elif att:
            raw = (att.attendance_status or "").strip()
            if raw == "Absent":
                status = "A"
                summary["absent"] += 1
            elif raw == "Half Day":
                status = "HD"
                summary["half_days"] += 1
            elif raw in ("On Leave",):
                status = "PL"
                summary["paid_leaves"] += 1
            else:
                status = "P"
                summary["present"] += 1
            check_in = _time_to_display(att.check_in)
            check_out = _time_to_display(att.check_out)
            if att.check_in and att.check_out:
                worked_m = _minutes_between_times(att.check_in, att.check_out, day_date)
                if att.worked_hours:
                    worked_m = int(float(att.worked_hours) * 60)
            elif att.worked_hours:
                worked_m = int(float(att.worked_hours) * 60)

            if att.check_in and employee_late_penalty_enabled(emp):
                late_m = calc_late_minutes(emp, att.check_in, day_date)

            if att.check_out and scheduled_out:
                out_dt = datetime.combine(day_date, att.check_out)
                sched_out_dt = datetime.combine(day_date, scheduled_out)
                early_m = max(0, int((sched_out_dt - out_dt).total_seconds() / 60))

            if worked_m > scheduled_daily:
                ot_m = worked_m - scheduled_daily

            total_worked += worked_m
            total_late += late_m
            total_early += early_m
            total_overtime += ot_m
        elif day_date <= date.today():
            status = "A"
            summary["absent"] += 1
        else:
            status = "-"

        if weekday not in week_off_days and day not in holidays:
            working_days += 1

        days.append(
            {
                "day": day,
                "day_label": day_label,
                "day_name": day_name,
                "status": status,
                "check_in": check_in,
                "check_out": check_out,
                "worked": _fmt_hhmm(worked_m),
                "worked_minutes": worked_m,
                "late": _fmt_hhmm(late_m),
                "early": _fmt_hhmm(early_m),
                "overtime": _fmt_hhmm(ot_m),
                "overtime_minutes": ot_m,
            }
        )

    payable = (
        summary["present"]
        + summary["half_days"] * 0.5
        + summary["week_off"]
        + summary["paid_leaves"]
        + summary["public_holiday"]
    )
    sched_total_m = working_days * scheduled_daily

    return {
        "employee": emp,
        "month_name": month_name,
        "year": year,
        "days": days,
        "summary": {
            **summary,
            "payable_days": round(payable, 1),
        },
        "totals": {
            "worked": _fmt_hm_total(total_worked),
            "late": _fmt_hm_total(total_late),
            "early": _fmt_hm_total(total_early),
            "overtime": _fmt_hm_total(total_overtime),
            "overtime_minutes": total_overtime,
        },
        "scheduled_hours_display": _fmt_hm_total(sched_total_m),
        "schedule_label": get_shift_label(emp),
    }


@login_required(login_url="login")
def monthly_attendance_report(request):
    from datetime import date
    import calendar

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")

    employees = EmpMaster.objects.all() if not is_restricted_user else [own_emp]
    month = int(request.GET.get("month", date.today().month))
    year = int(request.GET.get("year", date.today().year))

    if is_restricted_user:
        employee_id = str(own_emp.emp_id)
    else:
        employee_id = request.GET.get("employee_id", "").strip()

    report = None
    if employee_id:
        try:
            emp = EmpMaster.objects.get(emp_id=employee_id)
            report = _build_monthly_attendance_report_data(emp, month, year)
        except EmpMaster.DoesNotExist:
            messages.error(request, "Employee not found.")

    company = SystemSettings.objects.first()
    context = {
        "employees": employees,
        "month": month,
        "year": year,
        "selected_employee": employee_id,
        "is_restricted_user": is_restricted_user,
        "own_emp": own_emp,
        "report": report,
        "report_date": date.today().strftime("%d-%m-%Y"),
        "company": company,
        "month_choices": list(range(1, 13)),
        "year_choices": list(range(2024, 2029)),
    }
    return render(request, "accounts/monthly_attendance_report.html", context)


@login_required(login_url="login")
def attendance_report(request):
    from datetime import date, timedelta
    import calendar

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")

    employees = EmpMaster.objects.all() if not is_restricted_user else [own_emp]

    # Get filter parameters
    month = request.GET.get("month", str(date.today().month))
    year = request.GET.get("year", str(date.today().year))

    # Restricted users always see only their own report — ignore any employee_id param
    if is_restricted_user:
        employee_id = str(own_emp.emp_id)
    else:
        employee_id = request.GET.get("employee_id", "")

    month = int(month)
    year = int(year)

    # Get month name and number of days
    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    month_name = month_names[month]
    num_days = calendar.monthrange(year, month)[1]
    days_list = list(range(1, num_days + 1))

    # Get employees to show
    if is_restricted_user:
        emp_list = [own_emp]
    elif employee_id:
        emp_list = EmpMaster.objects.filter(emp_id=employee_id)
    else:
        emp_list = EmpMaster.objects.all()

    # Build attendance data for each employee (week off per employee profile)
    report_data = []
    for emp in emp_list:
        days_status, week_off_label = _build_attendance_grid_for_employee(
            emp, month, year
        )
        report_data.append(
            {
                "emp_id": emp.emp_id,
                "full_name": emp.full_name,
                "week_off_label": week_off_label,
                "days_status": days_status,
            }
        )

    context = {
        "employees": employees,
        "report_data": report_data,
        "days_list": days_list,
        "month": month,
        "month_name": month_name,
        "year": year,
        "selected_employee": employee_id,
        "is_restricted_user": is_restricted_user,
        "own_emp": own_emp,
    }
    return render(request, "accounts/attendance_report.html", context)


@login_required(login_url="login")
def self_attendance_report(request):
    """Selfie + location tracking report with detail and map actions."""
    from datetime import date

    is_restricted_user = not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    own_emp = None
    if is_restricted_user:
        own_emp = find_emp_for_auth_user(request.user)
        if own_emp:
            try:
                attendance = AttendanceMaster.objects.filter(
                    emp_id=int(own_emp.emp_id)
                ).order_by("-att_date")
            except ValueError:
                attendance = AttendanceMaster.objects.none()
        else:
            attendance = AttendanceMaster.objects.none()
    else:
        attendance = AttendanceMaster.objects.all().order_by("-att_date")
        employees = EmpMaster.objects.all().order_by("full_name")

    today = date.today()
    default_from = date(today.year, today.month, 1).isoformat()
    default_to = today.isoformat()

    date_from = request.GET.get("date_from", default_from).strip()
    date_to = request.GET.get("date_to", default_to).strip()
    status_filter = request.GET.get("status", "").strip()
    employee_id = request.GET.get("employee_id", "").strip()

    if date_from:
        attendance = attendance.filter(att_date__gte=date_from)
    if date_to:
        attendance = attendance.filter(att_date__lte=date_to)
    if status_filter:
        attendance = attendance.filter(attendance_status__iexact=status_filter)
    if not is_restricted_user and employee_id:
        try:
            attendance = attendance.filter(emp_id=int(employee_id))
        except (ValueError, TypeError):
            pass

    attendance = _attach_location_counts(_attach_gps_status(attendance))

    total_records = len(attendance)
    with_login_selfie = sum(1 for a in attendance if a.checkin_photo_url)
    with_logout_selfie = sum(1 for a in attendance if a.checkout_photo_url)
    with_location = sum(1 for a in attendance if a.location_count > 0)

    context = {
        "attendance": attendance,
        "is_restricted_user": is_restricted_user,
        "date_from": date_from,
        "date_to": date_to,
        "status_filter": status_filter,
        "selected_employee": employee_id,
        "total_records": total_records,
        "with_login_selfie": with_login_selfie,
        "with_logout_selfie": with_logout_selfie,
        "with_location": with_location,
    }
    if not is_restricted_user:
        context["employees"] = employees

    return render(request, "accounts/self_attendance_report.html", context)


# User Authentication Views
def login(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        login_id = (request.POST.get("login_id") or request.POST.get("email") or "").strip()
        password = request.POST.get("password")

        db_user = resolve_auth_user_from_login(login_id)

        if db_user is not None:
            if not db_user.is_active:
                messages.error(
                    request,
                    "Your account is pending approval. Please contact HR/Admin.",
                )
            else:
                user = authenticate(request, username=db_user.username, password=password)
                if user is not None:
                    if not can_access_web_portal(user):
                        messages.error(
                            request,
                            "You do not have access to the web portal. Contact HR/Admin.",
                        )
                    else:
                        auth_login(request, user)
                        return redirect("home")
                else:
                    messages.error(request, "Invalid login ID or password")
        else:
            emp = find_emp_by_login_id(login_id) if login_id else None
            if emp and not (emp.contact or "").strip():
                messages.error(
                    request,
                    "Employee record has no mobile number. Contact HR/Admin.",
                )
            elif emp:
                messages.error(
                    request,
                    "No login account for this employee yet. Contact HR/Admin.",
                )
            else:
                messages.error(request, "Invalid login ID or password")

    return render(request, "accounts/login.html")


def _register_context(request):
    plan_key = (
        request.POST.get("plan_key")
        or request.GET.get("plan", "")
        or request.session.get("subscribe_plan_key", "")
    ).strip()
    subscribe_mode = (
        request.POST.get("subscribe_after", "") == "1"
        or request.GET.get("subscribe", "") == "1"
        or bool(request.session.get("subscribe_plan_key"))
    )
    trial_mode = (
        request.POST.get("trial_mode", "") == "1"
        or request.GET.get("trial", "") == "1"
    )
    plan_name = ""
    if plan_key:
        plan_obj = SaasPricingPlan.objects.filter(plan_key=plan_key, is_active=1).first()
        if plan_obj:
            plan_name = plan_obj.plan_name
    quick_register = True
    pricing_cfg = get_pricing_config()
    return {
        "subscribe_plan_key": plan_key,
        "subscribe_mode": subscribe_mode,
        "subscribe_plan_name": plan_name,
        "trial_mode": trial_mode,
        "quick_register": quick_register,
        "trial_days": pricing_cfg["trial_days"],
        "trial_max_employees": pricing_cfg["trial_max_employees"],
    }


def register(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password", "")
        dob = request.POST.get("dob")
        gender = request.POST.get("gender")
        address = request.POST.get("address")
        father_name = request.POST.get("father_name")
        emergency_contact = request.POST.get("emergency_contact")

        reg_ctx = _register_context(request)
        if not password:
            messages.error(request, "Password is required.")
            return render(request, "accounts/register.html", reg_ctx)
        if password != confirm_password:
            messages.error(request, "Password and confirmation do not match.")
            return render(request, "accounts/register.html", reg_ctx)
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "accounts/register.html", reg_ctx)

        # Validate phone number - must be exactly 10 digits
        if not phone or len(phone) != 10 or not phone.isdigit():
            messages.error(request, "Phone number must be exactly 10 digits")
            return render(request, "accounts/register.html", reg_ctx)

        # Check if phone or email already exists in EmpTemp or Users
        if EmpTemp.objects.filter(contact=phone).exists():
            # Check if Django User also exists, if not create it
            if not User.objects.filter(username=phone).exists():
                try:
                    # Get the existing EmpTemp to create missing User
                    existing_emp = EmpTemp.objects.get(contact=phone)
                    name_parts = existing_emp.full_name.split(" ", 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ""

                    User.objects.create_user(
                        username=phone,
                        email=existing_emp.email,
                        password=password,  # Use the current password
                        first_name=first_name,
                        last_name=last_name,
                    )
                    messages.success(request, "Account created! You can now login.")
                    return redirect("login")
                except Exception as e:
                    messages.error(request, f"Error creating account: {str(e)}")
                    return render(request, "accounts/register.html", _register_context(request))
            else:
                messages.error(request, "Phone number already registered")
                return render(request, "accounts/register.html", _register_context(request))

        if EmpTemp.objects.filter(email=email).exists():
            # Check if Django User also exists, if not create it
            if not User.objects.filter(email=email).exists():
                try:
                    # Get the existing EmpTemp to create missing User
                    existing_emp = EmpTemp.objects.get(email=email)
                    name_parts = existing_emp.full_name.split(" ", 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ""

                    User.objects.create_user(
                        username=existing_emp.contact,
                        email=email,
                        password=password,  # Use the current password
                        first_name=first_name,
                        last_name=last_name,
                    )
                    messages.success(request, "Account created! You can now login.")
                    return redirect("login")
                except Exception as e:
                    messages.error(request, f"Error creating account: {str(e)}")
                    return render(request, "accounts/register.html", _register_context(request))
            else:
                messages.error(request, "Email already registered")
                return render(request, "accounts/register.html", _register_context(request))

        if User.objects.filter(username=phone).exists():
            messages.error(request, "Phone number already registered")
            return render(request, "accounts/register.html", _register_context(request))

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return render(request, "accounts/register.html", _register_context(request))

        # Create both Django User and EmpTemp entry for approval workflow
        try:
            from django.db import transaction
            import hashlib

            trial_mode = request.POST.get("trial_mode", "") == "1"
            plan_key = request.POST.get("plan_key", "").strip()
            subscribe_after = request.POST.get("subscribe_after", "") == "1"
            is_company_owner = trial_mode or subscribe_after

            # Use atomic transaction to ensure User (and optional EmpTemp) are created together
            with transaction.atomic():
                hashed_password = hashlib.md5(password.encode()).hexdigest()

                # Parse date string to date object
                from datetime import datetime

                dob_date = None
                if dob:
                    try:
                        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
                    except:
                        dob_date = None

                # Create Django User account first
                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                user = User.objects.create_user(
                    username=phone,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.is_active = bool(is_company_owner)
                user.save()

                if is_company_owner:
                    try:
                        user.groups.clear()
                    except Exception:
                        pass
                else:
                    try:
                        user.groups.add(Group.objects.get(name="customer"))
                    except Group.DoesNotExist:
                        pass
                    EmpTemp.objects.create(
                        full_name=full_name,
                        contact=phone,
                        email=email,
                        password=hashed_password,
                        dob=dob_date,
                        gender=gender or "",
                        address=address or "",
                        father_name=father_name or "",
                        emergency_contact=emergency_contact or "",
                        status="PENDING",
                    )

            if is_company_owner:
                setup_company_owner_account(phone, email, full_name, password)
                if trial_mode:
                    provision_trial_organization(phone, email, full_name)
                elif subscribe_after:
                    provision_free_organization(phone, email, full_name)

            plan_name = ""
            if plan_key:
                plan_obj = SaasPricingPlan.objects.filter(plan_key=plan_key, is_active=1).first()
                plan_name = plan_obj.plan_name if plan_obj else plan_key

            if subscribe_after and plan_key:
                lead_source = "subscription"
            elif trial_mode:
                lead_source = "trial"
            else:
                lead_source = "registration"

            lead = create_saas_lead(
                source=lead_source,
                full_name=full_name,
                email=email,
                phone=phone,
                company=full_name,
                plan_interest=plan_name or (
                    f"{get_pricing_config()['trial_days']}-Day Free Trial (Full Access)"
                    if trial_mode
                    else "Employee Registration"
                ),
                subject="New Registration" + (f" — {plan_name}" if plan_name else ""),
                message=(
                    f"Quick registration via QuickHR"
                    + (f" — plan: {plan_name}" if plan_name else "")
                    + "."
                ),
            )
            _debug_session_log(
                "views.py:register",
                "saas lead created on registration",
                {"lead_id": lead.id, "source": lead.source, "plan_key": plan_key, "subscribe_after": subscribe_after},
                "H-LEAD",
            )

            if subscribe_after and plan_key:
                request.session["register_lead"] = {
                    "customer_name": full_name,
                    "customer_email": email,
                    "customer_phone": phone,
                    "company_name": full_name,
                }
                messages.success(
                    request,
                    "Account created! Complete payment to activate your subscription.",
                )
                return redirect("subscribe_plan", plan_key=plan_key)

            if trial_mode:
                cfg = get_pricing_config()
                messages.success(
                    request,
                    f"Your {cfg['trial_days']}-day free trial is active! Log in to use all features "
                    f"including GPS check-in for up to {cfg['trial_max_employees']} employees.",
                )
                return redirect("login")

            messages.success(
                request,
                "Registration successful! Your account is pending admin approval. You will be able to login once approved.",
            )
            return redirect("login")
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return render(request, "accounts/register.html", _register_context(request))

    return render(request, "accounts/register.html", _register_context(request))


def logout_view(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully!")
    _debug_session_log(
        "views.py:logout_view",
        "logout success message queued",
        {"redirect": "login", "message": "Logged out successfully!"},
        "H1",
    )
    return redirect("login")


# User Management Views
@login_required(login_url="login")
@permission_required("auth.view_user", raise_exception=True)
def user_list(request):
    ensure_default_roles()
    users = Users.objects.exclude(type=2).order_by("-id")
    role_map = {r.legacy_type: r for r in RoleMaster.objects.all()}
    user_rows = []
    for u in users:
        role = role_map.get(u.type)
        user_rows.append(
            {
                "user": u,
                "role_name": role.name if role else get_role_label(u.type),
                "role_badge": get_role_badge_class(u.type),
            }
        )
    return render(request, "accounts/user_list.html", {"user_rows": user_rows})


@login_required(login_url="login")
@permission_required("auth.add_user", raise_exception=True)
def user_add(request):
    ensure_default_roles()
    departments = DeptMaster.objects.all()

    if request.method == "POST":
        import hashlib

        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        user_type = int(request.POST.get("type", 2))
        role_id = request.POST.get("role_id")
        if role_id:
            role = RoleMaster.objects.filter(id=role_id).first()
            if role:
                user_type = role.legacy_type
        mgmt_types = get_management_legacy_types()
        if user_type not in mgmt_types:
            messages.error(request, "Please select a valid management role.")
            return render(
                request,
                "accounts/user_add.html",
                {
                    "departments": departments,
                    "roles": get_active_management_roles(),
                },
            )

        # Validate phone number
        if not phone or len(phone) != 10 or not phone.isdigit():
            messages.error(request, "Phone number must be exactly 10 digits")
            return render(
                request,
                "accounts/user_add.html",
                {"departments": departments, "roles": get_active_management_roles()},
            )

        # Check if user already exists
        if Users.objects.filter(contact=phone).exists():
            messages.error(request, "User with this phone number already exists")
            return render(
                request,
                "accounts/user_add.html",
                {"departments": departments, "roles": get_active_management_roles()},
            )

        if Users.objects.filter(email=email).exists():
            messages.error(request, "User with this email already exists")
            return render(
                request,
                "accounts/user_add.html",
                {"departments": departments, "roles": get_active_management_roles()},
            )

        # Hash password (MD5 to match legacy system)
        hashed_password = hashlib.md5(password.encode()).hexdigest()

        # Create user in the users table (legacy)
        user = Users.objects.create(
            full_name=full_name,
            email=email,
            password=hashed_password,
            contact=phone,
            type=user_type,
        )

        # Also create a Django auth user so the new user can log in
        from django.contrib.auth.models import User as AuthUser

        # prefer phone as username; ensure uniqueness
        username = phone or (email.split("@")[0] if email else f"legacy_{user.id}")
        base_username = username
        counter = 1
        while AuthUser.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        # create auth user if not exists by email
        if not AuthUser.objects.filter(email=email).exists():
            name_parts = (full_name or "").split(" ", 1)
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            auth_user = AuthUser.objects.create_user(
                username=username,
                email=email or "",
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

        sync_user_role(user)

        messages.success(request, "User added successfully!")
        return redirect("user_list")

    roles = get_active_management_roles()
    return render(request, "accounts/user_add.html", {"departments": departments, "roles": roles})


@login_required(login_url="login")
@permission_required("auth.change_user", raise_exception=True)
def user_edit(request, id):
    ensure_default_roles()
    user = get_object_or_404(Users, id=id)
    roles = get_active_management_roles()
    if request.method == "POST":
        user.full_name = request.POST.get("full_name", "")
        user.email = request.POST.get("email", "")
        user.contact = request.POST.get("contact", "")
        role_id = request.POST.get("role_id")
        if role_id:
            role = get_object_or_404(RoleMaster, id=role_id)
            if role.legacy_type == 2 or not role.is_active:
                messages.error(request, "Employee role cannot be assigned for web login.")
                return render(
                    request,
                    "accounts/user_edit.html",
                    {"user": user, "roles": roles},
                )
            user.type = role.legacy_type
        else:
            user_type = int(request.POST.get("type", 1))
            if user_type not in get_management_legacy_types():
                messages.error(request, "Invalid role selected")
                return render(
                    request,
                    "accounts/user_edit.html",
                    {"user": user, "roles": roles},
                )
            user.type = user_type
        user.save()
        sync_user_role(user)
        messages.success(request, "User updated successfully!")
        return redirect("user_list")
    return render(request, "accounts/user_edit.html", {"user": user, "roles": roles})


@login_required(login_url="login")
@permission_required("auth.delete_user", raise_exception=True)
def user_delete(request, id):
    user = get_object_or_404(Users, id=id)
    # Also delete the corresponding Django auth_user (matched by phone/email)
    try:
        auth_user = (
            User.objects.filter(username=user.contact).first()
            or User.objects.filter(email=user.email).first()
        )
        if auth_user:
            auth_user.delete()
    except Exception:
        pass
    user.delete()
    messages.success(request, "User deleted successfully!")
    return redirect("user_list")


@login_required(login_url="login")
def role_settings(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to access role settings.")
        return redirect("home")

    ensure_default_roles()

    if request.method == "POST":
        role_id = request.POST.get("role_id")
        role = get_object_or_404(RoleMaster, id=role_id)
        role.name = request.POST.get("name", role.name).strip() or role.name
        role.description = request.POST.get("description", "").strip()
        role.group_name = request.POST.get("group_name", role.group_name).strip() or role.group_name
        role.is_staff = 1 if request.POST.get("is_staff") == "1" else 0
        role.is_active = 1 if request.POST.get("is_active") == "1" else 0
        role.save()

        from django.contrib.auth.models import Group

        Group.objects.get_or_create(name=role.group_name)
        messages.success(request, f"Role '{role.name}' updated successfully.")
        return redirect("role_settings")

    roles = RoleMaster.objects.all().order_by("legacy_type")
    return render(request, "accounts/role_settings.html", {"roles": roles})


@login_required(login_url="login")
def role_assign(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to assign roles.")
        return redirect("home")

    ensure_default_roles()
    roles = get_active_management_roles()

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        role_id = request.POST.get("role_id")

        if not user_id or not role_id:
            messages.error(request, "Please select both user and role.")
        else:
            legacy_user = get_object_or_404(Users, id=user_id)
            role = get_object_or_404(RoleMaster, id=role_id)
            if role.legacy_type == 2 or not role.is_active:
                messages.error(request, "Employee role cannot be assigned for web login.")
            else:
                sync_user_role(legacy_user, legacy_type=role.legacy_type)
                messages.success(
                    request,
                    f"Role '{role.name}' assigned to {legacy_user.full_name}.",
                )
                return redirect("role_assign")

    users = Users.objects.exclude(type=2).order_by("full_name")
    role_map = {r.legacy_type: r for r in roles}
    user_rows = []
    for u in users:
        current = role_map.get(u.type)
        user_rows.append(
            {
                "user": u,
                "current_role": current,
                "role_name": current.name if current else get_role_label(u.type),
            }
        )

    return render(
        request,
        "accounts/role_assign.html",
        {
            "user_rows": user_rows,
            "roles": roles,
            "selected_user_id": request.GET.get("user", ""),
        },
    )


# Password Reset Views
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)

            # Generate token and uid
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Create reset link
            reset_link = request.build_absolute_uri(
                reverse("reset_password", kwargs={"uidb64": uid, "token": token})
            )

            # Send email (will display in console for development)
            subject = "Reset Your HRMS Password"
            message = f"""
Hello {user.first_name or user.username},

You have requested to reset your password for your HRMS account. 
Click the link below to reset your password:

{reset_link}

This link will expire in 24 hours for security reasons.
If you didn't request this, please ignore this email.

Best regards,
HRMS Team
            """

            email_message = EmailMessage(subject, message, to=[email])

            try:
                email_message.send()
                return redirect("reset_password_sent")
            except Exception as e:
                messages.error(request, "Error sending email. Please try again later.")
        else:
            messages.error(request, "No account found with this email address.")

    return render(request, "accounts/forgot_password.html")


def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")

            if password1 and password2:
                if password1 == password2:
                    if len(password1) >= 8:
                        user.set_password(password1)
                        user.save()
                        messages.success(request, "Password reset successful!")
                        return redirect("reset_password_complete")
                    else:
                        messages.error(
                            request, "Password must be at least 8 characters long."
                        )
                else:
                    messages.error(request, "Passwords do not match.")
            else:
                messages.error(request, "Please fill in both password fields.")

        return render(request, "accounts/reset_password.html", {"valid_link": True})
    else:
        messages.error(request, "Invalid or expired reset link.")
        return render(request, "accounts/reset_password.html", {"valid_link": False})


def reset_password_sent(request):
    return render(request, "accounts/reset_password_sent.html")


def reset_password_complete(request):
    return render(request, "accounts/reset_password_complete.html")


@login_required(login_url="login")
def manage_account(request):
    user = request.user

    if request.method == "POST":
        # Get form data
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        email = request.POST.get("email", "")
        username = request.POST.get("username", "")
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # Check if email already exists for another user
        if email != user.email and User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for another user.")
            return render(request, "accounts/manage_account.html", {"user": user})

        # Check if username already exists for another user
        if (
            username != user.username
            and User.objects.filter(username=username).exists()
        ):
            messages.error(
                request, "Username/Contact number already exists for another user."
            )
            return render(request, "accounts/manage_account.html", {"user": user})

        # Update basic information
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = username

        # Handle password change
        if new_password:
            # Verify current password
            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return render(request, "accounts/manage_account.html", {"user": user})

            # Check new password confirmation
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return render(request, "accounts/manage_account.html", {"user": user})

            # Check password length
            if len(new_password) < 8:
                messages.error(
                    request, "New password must be at least 8 characters long."
                )
                return render(request, "accounts/manage_account.html", {"user": user})

            # Set new password
            user.set_password(new_password)
            messages.success(
                request, "Password updated successfully! Please login again."
            )

        # Save user changes
        try:
            user.save()
            if new_password:
                # If password was changed, logout and redirect to login
                auth_logout(request)
                messages.info(
                    request,
                    "Password changed successfully. Please login with your new password.",
                )
                return redirect("login")
            else:
                messages.success(request, "Account information updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating account: {str(e)}")

    context = {"user": user}
    return render(request, "accounts/manage_account.html", context)


# Registration Request Management Views
@login_required(login_url="login")
def reg_user_list(request):
    """List all registration requests for admin approval"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied!")
        return redirect("home")

    reg_requests = EmpTemp.objects.all().order_by("-created_at")
    return render(
        request, "accounts/reg_user_list.html", {"reg_requests": reg_requests}
    )


@login_required(login_url="login")
def reg_user_approve(request, id):
    """Approve registration — open employee add form (no web portal login)."""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied!")
        return redirect("home")

    reg_request = get_object_or_404(EmpTemp, id=id)
    if reg_request.status != "PENDING":
        messages.error(request, "Registration request already processed!")
        return redirect("reg_user_list")

    messages.info(
        request,
        "Complete the employee profile. Employee can log in with mobile or Employee ID.",
    )
    return redirect(f"{reverse('employee_add')}?reg_id={id}")


@login_required(login_url="login")
def reg_user_reject(request, id):
    """Reject a registration request"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied!")
        return redirect("home")

    try:
        reg_request = get_object_or_404(EmpTemp, id=id)

        if reg_request.status != "PENDING":
            messages.error(request, "Registration request already processed!")
            return redirect("reg_user_list")

        reg_request.status = "REJECTED"
        reg_request.save()

        messages.success(request, f"Registration rejected for {reg_request.full_name}")
    except Exception as e:
        messages.error(request, f"Error rejecting registration: {str(e)}")

    return redirect("reg_user_list")


# ==================== LOCATION TRACKING ====================
import json
import math


@login_required(login_url="login")
def save_location_update(request):
    """
    API endpoint to receive a single location update from the frontend.
    Accepts POST with JSON body: {latitude, longitude, is_checkin_point, is_checkout_point}
    Returns JSON {status: 'ok'}.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        latitude = float(data.get("latitude", 0))
        longitude = float(data.get("longitude", 0))
        is_checkin_point = bool(data.get("is_checkin_point", False))
        is_checkout_point = bool(data.get("is_checkout_point", False))
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "message": "Invalid data"}, status=400)

    if latitude == 0 and longitude == 0:
        return JsonResponse({"status": "error", "message": "Invalid coordinates"}, status=400)

    emp = find_emp_for_auth_user(request.user)
    if not emp:
        return JsonResponse({"status": "error", "message": "Employee not found"}, status=403)

    if not _employee_gps_enabled(emp):
        return JsonResponse(
            {"status": "skipped", "message": "GPS tracking is disabled for this employee"}
        )

    from datetime import date

    session_date = date.today()

    if is_checkout_point:
        saved = _save_tracking_point(
            request.user,
            emp,
            latitude,
            longitude,
            session_date,
            is_checkout=True,
        )
    elif is_checkin_point:
        saved = _save_tracking_point(
            request.user,
            emp,
            latitude,
            longitude,
            session_date,
            is_checkin=True,
        )
    else:
        if not _has_active_checkin(emp, session_date):
            return JsonResponse(
                {"status": "error", "message": "No active check-in session"},
                status=400,
            )
        saved = _save_tracking_point(
            request.user,
            emp,
            latitude,
            longitude,
            session_date,
        )

    if not saved:
        return JsonResponse({"status": "skipped", "message": "Duplicate or too soon"})

    return JsonResponse({"status": "ok"})


@login_required(login_url="login")
def employee_location_map(request, emp_id, session_date):
    """
    View an employee's movement map for a given session date.
    Admins can view any employee; employees can view their own records only.
    """
    from datetime import datetime

    is_admin = request.user.is_staff or request.user.is_superuser or (
        request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )

    if not is_admin:
        own_emp = _get_own_employee(request)
        if not own_emp:
            messages.error(request, "Access denied!")
            return redirect("home")
        try:
            if int(own_emp.emp_id) != int(emp_id):
                messages.error(request, "Access denied!")
                return redirect("attendance_list")
        except (ValueError, TypeError):
            if str(own_emp.emp_id) != str(emp_id):
                messages.error(request, "Access denied!")
                return redirect("attendance_list")

    try:
        session_date_obj = datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date.")
        return redirect("attendance_list")

    locations = _get_location_records(emp_id, session_date_obj)
    location_points = _build_location_points(locations)

    try:
        emp = EmpMaster.objects.get(emp_id=str(emp_id))
        emp_name = emp.full_name or emp_id
    except EmpMaster.DoesNotExist:
        try:
            emp = EmpMaster.objects.get(emp_id=str(int(emp_id)))
            emp_name = emp.full_name or emp_id
        except (EmpMaster.DoesNotExist, ValueError, TypeError):
            att = AttendanceMaster.objects.filter(
                emp_id=int(emp_id), att_date=session_date_obj
            ).first()
            emp_name = att.full_name if att else emp_id

    context = {
        "emp_id": emp_id,
        "emp_name": emp_name,
        "session_date": session_date,
        "location_points_json": json.dumps(location_points),
        "location_count": len(location_points),
    }
    return render(request, "accounts/employee_location_map.html", context)


# ==================== VISITOR / CLIENT MANAGEMENT ====================


@login_required(login_url="login")
def visitor_add(request):
    """
    Any logged-in employee can add a client-visit record.
    The logged-in user is auto-attached; employees cannot change who added the record.
    """
    import base64
    import uuid
    from django.core.files.base import ContentFile
    from .models import ClientVisitor
    from datetime import date

    # Resolve linked employee (if any)
    own_emp = find_emp_for_auth_user(request.user)

    if request.method == "POST":
        client_name = request.POST.get("client_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        location = request.POST.get("location", "").strip()
        notes = request.POST.get("notes", "").strip()
        visit_date = request.POST.get("visit_date", "") or str(date.today())
        photo_data = request.POST.get("photo_data", "").strip()

        if not client_name:
            messages.error(request, "Client Name is required.")
            return redirect("visitor_add")

        visitor = ClientVisitor(
            user=request.user,
            emp_id=own_emp.emp_id if own_emp else "",
            emp_name=(
                own_emp.full_name
                if own_emp
                else request.user.get_full_name() or request.user.username
            ),
            client_name=client_name,
            phone=phone,
            location=location,
            notes=notes,
            visit_date=visit_date,
        )
        visitor.save()

        # Save base64 camera photo if provided
        if photo_data and photo_data.startswith("data:image/"):
            try:
                header, imgstr = photo_data.split(";base64,", 1)
                ext = header.split("/")[-1].lower()
                if ext not in ("jpeg", "jpg", "png", "webp"):
                    ext = "jpeg"
                filename = f"visitor_{uuid.uuid4().hex}.{ext}"
                visitor.photo.save(
                    filename, ContentFile(base64.b64decode(imgstr)), save=True
                )
            except Exception:
                pass  # Photo is optional; ignore decode errors

        messages.success(request, f"Client '{client_name}' added successfully.")
        return redirect("visitor_list")

    context = {
        "today": date.today().strftime("%Y-%m-%d"),
        "own_emp": own_emp,
    }
    return render(request, "accounts/visitor_add.html", context)


@login_required(login_url="login")
def visitor_list(request):
    """
    Employees see only their own records.
    Admin / staff see all records with search + employee filter.
    """
    from .models import ClientVisitor

    is_admin = request.user.is_staff or request.user.is_superuser
    search = request.GET.get("q", "").strip()
    emp_filter = request.GET.get(
        "emp_filter", ""
    ).strip()  # admin-only filter by emp_name

    if is_admin:
        qs = ClientVisitor.objects.all()
        if emp_filter:
            qs = qs.filter(emp_name=emp_filter)
        if search:
            qs = (
                qs.filter(client_name__icontains=search)
                | qs.filter(emp_name__icontains=search)
                | qs.filter(phone__icontains=search)
            )
        # Distinct employee names for the filter dropdown
        emp_choices = (
            ClientVisitor.objects.values_list("emp_name", flat=True)
            .exclude(emp_name__isnull=True)
            .exclude(emp_name="")
            .distinct()
            .order_by("emp_name")
        )
    else:
        qs = ClientVisitor.objects.filter(user=request.user)
        if search:
            qs = qs.filter(client_name__icontains=search) | qs.filter(
                phone__icontains=search
            )
        emp_choices = []

    context = {
        "visitors": qs.order_by("-created_at"),
        "is_admin": is_admin,
        "search": search,
        "emp_filter": emp_filter,
        "emp_choices": emp_choices,
    }
    return render(request, "accounts/visitor_list.html", context)


@login_required(login_url="login")
def visitor_view(request, id):
    """Read-only detail view for a visitor record."""
    from .models import ClientVisitor

    visitor = get_object_or_404(ClientVisitor, id=id)
    is_admin = request.user.is_staff or request.user.is_superuser

    if not is_admin and visitor.user != request.user:
        messages.error(request, "Access denied.")
        return redirect("visitor_list")

    return render(
        request,
        "accounts/visitor_view.html",
        {"visitor": visitor, "is_admin": is_admin},
    )


@login_required(login_url="login")
def visitor_edit(request, id):
    """
    Edit an existing visitor record.
    Employees can only edit their own. Admins can edit any.
    """
    import base64
    import uuid
    from django.core.files.base import ContentFile
    from .models import ClientVisitor
    from datetime import date

    visitor = get_object_or_404(ClientVisitor, id=id)
    is_admin = request.user.is_staff or request.user.is_superuser

    if not is_admin and visitor.user != request.user:
        messages.error(request, "You are not allowed to edit this record.")
        return redirect("visitor_list")

    if request.method == "POST":
        client_name = request.POST.get("client_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        location = request.POST.get("location", "").strip()
        notes = request.POST.get("notes", "").strip()
        visit_date = request.POST.get("visit_date", "").strip() or str(date.today())
        photo_data = request.POST.get("photo_data", "").strip()

        if not client_name:
            messages.error(request, "Client Name is required.")
            return redirect("visitor_edit", id=id)

        visitor.client_name = client_name
        visitor.phone = phone
        visitor.location = location
        visitor.notes = notes
        visitor.visit_date = visit_date
        visitor.save()

        # Save new camera photo if captured
        if photo_data and photo_data.startswith("data:image/"):
            try:
                header, imgstr = photo_data.split(";base64,", 1)
                ext = header.split("/")[-1].lower()
                if ext not in ("jpeg", "jpg", "png", "webp"):
                    ext = "jpeg"
                filename = f"visitor_{uuid.uuid4().hex}.{ext}"
                # Delete old photo file before saving new one
                if visitor.photo:
                    visitor.photo.delete(save=False)
                visitor.photo.save(
                    filename, ContentFile(base64.b64decode(imgstr)), save=True
                )
            except Exception:
                pass  # Photo is optional; ignore decode errors

        messages.success(request, f"Visitor record for '{client_name}' updated.")
        return redirect("visitor_list")

    context = {
        "visitor": visitor,
        "today": date.today().strftime("%Y-%m-%d"),
    }
    return render(request, "accounts/visitor_edit.html", context)


@login_required(login_url="login")
def visitor_delete(request, id):
    """
    Employees can only delete their own records.
    Admins can delete any record.
    """
    from .models import ClientVisitor

    visitor = get_object_or_404(ClientVisitor, id=id)
    is_admin = request.user.is_staff or request.user.is_superuser

    if not is_admin and visitor.user != request.user:
        messages.error(request, "You are not allowed to delete this record.")
        return redirect("visitor_list")

    client_name = visitor.client_name
    visitor.delete()
    messages.success(request, f"Visitor record for '{client_name}' deleted.")
    return redirect("visitor_list")

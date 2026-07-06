from datetime import datetime, time as time_cls

from .models import ShiftMaster
from .shift_rotation_utils import get_rotated_shift, is_shift_rotation_enabled

DEFAULT_SHIFTS = [
    {
        "shift_name": "General",
        "check_in": time_cls(9, 30),
        "check_out": time_cls(18, 30),
        "grace_minutes": 10,
        "description": "Standard office shift (9:30 AM – 6:30 PM)",
        "rotation_order": 0,
    },
    {
        "shift_name": "Morning",
        "check_in": time_cls(7, 0),
        "check_out": time_cls(15, 0),
        "grace_minutes": 10,
        "description": "Morning shift (7:00 AM – 3:00 PM)",
        "rotation_order": 1,
    },
    {
        "shift_name": "Evening",
        "check_in": time_cls(14, 0),
        "check_out": time_cls(22, 0),
        "grace_minutes": 10,
        "description": "Evening shift (2:00 PM – 10:00 PM)",
        "rotation_order": 2,
    },
    {
        "shift_name": "Night",
        "check_in": time_cls(22, 0),
        "check_out": time_cls(6, 0),
        "grace_minutes": 15,
        "description": "Night shift (10:00 PM – 6:00 AM)",
        "rotation_order": 3,
    },
]


def ensure_default_shifts():
    for shift in DEFAULT_SHIFTS:
        ShiftMaster.objects.update_or_create(
            shift_name=shift["shift_name"],
            defaults={
                "check_in": shift["check_in"],
                "check_out": shift["check_out"],
                "grace_minutes": shift["grace_minutes"],
                "description": shift["description"],
                "is_active": 1,
                "rotation_order": shift.get("rotation_order", 0),
            },
        )


def get_active_shifts():
    ensure_default_shifts()
    return ShiftMaster.objects.filter(is_active=1).order_by("rotation_order", "shift_name")


def get_shift_for_employee(emp, att_date=None):
    if att_date is not None and is_shift_rotation_enabled():
        rotated = get_rotated_shift(emp, att_date)
        if rotated:
            return rotated

    if not emp:
        return None
    name = (getattr(emp, "shift", None) or "").strip()
    if name:
        shift = ShiftMaster.objects.filter(shift_name=name, is_active=1).first()
        if shift:
            return shift
    return ShiftMaster.objects.filter(shift_name="General", is_active=1).first()


def get_scheduled_check_in(emp, att_date=None):
    shift = get_shift_for_employee(emp, att_date)
    if shift and shift.check_in:
        return shift.check_in
    if emp and emp.check_in:
        return emp.check_in
    return time_cls(9, 30)


def get_scheduled_check_out(emp, att_date=None):
    shift = get_shift_for_employee(emp, att_date)
    if shift and shift.check_out:
        return shift.check_out
    if emp and emp.check_out:
        return emp.check_out
    return time_cls(18, 30)


def get_late_grace_minutes(emp, att_date=None):
    shift = get_shift_for_employee(emp, att_date)
    if shift:
        return int(shift.grace_minutes or 10)
    return 10


def get_shift_label(emp, att_date=None):
    shift = get_shift_for_employee(emp, att_date)
    if shift:
        return shift.shift_name
    return (getattr(emp, "shift", None) or "").strip() or "General"


def employee_late_penalty_enabled(emp):
    if emp is None:
        return True
    val = getattr(emp, "late_attendance_penalty", None)
    if val is None:
        return True
    try:
        return int(val) != 0
    except (TypeError, ValueError):
        return True


def calc_late_minutes(emp, check_in_time, att_date):
    """Minutes late after grace period; 0 if on time or penalty disabled."""
    if not employee_late_penalty_enabled(emp):
        return 0
    if not check_in_time or not att_date:
        return 0

    office_time = get_scheduled_check_in(emp, att_date)
    grace = get_late_grace_minutes(emp, att_date)
    try:
        office_dt = datetime.combine(att_date, office_time)
        checkin_dt = datetime.combine(att_date, check_in_time)
        diff = int((checkin_dt - office_dt).total_seconds() / 60)
        return max(0, diff - grace)
    except (TypeError, ValueError):
        return 0


def attendance_status_for_check_in(emp, check_in_time, att_date):
    if calc_late_minutes(emp, check_in_time, att_date) > 0:
        return "Late"
    return "Present"


def fmt_late_display(minutes):
    if not minutes or minutes <= 0:
        return "-"
    h, m = divmod(int(minutes), 60)
    if h:
        return f"{h}h {m}m"
    return f"{m} min"

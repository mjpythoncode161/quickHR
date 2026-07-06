"""Automatic shift rotation for attendance late/on-time checks."""

from datetime import date

from .models import ShiftMaster, ShiftRotationConfig


def ensure_shift_rotation_defaults():
    config, _ = ShiftRotationConfig.objects.get_or_create(
        pk=1,
        defaults={
            "enabled": 0,
            "cycle_days": 7,
            "rotation_start_date": date.today(),
            "stagger_employees": 1,
        },
    )
    return config


def get_shift_rotation_config():
    ensure_shift_rotation_defaults()
    return ShiftRotationConfig.objects.filter(pk=1).first()


def is_shift_rotation_enabled():
    config = get_shift_rotation_config()
    return bool(config and config.enabled)


def get_rotation_shifts():
    return list(
        ShiftMaster.objects.filter(is_active=1).order_by("rotation_order", "shift_name")
    )


def _employee_rotation_offset(emp, shift_count):
    if not emp or shift_count <= 0:
        return 0
    try:
        return int(emp.emp_id) % shift_count
    except (TypeError, ValueError):
        return abs(hash(str(emp.emp_id))) % shift_count


def get_rotated_shift(emp, att_date):
    """Return ShiftMaster for employee on att_date when rotation is enabled."""
    config = get_shift_rotation_config()
    if not config or not config.enabled:
        return None

    shifts = get_rotation_shifts()
    if not shifts:
        return None

    d = att_date or date.today()
    start = config.rotation_start_date or date.today()
    days = max(0, (d - start).days)
    cycle = max(1, int(config.cycle_days or 7))
    period = days // cycle

    offset = (
        _employee_rotation_offset(emp, len(shifts))
        if config.stagger_employees
        else 0
    )
    idx = (period + offset) % len(shifts)
    return shifts[idx]


def get_effective_shift_name(emp, att_date=None):
    rotated = get_rotated_shift(emp, att_date)
    if rotated:
        return rotated.shift_name
    return (getattr(emp, "shift", None) or "").strip() or "General"


def get_rotation_periods(count=5):
    """Upcoming rotation period date ranges from today."""
    from datetime import timedelta

    config = get_shift_rotation_config()
    if not config or not config.enabled:
        return []

    start = config.rotation_start_date or date.today()
    cycle = max(1, int(config.cycle_days or 7))
    today = date.today()
    days_since = max(0, (today - start).days)
    current_period = days_since // cycle

    periods = []
    for i in range(count):
        p_start = start + timedelta(days=(current_period + i) * cycle)
        p_end = p_start + timedelta(days=cycle - 1)
        label = (
            f"{p_start.strftime('%d %b')}"
            if cycle <= 1
            else f"{p_start.strftime('%d %b')} – {p_end.strftime('%d %b %Y')}"
        )
        periods.append(
            {
                "index": i,
                "period_start": p_start,
                "period_end": p_end,
                "label": label,
                "is_current": i == 0,
            }
        )
    return periods


def get_employee_rotation_schedule(emp, periods=None):
    """Shift name for each upcoming rotation period."""
    if periods is None:
        periods = get_rotation_periods()
    schedule = []
    for period in periods:
        shift = get_rotated_shift(emp, period["period_start"])
        schedule.append(
            {
                "period": period,
                "shift_name": shift.shift_name if shift else "—",
                "shift": shift,
            }
        )
    return schedule


def get_employees_on_shift(shift_name, att_date, employees):
    """Employees effectively on shift_name for att_date."""
    from .shift_utils import get_shift_label

    name = (shift_name or "").strip()
    return [
        emp
        for emp in employees
        if get_shift_label(emp, att_date) == name
    ]


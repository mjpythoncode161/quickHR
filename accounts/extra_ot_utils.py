"""Extra overtime (OT) pay — settings and all-employee OT summary."""

import json
import time
from decimal import Decimal

from .models import EmpMaster, ExtraOtConfig
from .payroll_module_utils import get_payroll_module_config, is_module_enabled


def ensure_extra_ot_defaults():
    config, _ = ExtraOtConfig.objects.get_or_create(pk=1)
    return config


def is_extra_ot_active():
    payroll = get_payroll_module_config()
    if not is_module_enabled(payroll, "extra_ot_working"):
        return False
    cfg = ensure_extra_ot_defaults()
    return bool(cfg.enabled)


def _scheduled_hours_per_day(emp):
    from .views import _scheduled_hours_per_day as sched_hours

    return sched_hours(emp) or 8.0


def calc_daily_salary(emp, config):
    try:
        salary = Decimal(str(emp.salary_amt or 0))
    except Exception:
        return Decimal("0")
    if salary <= 0:
        return Decimal("0")

    salary_type = (emp.salary_type or "Monthly").strip().lower()
    if salary_type == "hourly":
        sched_h = Decimal(str(_scheduled_hours_per_day(emp)))
        return (salary * sched_h).quantize(Decimal("0.01"))

    days = max(1, int(config.working_days_per_month or 26))
    return (salary / Decimal(str(days))).quantize(Decimal("0.01"))


def calc_ot_hourly_base(emp, config):
    """Derive base hourly rate from employee salary for OT multiplier mode."""
    try:
        salary = float(emp.salary_amt or 0)
    except (TypeError, ValueError):
        return 0.0
    if salary <= 0:
        return 0.0

    salary_type = (emp.salary_type or "Monthly").strip().lower()
    if salary_type == "hourly":
        return salary

    sched_h = _scheduled_hours_per_day(emp)
    days = max(1, int(config.working_days_per_month or 26))
    return salary / (days * sched_h)


def calc_hourly_ot_rate(emp, config):
    mode = (config.ot_rate_mode or ExtraOtConfig.RATE_MULTIPLIER).strip()
    if mode == ExtraOtConfig.RATE_FIXED:
        return Decimal(str(config.ot_hourly_rate or 0))
    hourly = Decimal(str(calc_ot_hourly_base(emp, config)))
    mult = Decimal(str(config.ot_multiplier or 2))
    return (hourly * mult).quantize(Decimal("0.01"))


def _basis_hours_for_day(day_row, config):
    worked_m = int(day_row.get("worked_minutes") or 0)
    ot_m = int(day_row.get("overtime_minutes") or 0)
    basis = (config.hours_basis or ExtraOtConfig.BASIS_OT_ONLY).strip()
    if basis == ExtraOtConfig.BASIS_TOTAL_WORKED:
        return Decimal(str(worked_m)) / Decimal("60")
    return Decimal(str(ot_m)) / Decimal("60")


def calc_day_ot_pay_slab(emp, basis_hours, config):
    """Slab: hourly below half threshold; half day + hourly; full day + extra hourly."""
    basis_hours = Decimal(str(basis_hours or 0))
    if basis_hours <= 0:
        return Decimal("0.00"), "none"

    daily = calc_daily_salary(emp, config)
    hourly_ot = calc_hourly_ot_rate(emp, config)
    half_th = Decimal(str(config.half_day_threshold_hours or 2))
    full_th = Decimal(str(config.full_day_threshold_hours or 8))
    if full_th <= half_th:
        full_th = half_th + Decimal("1")

    if basis_hours >= full_th:
        extra_h = basis_hours - full_th
        pay = daily + (extra_h * hourly_ot)
        return pay.quantize(Decimal("0.01")), "full_plus_extra"

    if basis_hours >= half_th:
        extra_h = basis_hours - half_th
        pay = (daily * Decimal("0.5")) + (extra_h * hourly_ot)
        return pay.quantize(Decimal("0.01")), "half_plus_extra"

    pay = basis_hours * hourly_ot
    return pay.quantize(Decimal("0.01")), "hourly"


def calc_ot_pay_shift_mode(emp, ot_minutes, config):
    if not ot_minutes or ot_minutes <= 0:
        return Decimal("0.00")
    ot_hours = Decimal(str(ot_minutes)) / Decimal("60")
    hourly_ot = calc_hourly_ot_rate(emp, config)
    return (ot_hours * hourly_ot).quantize(Decimal("0.01"))


def calc_monthly_ot_from_report(emp, report, config):
    """Auto-calculate monthly OT pay using selected client policy."""
    policy = (config.calc_policy or ExtraOtConfig.CALC_SHIFT_OT).strip()
    total_ot_minutes = 0
    total_pay = Decimal("0.00")
    half_days = 0
    full_plus_days = 0
    hourly_days = 0

    for day_row in report.get("days", []):
        if day_row.get("status") not in ("P", "HD"):
            continue
        ot_m = int(day_row.get("overtime_minutes") or 0)
        total_ot_minutes += ot_m

        if policy == ExtraOtConfig.CALC_SLAB_HALF_FULL:
            basis_h = _basis_hours_for_day(day_row, config)
            day_pay, slab = calc_day_ot_pay_slab(emp, basis_h, config)
            total_pay += day_pay
            if slab == "full_plus_extra":
                full_plus_days += 1
            elif slab == "half_plus_extra":
                half_days += 1
            elif slab == "hourly" and basis_h > 0:
                hourly_days += 1
        else:
            total_pay += calc_ot_pay_shift_mode(emp, ot_m, config)

    return {
        "ot_minutes": total_ot_minutes,
        "ot_pay": total_pay if config.enabled else Decimal("0.00"),
        "half_day_ot_count": half_days,
        "full_day_ot_count": full_plus_days,
        "hourly_ot_days": hourly_days,
        "calc_policy": policy,
    }


def calc_ot_pay_amount(emp, ot_minutes, config):
    return calc_ot_pay_shift_mode(emp, ot_minutes, config)


def get_employee_ot_summary(emp, month, year, config=None):
    from .views import _build_monthly_attendance_report_data, _fmt_hm_total

    config = config or ensure_extra_ot_defaults()
    report = _build_monthly_attendance_report_data(emp, int(month), int(year))
    result = calc_monthly_ot_from_report(emp, report, config)

    policy = result["calc_policy"]
    policy_label = "Shift OT (hourly)"
    if policy == ExtraOtConfig.CALC_SLAB_HALF_FULL:
        policy_label = (
            f"Slab: ≥{config.half_day_threshold_hours}h Half Day, "
            f"≥{config.full_day_threshold_hours}h Full+Extra"
        )

    return {
        "emp": emp,
        "ot_minutes": result["ot_minutes"],
        "ot_hours_display": _fmt_hm_total(result["ot_minutes"]),
        "ot_pay": result["ot_pay"],
        "has_ot": result["ot_minutes"] > 0,
        "half_day_ot_count": result["half_day_ot_count"],
        "full_day_ot_count": result["full_day_ot_count"],
        "hourly_ot_days": result["hourly_ot_days"],
        "calc_policy_label": policy_label,
        "salary_amt": emp.salary_amt or "0",
        "salary_type": emp.salary_type or "Monthly",
    }


def get_all_employees_ot_rows(month, year, config=None):
    config = config or ensure_extra_ot_defaults()
    rows = []
    total_ot_minutes = 0
    total_ot_pay = Decimal("0.00")
    total_half = 0
    total_full = 0
    affected_count = 0

    for emp in EmpMaster.objects.all().order_by("full_name", "emp_id"):
        row = get_employee_ot_summary(emp, month, year, config)
        rows.append(row)
        total_ot_minutes += row["ot_minutes"]
        total_ot_pay += row["ot_pay"]
        total_half += row["half_day_ot_count"]
        total_full += row["full_day_ot_count"]
        if row["has_ot"]:
            affected_count += 1

    from .views import _fmt_hm_total

    policy = (config.calc_policy or ExtraOtConfig.CALC_SHIFT_OT).strip()
    return {
        "rows": rows,
        "total_ot_minutes": total_ot_minutes,
        "total_ot_display": _fmt_hm_total(total_ot_minutes),
        "total_ot_pay": total_ot_pay,
        "total_half_day_count": total_half,
        "total_full_day_count": total_full,
        "affected_count": affected_count,
        "employee_count": len(rows),
        "calc_policy": policy,
    }


def _debug_log(message, data=None, hypothesis_id="EOT"):
    # #region agent log
    try:
        from pathlib import Path

        log_path = Path(__file__).resolve().parent.parent.parent / "debug-72a37d.log"
        payload = {
            "sessionId": "72a37d",
            "hypothesisId": hypothesis_id,
            "location": "extra_ot_utils.py",
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass
    # #endregion

"""Per-employee subscription pricing (monthly / yearly) — editable in Super Admin."""

from decimal import Decimal

from .models import SaasPlatformConfig

DEFAULT_PRICE_PER_EMPLOYEE = Decimal("1000")
DEFAULT_MIN_PAID_EMPLOYEES = 10
DEFAULT_YEARLY_MONTHS_BILLED = 10
DEFAULT_TRIAL_DAYS = 7
DEFAULT_TRIAL_MAX_EMPLOYEES = 25
DEFAULT_FREE_MAX_EMPLOYEES = 2


def get_pricing_config():
    cfg = SaasPlatformConfig.objects.filter(pk=1).first()
    rate = DEFAULT_PRICE_PER_EMPLOYEE
    min_emp = DEFAULT_MIN_PAID_EMPLOYEES
    yearly_months = DEFAULT_YEARLY_MONTHS_BILLED
    trial_days = DEFAULT_TRIAL_DAYS
    trial_max_employees = DEFAULT_TRIAL_MAX_EMPLOYEES
    free_max_employees = DEFAULT_FREE_MAX_EMPLOYEES
    if cfg:
        if cfg.price_per_employee_monthly:
            rate = Decimal(str(cfg.price_per_employee_monthly))
        if cfg.min_paid_employees:
            min_emp = int(cfg.min_paid_employees)
        if cfg.yearly_months_billed:
            yearly_months = int(cfg.yearly_months_billed)
        if getattr(cfg, "trial_days", None):
            trial_days = int(cfg.trial_days)
        if getattr(cfg, "trial_max_employees", None):
            trial_max_employees = int(cfg.trial_max_employees)
        if getattr(cfg, "free_max_employees", None):
            free_max_employees = int(cfg.free_max_employees)
    return {
        "price_per_employee": rate,
        "min_paid_employees": min_emp,
        "yearly_months_billed": yearly_months,
        "yearly_free_months": max(0, 12 - yearly_months),
        "trial_days": trial_days,
        "trial_max_employees": trial_max_employees,
        "free_max_employees": free_max_employees,
    }


def normalize_employee_count(raw_count, min_paid=None):
    cfg = get_pricing_config()
    minimum = min_paid if min_paid is not None else cfg["min_paid_employees"]
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        count = minimum
    return max(minimum, count)


def calculate_subscription_quote(employee_count, billing_period="monthly"):
    cfg = get_pricing_config()
    count = normalize_employee_count(employee_count)
    period = (billing_period or "monthly").strip().lower()
    if period not in ("monthly", "yearly"):
        period = "monthly"

    rate = cfg["price_per_employee"]
    if period == "yearly":
        multiplier = cfg["yearly_months_billed"]
        period_label = f"yearly ({cfg['yearly_months_billed']} months)"
    else:
        multiplier = 1
        period_label = "monthly"

    total = count * rate * multiplier
    return {
        "employee_count": count,
        "billing_period": period,
        "billing_period_label": period_label,
        "price_per_employee": rate,
        "multiplier": multiplier,
        "total_inr": total,
        "total_paise": int(total * 100),
        "formula": f"{count} × ₹{int(rate)} × {multiplier} = ₹{int(total)}",
    }

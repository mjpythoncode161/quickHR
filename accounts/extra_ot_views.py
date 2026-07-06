from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from .extra_ot_utils import (
    _debug_log,
    ensure_extra_ot_defaults,
    get_all_employees_ot_rows,
    is_extra_ot_active,
)
from .models import ExtraOtConfig
from .payroll_module_utils import get_payroll_module_config, is_module_enabled


def _decimal_post(request, key, default, minimum=None):
    try:
        val = float(request.POST.get(key, default) or default)
        if minimum is not None:
            val = max(minimum, val)
        return val
    except (TypeError, ValueError):
        return default


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def extra_ot_working(request):
    payroll = get_payroll_module_config()
    if not is_module_enabled(payroll, "extra_ot_working"):
        messages.error(request, "Extra OT Working is disabled in Payroll Settings.")
        return redirect("payroll_module_settings")

    config = ensure_extra_ot_defaults()
    today = date.today()
    month = int(request.GET.get("month") or request.POST.get("month") or today.month)
    year = int(request.GET.get("year") or request.POST.get("year") or today.year)

    if request.method == "POST" and request.POST.get("form_type") == "settings":
        config.enabled = 1 if request.POST.get("enabled") else 0

        calc_policy = request.POST.get("calc_policy", ExtraOtConfig.CALC_SHIFT_OT)
        if calc_policy not in (ExtraOtConfig.CALC_SHIFT_OT, ExtraOtConfig.CALC_SLAB_HALF_FULL):
            calc_policy = ExtraOtConfig.CALC_SHIFT_OT
        config.calc_policy = calc_policy

        hours_basis = request.POST.get("hours_basis", ExtraOtConfig.BASIS_OT_ONLY)
        if hours_basis not in (ExtraOtConfig.BASIS_OT_ONLY, ExtraOtConfig.BASIS_TOTAL_WORKED):
            hours_basis = ExtraOtConfig.BASIS_OT_ONLY
        config.hours_basis = hours_basis

        config.half_day_threshold_hours = _decimal_post(request, "half_day_threshold_hours", 2.0, 0.5)
        config.full_day_threshold_hours = _decimal_post(request, "full_day_threshold_hours", 8.0, 1.0)
        if float(config.full_day_threshold_hours) <= float(config.half_day_threshold_hours):
            config.full_day_threshold_hours = float(config.half_day_threshold_hours) + 1

        config.ot_rate_mode = request.POST.get("ot_rate_mode", ExtraOtConfig.RATE_MULTIPLIER)
        if config.ot_rate_mode not in (ExtraOtConfig.RATE_MULTIPLIER, ExtraOtConfig.RATE_FIXED):
            config.ot_rate_mode = ExtraOtConfig.RATE_MULTIPLIER
        config.ot_multiplier = _decimal_post(request, "ot_multiplier", 2.0, 1)
        config.ot_hourly_rate = _decimal_post(request, "ot_hourly_rate", 0, 0)
        config.working_days_per_month = int(_decimal_post(request, "working_days_per_month", 26, 1))

        config.save()
        _debug_log(
            "extra_ot_settings_saved",
            {
                "enabled": config.enabled,
                "calc_policy": config.calc_policy,
                "hours_basis": config.hours_basis,
                "half_th": str(config.half_day_threshold_hours),
                "full_th": str(config.full_day_threshold_hours),
                "mode": config.ot_rate_mode,
            },
            "EOT-H1",
        )
        messages.success(request, "Extra OT settings saved — automatic pay uses your client rules.")
        return redirect(f"{request.path}?month={month}&year={year}")

    summary = get_all_employees_ot_rows(month, year, config)
    _debug_log(
        "extra_ot_summary_loaded",
        {
            "month": month,
            "year": year,
            "policy": summary.get("calc_policy"),
            "affected": summary["affected_count"],
            "half_days": summary["total_half_day_count"],
            "full_days": summary["total_full_day_count"],
            "total_pay": str(summary["total_ot_pay"]),
        },
        "EOT-H2",
    )

    years = list(range(today.year - 2, today.year + 2))
    return render(
        request,
        "accounts/extra_ot_working.html",
        {
            "config": config,
            "month": month,
            "year": year,
            "years": years,
            "months": list(range(1, 13)),
            "summary": summary,
            "ot_active": is_extra_ot_active(),
            "rate_multiplier": ExtraOtConfig.RATE_MULTIPLIER,
            "rate_fixed": ExtraOtConfig.RATE_FIXED,
            "calc_shift_ot": ExtraOtConfig.CALC_SHIFT_OT,
            "calc_slab": ExtraOtConfig.CALC_SLAB_HALF_FULL,
            "basis_ot": ExtraOtConfig.BASIS_OT_ONLY,
            "basis_total": ExtraOtConfig.BASIS_TOTAL_WORKED,
        },
    )

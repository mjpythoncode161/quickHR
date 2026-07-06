from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from .models import PayrollModuleConfig
from .payroll_module_utils import (
    MODULE_KEYS,
    PAYROLL_MODULES,
    _debug_log,
    ensure_payroll_module_defaults,
    get_module_by_key,
    is_module_enabled,
)


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def payroll_module_settings(request):
    ensure_payroll_module_defaults()
    config = PayrollModuleConfig.objects.get(pk=1)

    if request.method == "POST":
        enabled_map = {}
        for key in MODULE_KEYS:
            val = 1 if request.POST.get(key) else 0
            setattr(config, key, val)
            enabled_map[key] = val
        config.save()
        # #region agent log
        _debug_log(
            "payroll_module_settings_saved",
            {"enabled": enabled_map},
            hypothesis_id="H1",
        )
        # #endregion
        messages.success(request, "Payroll module settings saved.")
        return redirect("payroll_module_settings")

    modules = []
    for mod in PAYROLL_MODULES:
        modules.append(
            {
                **mod,
                "enabled": is_module_enabled(config, mod["key"]),
            }
        )

    return render(
        request,
        "accounts/payroll_module_settings.html",
        {"config": config, "modules": modules},
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def payroll_module_page(request, module_key):
    mod = get_module_by_key(module_key)
    if not mod:
        messages.error(request, "Unknown payroll module.")
        return redirect("settings_hub")

    config = ensure_payroll_module_defaults()
    if not is_module_enabled(config, module_key):
        messages.error(request, f"{mod['name']} is disabled in Payroll Settings.")
        return redirect("payroll_module_settings")

    return render(
        request,
        "accounts/payroll_module_placeholder.html",
        {"module": mod},
    )

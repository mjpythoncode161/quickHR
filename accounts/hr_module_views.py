from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .hr_module_utils import HR_MODULES, MODULE_KEYS, ensure_hr_module_defaults, is_hr_module_enabled
from .models import HrModuleConfig


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def hr_module_settings(request):
    ensure_hr_module_defaults()
    config = HrModuleConfig.objects.get(pk=1)

    if request.method == "POST":
        for key in MODULE_KEYS:
            setattr(config, key, 1 if request.POST.get(key) else 0)
        config.save()
        messages.success(request, "HR module settings saved.")
        return redirect("hr_module_settings")

    modules = []
    for mod in HR_MODULES:
        if mod["key"] == "hr_module_settings":
            continue
        modules.append({**mod, "enabled": is_hr_module_enabled(mod["key"])})

    return render(
        request,
        "accounts/hr_module_settings.html",
        {"config": config, "modules": modules},
    )

"""HR module on/off configuration."""

from .models import HrModuleConfig

HR_MODULES = [
    {
        "key": "recruitment",
        "name": "Recruitment Management",
        "desc": "Jobs, candidates, interviews, offers, joining & platform APIs",
        "icon": "fas fa-user-tie",
        "url_name": "recruitment_dashboard",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "claims",
        "name": "Claims / Expense Reimbursement",
        "desc": "Employees submit expense claims; HR approves and tracks payment",
        "icon": "fas fa-receipt",
        "url_name": "claim_list",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "hr_module_settings",
        "name": "HR Module Settings",
        "desc": "Enable or disable HR modules",
        "icon": "fas fa-sliders-h",
        "url_name": "hr_module_settings",
        "show_in_hub": True,
        "show_in_sidebar": False,
        "always_on_hub": True,
    },
]

MODULE_KEYS = [m["key"] for m in HR_MODULES if m["key"] != "hr_module_settings"]


def ensure_hr_module_defaults():
    config, _ = HrModuleConfig.objects.get_or_create(pk=1, defaults={"claims": 0})
    return config


def get_hr_module_config():
    ensure_hr_module_defaults()
    return HrModuleConfig.objects.filter(pk=1).first()


def is_hr_module_enabled(key):
    config = get_hr_module_config()
    if not config:
        return False
    return bool(getattr(config, key, 0))


def get_hr_modules_map():
    config = get_hr_module_config()
    return {m["key"]: is_hr_module_enabled(m["key"]) for m in HR_MODULES if m["key"] != "hr_module_settings"}


def get_hr_hub_items():
    config = get_hr_module_config()
    items = []
    for mod in HR_MODULES:
        if not mod.get("show_in_hub"):
            continue
        if mod.get("always_on_hub") or is_hr_module_enabled(mod["key"]):
            item = {
                "name": mod["name"],
                "icon": mod["icon"],
                "desc": mod["desc"],
                "key": mod["key"],
            }
            if mod.get("url_name"):
                item["url_name"] = mod["url_name"]
            items.append(item)
    if is_hr_module_enabled("recruitment"):
        items.append(
            {
                "name": "Recruitment Settings",
                "icon": "fas fa-plug",
                "desc": "Job board API keys — LinkedIn, Naukri, Indeed & webhook",
                "key": "recruitment_settings",
                "url_name": "recruitment_settings",
            }
        )
    if is_hr_module_enabled("claims"):
        items.append(
            {
                "name": "Claim Categories",
                "icon": "fas fa-tags",
                "desc": "Create and manage dynamic claim type dropdown",
                "key": "claim_categories",
                "url_name": "claim_category_settings",
            }
        )
    return items


def claims_module_required(view_func):
    from functools import wraps
    from django.contrib import messages
    from django.shortcuts import redirect

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_hr_module_enabled("claims"):
            messages.error(request, "Claims module is disabled in HR Module Settings.")
            if request.user.is_staff or request.user.is_superuser:
                return redirect("hr_module_settings")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


def recruitment_module_required(view_func):
    from functools import wraps
    from django.contrib import messages
    from django.shortcuts import redirect

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_hr_module_enabled("recruitment"):
            messages.error(request, "Recruitment module is disabled in HR Module Settings.")
            if request.user.is_staff or request.user.is_superuser:
                return redirect("hr_module_settings")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper

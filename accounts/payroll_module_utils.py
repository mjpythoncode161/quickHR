"""Payroll module on/off configuration for Settings and sidebar."""

import json
import time

from .models import PayrollModuleConfig

PAYROLL_MODULES = [
    {
        "key": "employee_salary_setup",
        "name": "Employee Salary Setup",
        "desc": "Salary breakdown section on employee add and edit forms",
        "icon": "fas fa-user-tag",
        "url_name": None,
        "show_in_hub": True,
        "show_in_sidebar": False,
    },
    {
        "key": "salary_structure",
        "name": "Salary Structure",
        "desc": "Configure Basic, HRA, PF, fixed and remaining components",
        "icon": "fas fa-percent",
        "url_name": "salary_structure_settings",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "deductions",
        "name": "Deductions",
        "desc": "Manage salary deduction rules (PF, TDS, loans, etc.)",
        "icon": "fas fa-minus-circle",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "deductions"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "employer_contributions",
        "name": "Employer Contributions",
        "desc": "Employer PF, ESI, gratuity and other contributions",
        "icon": "fas fa-hand-holding-usd",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "employer_contributions"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "attendance_integration",
        "name": "Attendance Integration",
        "desc": "Link attendance, LOP and late penalties to payroll",
        "icon": "fas fa-link",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "attendance_integration"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "payroll_processing",
        "name": "Payroll Processing",
        "desc": "Run monthly payroll batch and salary processing",
        "icon": "fas fa-cogs",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "payroll_processing"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "statutory_compliance",
        "name": "Statutory Compliance (India)",
        "desc": "PF, ESI, PT, TDS and Indian statutory settings",
        "icon": "fas fa-balance-scale",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "statutory_compliance"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "payslip",
        "name": "Payslip",
        "desc": "Generate and download employee payslips",
        "icon": "fas fa-file-invoice-dollar",
        "url_name": "payslip_generate",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "extra_ot_working",
        "name": "Extra OT Working",
        "desc": "ON/OFF extra overtime pay — OT hours and pay amount for all employees",
        "icon": "fas fa-business-time",
        "url_name": "extra_ot_working",
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "payroll_reports",
        "name": "Reports",
        "desc": "Payroll summary, salary register and finance reports",
        "icon": "fas fa-chart-bar",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "payroll_reports"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "payroll_approvals",
        "name": "Payroll Approvals",
        "desc": "Approve payroll runs before payment",
        "icon": "fas fa-check-double",
        "url_name": "payroll_module_page",
        "url_kwargs": {"module_key": "payroll_approvals"},
        "show_in_hub": True,
        "show_in_sidebar": True,
    },
    {
        "key": "payroll_settings",
        "name": "Payroll Settings",
        "desc": "Enable or disable payroll modules for this company",
        "icon": "fas fa-sliders-h",
        "url_name": "payroll_module_settings",
        "show_in_hub": True,
        "show_in_sidebar": True,
        "always_on_hub": True,
    },
]

MODULE_KEYS = [m["key"] for m in PAYROLL_MODULES]


def ensure_payroll_module_defaults():
    config, _ = PayrollModuleConfig.objects.get_or_create(pk=1)
    return config


def get_payroll_module_config():
    ensure_payroll_module_defaults()
    return PayrollModuleConfig.objects.filter(pk=1).first()


def is_module_enabled(config, key):
    if not config:
        return True
    return bool(getattr(config, key, 1))


def get_enabled_modules_map():
    config = get_payroll_module_config()
    return {m["key"]: is_module_enabled(config, m["key"]) for m in PAYROLL_MODULES}


def get_payroll_hub_items():
    """Build settings hub cards for enabled payroll modules."""
    config = get_payroll_module_config()
    items = []
    for mod in PAYROLL_MODULES:
        if not mod.get("show_in_hub"):
            continue
        if mod.get("always_on_hub") or is_module_enabled(config, mod["key"]):
            item = {
                "name": mod["name"],
                "icon": mod["icon"],
                "desc": mod["desc"],
                "key": mod["key"],
            }
            if mod.get("url_name"):
                item["url_name"] = mod["url_name"]
                if mod.get("url_kwargs"):
                    item["url_kwargs"] = mod["url_kwargs"]
            items.append(item)
    return items


def get_payroll_sidebar_items():
    """Sidebar links for enabled payroll modules."""
    config = get_payroll_module_config()
    items = []
    for mod in PAYROLL_MODULES:
        if not mod.get("show_in_sidebar") or not mod.get("url_name"):
            continue
        if is_module_enabled(config, mod["key"]):
            entry = {
                "name": mod["name"],
                "url_name": mod["url_name"],
                "icon": mod["icon"],
                "key": mod["key"],
            }
            if mod.get("url_kwargs"):
                entry["url_kwargs"] = mod["url_kwargs"]
            items.append(entry)
    return items


def any_payroll_sidebar_visible():
    return len(get_payroll_sidebar_items()) > 0


def get_module_by_key(key):
    for mod in PAYROLL_MODULES:
        if mod["key"] == key:
            return mod
    return None


def _debug_log(message, data=None, hypothesis_id="PM"):
    # #region agent log
    try:
        from pathlib import Path

        log_path = Path(__file__).resolve().parent.parent.parent / "debug-72a37d.log"
        payload = {
            "sessionId": "72a37d",
            "hypothesisId": hypothesis_id,
            "location": "payroll_module_utils.py",
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # #endregion

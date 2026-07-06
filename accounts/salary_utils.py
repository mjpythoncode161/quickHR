"""Configurable salary structure for employee add/edit and payslip."""

import json
from decimal import Decimal

from .models import SalaryComponentRule, SalaryStructureConfig

CALC_METHOD_LABELS = {
    "pct_gross": "% of Gross",
    "pct_basic": "% of Basic",
    "fixed": "Fixed",
    "remaining": "Remaining",
}

CALC_METHOD_TO_AMT_TYPE = {
    "pct_gross": "PctGross",
    "pct_basic": "PctBasic",
    "fixed": "Fixed",
    "remaining": "Remaining",
}

AMT_TYPE_TO_CALC_METHOD = {
    "PctGross": "pct_gross",
    "PctBasic": "pct_basic",
    "Percentage": "pct_basic",
    "Fixed": "fixed",
    "Remaining": "remaining",
}

DEFAULT_COMPONENTS = [
    {
        "component_name": "Basic Salary",
        "calc_method": "pct_gross",
        "rate_value": 40,
        "item_type": "Earning",
        "sort_order": 1,
    },
    {
        "component_name": "HRA",
        "calc_method": "pct_basic",
        "rate_value": 40,
        "item_type": "Earning",
        "sort_order": 2,
    },
    {
        "component_name": "Conveyance",
        "calc_method": "fixed",
        "rate_value": 19200,
        "item_type": "Earning",
        "sort_order": 3,
    },
    {
        "component_name": "Medical Allowance",
        "calc_method": "fixed",
        "rate_value": 15000,
        "item_type": "Earning",
        "sort_order": 4,
    },
    {
        "component_name": "Special Allowance",
        "calc_method": "remaining",
        "rate_value": 0,
        "item_type": "Earning",
        "sort_order": 5,
    },
    {
        "component_name": "PF",
        "calc_method": "pct_basic",
        "rate_value": 12,
        "item_type": "Deduction",
        "sort_order": 6,
    },
]


def ensure_salary_structure_defaults():
    config, _ = SalaryStructureConfig.objects.get_or_create(
        pk=1,
        defaults={
            "salary_base_mode": "gross",
            "salary_field_label": "Gross Salary (₹)",
            "show_basic_row": 1,
        },
    )
    if not SalaryComponentRule.objects.exists():
        for row in DEFAULT_COMPONENTS:
            SalaryComponentRule.objects.create(
                component_name=row["component_name"],
                calc_method=row["calc_method"],
                rate_value=row["rate_value"],
                item_type=row["item_type"],
                sort_order=row["sort_order"],
                is_active=1,
            )
    return config


def get_salary_config():
    ensure_salary_structure_defaults()
    return SalaryStructureConfig.objects.filter(pk=1).first()


def get_active_salary_components():
    ensure_salary_structure_defaults()
    return list(
        SalaryComponentRule.objects.filter(is_active=1).order_by("sort_order", "id")
    )


def component_to_dict(comp, rate_override=None):
    rate = rate_override if rate_override is not None else float(comp.rate_value or 0)
    return {
        "id": comp.id,
        "name": comp.component_name,
        "calc_method": comp.calc_method,
        "calc_label": CALC_METHOD_LABELS.get(comp.calc_method, comp.calc_method),
        "rate_value": rate,
        "item_type": comp.item_type,
        "sort_order": comp.sort_order,
        "amt_type": CALC_METHOD_TO_AMT_TYPE.get(comp.calc_method, "Fixed"),
    }


def get_other_emp_items(existing_items):
    """Employee-specific items not defined in salary structure settings."""
    if not existing_items:
        return []
    components = get_active_salary_components()
    config_names = {c.component_name.strip().upper() for c in components}
    return [
        item
        for item in existing_items
        if (item.item_name or "").strip().upper() not in config_names
    ]


def get_salary_structure_for_form(existing_items=None):
    """Build template context for employee add/edit salary section."""
    config = get_salary_config()
    components = get_active_salary_components()
    existing_map = {}
    if existing_items:
        for item in existing_items:
            key = (item.item_name or "").strip().upper()
            if key:
                existing_map[key] = item

    component_rows = []
    for comp in components:
        key = comp.component_name.strip().upper()
        rate_override = None
        if key in existing_map:
            try:
                rate_override = float(existing_map[key].item_amt or 0)
            except (TypeError, ValueError):
                rate_override = None
        component_rows.append(component_to_dict(comp, rate_override))

    return {
        "salary_config": config,
        "salary_components": component_rows,
        "salary_components_json": json.dumps(component_rows),
        "salary_base_mode": config.salary_base_mode if config else "gross",
        "salary_field_label": (
            config.salary_field_label if config else "Gross Salary (₹)"
        ),
    }


def _to_float(val):
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0


def calculate_salary_breakdown(base_amount, components, base_mode="gross"):
    """
    Calculate all component amounts.
    base_amount: salary field value (gross or basic per base_mode).
    components: list of dicts with name, calc_method, rate_value, item_type.
    """
    base_amount = _to_float(base_amount)
    if base_amount <= 0:
        return {
            "rows": [],
            "basic": 0,
            "gross": 0,
            "total_earnings": 0,
            "total_deductions": 0,
            "net": 0,
        }

    gross = base_amount if base_mode == "gross" else 0
    basic = base_amount if base_mode == "basic" else 0
    rows = []
    earnings_total = 0
    deductions_total = 0

    ordered = sorted(components, key=lambda c: c.get("sort_order", 0))

    for comp in ordered:
        method = comp.get("calc_method") or "fixed"
        if method == "remaining":
            continue
        rate = _to_float(comp.get("rate_value"))
        name = comp.get("name") or comp.get("component_name") or ""
        item_type = comp.get("item_type") or "Earning"

        if method == "pct_gross":
            amount = round(gross * rate / 100, 2)
            if "basic" in name.lower():
                basic = amount
        elif method == "pct_basic":
            base_for_pct = basic if basic > 0 else (gross if gross else base_amount)
            amount = round(base_for_pct * rate / 100, 2)
        elif method == "fixed":
            amount = round(rate, 2)
        else:
            amount = 0

        row = {
            "name": name,
            "calc_method": method,
            "calc_label": CALC_METHOD_LABELS.get(method, method),
            "rate_value": rate,
            "amount": amount,
            "item_type": item_type,
            "amt_type": CALC_METHOD_TO_AMT_TYPE.get(method, "Fixed"),
        }
        rows.append(row)
        if item_type == "Deduction":
            deductions_total += amount
        else:
            earnings_total += amount

    for comp in ordered:
        if (comp.get("calc_method") or "") != "remaining":
            continue
        name = comp.get("name") or comp.get("component_name") or ""
        item_type = comp.get("item_type") or "Earning"
        target = gross if base_mode == "gross" else earnings_total
        if base_mode == "gross" and gross > 0:
            amount = round(max(0, gross - earnings_total), 2)
        else:
            amount = round(max(0, base_amount - earnings_total), 2)
        rows.append(
            {
                "name": name,
                "calc_method": "remaining",
                "calc_label": CALC_METHOD_LABELS["remaining"],
                "rate_value": 0,
                "amount": amount,
                "item_type": item_type,
                "amt_type": "Remaining",
            }
        )
        if item_type == "Deduction":
            deductions_total += amount
        else:
            earnings_total += amount

    if base_mode == "gross":
        final_gross = gross
    else:
        final_gross = earnings_total
        basic = base_amount

    return {
        "rows": rows,
        "basic": round(basic, 2),
        "gross": round(final_gross, 2),
        "total_earnings": round(earnings_total, 2),
        "total_deductions": round(deductions_total, 2),
        "net": round(earnings_total - deductions_total, 2),
    }


def build_breakdown_for_employee(salary_amt, emp_items, base_mode="gross"):
    """Salary breakdown using structure settings + per-employee rate overrides."""
    existing_map = {}
    for item in emp_items or []:
        key = (item.item_name or "").strip().upper()
        if key:
            existing_map[key] = item

    comp_dicts = []
    for comp in get_active_salary_components():
        key = comp.component_name.strip().upper()
        rate_override = None
        if key in existing_map:
            try:
                rate_override = float(existing_map[key].item_amt or 0)
            except (TypeError, ValueError):
                rate_override = None
        comp_dicts.append(component_to_dict(comp, rate_override))

    return calculate_salary_breakdown(salary_amt, comp_dicts, base_mode=base_mode)


def get_payslip_line_items(emp_id):
    """
    All payslip lines: active structure components (with defaults if not saved)
    plus custom employee items outside the structure.
    """
    from .models import EmpItemMaster

    emp_items = list(EmpItemMaster.objects.filter(emp_id=emp_id))
    emp_map = {(i.item_name or "").strip().upper(): i for i in emp_items}
    lines = []

    for comp in get_active_salary_components():
        key = comp.component_name.strip().upper()
        if key in emp_map:
            lines.append(emp_map[key])
        else:
            lines.append(
                EmpItemMaster(
                    emp_id=emp_id,
                    item_name=comp.component_name,
                    item_amt=comp.rate_value,
                    item_amt_type=CALC_METHOD_TO_AMT_TYPE.get(comp.calc_method, "Fixed"),
                    item_type=comp.item_type,
                )
            )

    lines.extend(get_other_emp_items(emp_items))
    return lines


def compute_emp_item_amount(item, salary_amt, proration_factor=1.0, breakdown=None):
    """Payslip line amount — uses employee rate/type with structure breakdown context."""
    if breakdown is None:
        config = get_salary_config()
        breakdown = calculate_salary_breakdown(
            salary_amt,
            [component_to_dict(c) for c in get_active_salary_components()],
            base_mode=config.salary_base_mode if config else "gross",
        )

    amt_type = (item.item_amt_type or "").strip()
    rate = _to_float(item.item_amt)
    basic = breakdown.get("basic") or _to_float(salary_amt)
    gross = breakdown.get("gross") or _to_float(salary_amt)
    name = (item.item_name or "").strip().upper()

    if amt_type == "PctGross":
        return round(gross * rate / 100 * proration_factor, 2)
    if amt_type in ("PctBasic", "Percentage"):
        return round(basic * rate / 100 * proration_factor, 2)
    if amt_type == "Remaining":
        for row in breakdown.get("rows", []):
            if (row.get("name") or "").strip().upper() == name:
                return round(row["amount"] * proration_factor, 2)
        return 0
    if amt_type == "Fixed" or not amt_type:
        return round(rate * proration_factor, 2)

    calc_method = AMT_TYPE_TO_CALC_METHOD.get(amt_type, "fixed")
    if calc_method == "pct_gross":
        return round(gross * rate / 100 * proration_factor, 2)
    if calc_method == "pct_basic":
        return round(basic * rate / 100 * proration_factor, 2)
    return round(rate * proration_factor, 2)

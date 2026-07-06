from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import SalaryComponentRule, SalaryStructureConfig
from .payroll_module_utils import get_payroll_module_config, is_module_enabled
from .salary_utils import CALC_METHOD_LABELS, ensure_salary_structure_defaults


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def salary_structure_settings(request):
    ensure_salary_structure_defaults()
    payroll_config = get_payroll_module_config()
    if not is_module_enabled(payroll_config, "salary_structure"):
        messages.error(request, "Salary Structure is disabled in Payroll Settings.")
        return redirect("payroll_module_settings")

    salary_config = SalaryStructureConfig.objects.get(pk=1)
    components = SalaryComponentRule.objects.all().order_by("sort_order", "id")

    if request.method == "POST":
        action = request.POST.get("action", "save_config")

        if action == "add_component":
            name = request.POST.get("component_name", "").strip()
            if not name:
                messages.error(request, "Component name is required.")
            else:
                SalaryComponentRule.objects.create(
                    component_name=name,
                    calc_method=request.POST.get("calc_method", "fixed"),
                    rate_value=request.POST.get("rate_value", "0") or 0,
                    item_type=request.POST.get("item_type", "Earning"),
                    sort_order=int(request.POST.get("sort_order", "99") or 99),
                    is_active=1,
                )
                messages.success(request, f"Component '{name}' added.")
            return redirect("salary_structure_settings")

        if action == "delete_component":
            comp_id = request.POST.get("component_id")
            if comp_id:
                SalaryComponentRule.objects.filter(id=comp_id).delete()
                messages.success(request, "Component removed.")
            return redirect("salary_structure_settings")

        salary_config.salary_base_mode = request.POST.get("salary_base_mode", "gross")
        salary_config.salary_field_label = request.POST.get(
            "salary_field_label", "Gross Salary (₹)"
        ).strip()
        salary_config.show_basic_row = 1 if request.POST.get("show_basic_row") else 0
        salary_config.save()

        names = request.POST.getlist("comp_id[]")
        for comp_id in names:
            comp = SalaryComponentRule.objects.filter(id=comp_id).first()
            if not comp:
                continue
            comp.component_name = request.POST.get(f"name_{comp_id}", comp.component_name).strip()
            comp.calc_method = request.POST.get(f"method_{comp_id}", comp.calc_method)
            comp.rate_value = request.POST.get(f"rate_{comp_id}", comp.rate_value) or 0
            comp.item_type = request.POST.get(f"type_{comp_id}", comp.item_type)
            comp.sort_order = int(request.POST.get(f"order_{comp_id}", comp.sort_order) or 0)
            comp.is_active = 1 if request.POST.get(f"active_{comp_id}") else 0
            comp.save()

        messages.success(request, "Salary structure settings saved.")
        return redirect("salary_structure_settings")

    return render(
        request,
        "accounts/salary_structure_settings.html",
        {
            "config": salary_config,
            "components": components,
            "calc_methods": CALC_METHOD_LABELS,
        },
    )

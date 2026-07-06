from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .claims_utils import get_active_claim_categories, resolve_claim_type_name
from .hr_module_utils import claims_module_required
from .models import ClaimCategory, EmpMaster, ExpenseClaim
from .role_utils import find_emp_for_auth_user


def _claims_is_admin(request):
    return (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    )


@login_required(login_url="login")
@claims_module_required
def claim_list(request):
    is_restricted = not _claims_is_admin(request)
    if is_restricted:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")
        claims = ExpenseClaim.objects.filter(emp_id=str(own_emp.emp_id)).order_by("-applied_at")
    else:
        claims = ExpenseClaim.objects.all().order_by("-applied_at")

    pending_count = sum(1 for c in claims if c.status == ExpenseClaim.STATUS_PENDING)
    return render(
        request,
        "accounts/claim_list.html",
        {
            "claims": claims,
            "is_restricted_user": is_restricted,
            "pending_count": pending_count,
        },
    )


@login_required(login_url="login")
@claims_module_required
def claim_add(request):
    is_restricted = not _claims_is_admin(request)
    own_emp = None
    if is_restricted:
        own_emp = find_emp_for_auth_user(request.user)
        if not own_emp:
            messages.error(request, "No employee record linked to your account.")
            return redirect("home")

    if request.method == "POST":
        if is_restricted:
            emp_id = str(own_emp.emp_id)
            full_name = own_emp.full_name or ""
        else:
            emp_id = request.POST.get("emp_id", "").strip()
            try:
                emp = EmpMaster.objects.get(emp_id=emp_id)
                full_name = emp.full_name or ""
            except EmpMaster.DoesNotExist:
                messages.error(request, "Select a valid employee.")
                return redirect("claim_add")

        claim_type = resolve_claim_type_name(
            category_id=request.POST.get("claim_category_id"),
            category_name=request.POST.get("claim_type", ""),
        )
        claim_date = request.POST.get("claim_date", "").strip()
        amount = request.POST.get("amount", "0").strip()
        description = request.POST.get("description", "").strip()
        receipt_note = request.POST.get("receipt_note", "").strip()

        if not claim_type or not claim_date or not amount:
            messages.error(request, "Claim type, date and amount are required.")
            return redirect("claim_add")

        ExpenseClaim.objects.create(
            emp_id=emp_id,
            full_name=full_name,
            claim_type=claim_type,
            claim_date=claim_date,
            amount=amount,
            description=description,
            receipt_note=receipt_note,
            status=ExpenseClaim.STATUS_PENDING,
        )
        from .notification_service import get_emp_for_claim, send_notification

        emp = get_emp_for_claim(emp_id)
        send_notification(
            "claim_submitted",
            context={
                "full_name": full_name,
                "claim_type": claim_type,
                "amount": amount,
                "claim_date": claim_date,
            },
            emp=emp,
            admin_alert=True,
        )
        messages.success(request, "Claim submitted successfully.")
        return redirect("claim_list")

    employees = [own_emp] if is_restricted else EmpMaster.objects.all().order_by("full_name")
    categories = get_active_claim_categories()
    return render(
        request,
        "accounts/claim_add.html",
        {
            "employees": employees,
            "is_restricted_user": is_restricted,
            "own_emp": own_emp,
            "claim_categories": categories,
        },
    )


@login_required(login_url="login")
@claims_module_required
def claim_approval_list(request):
    if not _claims_is_admin(request):
        messages.error(request, "You do not have permission to approve claims.")
        return redirect("claim_list")

    claims = ExpenseClaim.objects.filter(status=ExpenseClaim.STATUS_PENDING).order_by("-applied_at")
    return render(request, "accounts/claim_approval_list.html", {"claims": claims})


@login_required(login_url="login")
@claims_module_required
def claim_status_update(request, id):
    if not _claims_is_admin(request):
        messages.error(request, "You do not have permission.")
        return redirect("claim_list")

    claim = get_object_or_404(ExpenseClaim, id=id)
    action = request.POST.get("action", "")
    remarks = request.POST.get("admin_remarks", "").strip()

    if action == "approve":
        claim.status = ExpenseClaim.STATUS_APPROVED
        claim.admin_remarks = remarks
        claim.reviewed_at = timezone.now()
        claim.reviewed_by = request.user.get_full_name() or request.user.username
        claim.save()
        from .notification_service import get_emp_for_claim, send_notification

        emp = get_emp_for_claim(claim.emp_id)
        send_notification(
            "claim_approved",
            context={
                "full_name": claim.full_name,
                "claim_type": claim.claim_type,
                "amount": claim.amount,
                "remarks": remarks or "—",
            },
            emp=emp,
        )
        messages.success(request, f"Claim #{claim.id} approved.")
    elif action == "reject":
        claim.status = ExpenseClaim.STATUS_REJECTED
        claim.admin_remarks = remarks
        claim.reviewed_at = timezone.now()
        claim.reviewed_by = request.user.get_full_name() or request.user.username
        claim.save()
        from .notification_service import get_emp_for_claim, send_notification

        emp = get_emp_for_claim(claim.emp_id)
        send_notification(
            "claim_rejected",
            context={
                "full_name": claim.full_name,
                "claim_type": claim.claim_type,
                "amount": claim.amount,
                "remarks": remarks or "—",
            },
            emp=emp,
        )
        messages.success(request, f"Claim #{claim.id} rejected.")
    elif action == "paid":
        claim.status = ExpenseClaim.STATUS_PAID
        claim.admin_remarks = remarks or claim.admin_remarks
        claim.reviewed_at = timezone.now()
        claim.reviewed_by = request.user.get_full_name() or request.user.username
        claim.save()
        from .notification_service import get_emp_for_claim, send_notification

        emp = get_emp_for_claim(claim.emp_id)
        send_notification(
            "claim_paid",
            context={
                "full_name": claim.full_name,
                "claim_type": claim.claim_type,
                "amount": claim.amount,
                "remarks": remarks or "—",
            },
            emp=emp,
        )
        messages.success(request, f"Claim #{claim.id} marked as paid.")

    return redirect(request.POST.get("next", "claim_approval_list"))


@login_required(login_url="login")
@claims_module_required
def claim_category_settings(request):
    if not _claims_is_admin(request):
        messages.error(request, "You do not have permission to manage claim categories.")
        return redirect("claim_list")

    categories = ClaimCategory.objects.all().order_by("sort_order", "category_name")

    if request.method == "POST":
        action = request.POST.get("action", "save_all")

        if action == "add_category":
            name = request.POST.get("category_name", "").strip()
            if not name:
                messages.error(request, "Category name is required.")
            elif ClaimCategory.objects.filter(category_name=name).exists():
                messages.error(request, "Category already exists.")
            else:
                ClaimCategory.objects.create(
                    category_name=name,
                    description=request.POST.get("description", "").strip(),
                    sort_order=int(request.POST.get("sort_order", "99") or 99),
                    is_active=1,
                )
                messages.success(request, f"Category '{name}' added.")
            return redirect("claim_category_settings")

        if action == "delete_category":
            cat_id = request.POST.get("category_id")
            cat = ClaimCategory.objects.filter(id=cat_id).first()
            if cat:
                in_use = ExpenseClaim.objects.filter(claim_type=cat.category_name).exists()
                if in_use:
                    messages.error(request, "Cannot delete — claims exist with this category.")
                else:
                    cat.delete()
                    messages.success(request, "Category deleted.")
            return redirect("claim_category_settings")

        for cat in categories:
            cat.category_name = request.POST.get(f"name_{cat.id}", cat.category_name).strip()
            cat.description = request.POST.get(f"desc_{cat.id}", cat.description).strip()
            cat.sort_order = int(request.POST.get(f"order_{cat.id}", cat.sort_order) or 0)
            cat.is_active = 1 if request.POST.get(f"active_{cat.id}") else 0
            cat.save()

        messages.success(request, "Claim categories saved.")
        return redirect("claim_category_settings")

    return render(
        request,
        "accounts/claim_category_settings.html",
        {"categories": categories},
    )

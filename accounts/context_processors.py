from datetime import date
import os
import uuid

from django.conf import settings

from .models import Users, EmpMaster, SystemSettings, LogoMaster, SaasPlatformConfig
from .payroll_module_utils import (
    any_payroll_sidebar_visible,
    get_enabled_modules_map,
    get_payroll_sidebar_items,
)
from .role_utils import (
    can_access_web_portal,
    find_emp_for_auth_user,
    find_legacy_user,
    is_employee_portal_user,
)
from .shift_rotation_utils import is_shift_rotation_enabled
from .hr_module_utils import get_hr_modules_map, is_hr_module_enabled
from .notification_module_utils import (
    any_notification_sidebar_visible,
    get_notification_sidebar_items,
    is_notification_module_enabled,
)
from .notification_service import get_unread_count
from .subscription_utils import get_subscription_context
from .subscription_pricing import get_pricing_config


def _resolve_logo_url(logo=None, company=None):
    if logo is None:
        logo = LogoMaster.objects.order_by("-created_at").first()
    if company is None:
        company = SystemSettings.objects.first()

    if logo and logo.image_path:
        path = logo.image_path.strip()
        if path.startswith(("http://", "https://", "/")):
            return path
        return f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"

    if company and company.cover_img:
        path = company.cover_img.strip()
        if path.startswith(("http://", "https://", "/")):
            return path
        return f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"

    return None


def save_company_logo(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".png"

    filename = f"logo_{uuid.uuid4().hex}{ext}"
    rel_path = os.path.join("company", filename).replace("\\", "/")
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    with open(abs_path, "wb+") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)

    logo = LogoMaster()
    logo.image_name = uploaded_file.name
    logo.image_path = rel_path
    logo.created_at = date.today()
    logo.save()
    return rel_path


def user_approval_status(request):
    user_approved = False
    user_is_employee = False

    if request.user.is_authenticated:
        emp = find_emp_for_auth_user(request.user)
        if can_access_web_portal(request.user):
            if is_employee_portal_user(request.user):
                user_is_employee = True
                user_approved = True
            else:
                user_approved = True
                user_is_employee = False
        elif emp:
            user_approved = False
            user_is_employee = True

    return {"user_approved": user_approved, "user_is_employee": user_is_employee}


def company_info(request):
    company = SystemSettings.objects.first()
    logo = LogoMaster.objects.order_by("-created_at").first()
    raw_name = (company.name or "").strip() if company else ""

    platform = SaasPlatformConfig.objects.filter(pk=1).first()
    product_name = (
        (platform.platform_name or "").strip() if platform else ""
    ) or "QuickHR"

    # Never show vendor name in HRMS UI — use QuickHR product branding
    if raw_name.upper() == "INDATAAI":
        display_name = product_name
    else:
        display_name = raw_name or product_name

    return {
        "company_settings": company,
        "company": company,
        "company_logo": logo,
        "company_logo_url": _resolve_logo_url(logo, company),
        "system_name": display_name,
        "product_name": product_name,
        "company_display_name": raw_name or display_name,
        "payroll_modules": get_enabled_modules_map(),
        "payroll_sidebar_items": get_payroll_sidebar_items(),
        "payroll_sidebar_visible": any_payroll_sidebar_visible(),
        "shift_rotation_enabled": is_shift_rotation_enabled(),
        "hr_modules": get_hr_modules_map(),
        "claims_module_enabled": is_hr_module_enabled("claims"),
        "recruitment_module_enabled": is_hr_module_enabled("recruitment"),
        "notification_sidebar_visible": any_notification_sidebar_visible(),
        "notification_sidebar_items": get_notification_sidebar_items(),
        "in_app_alerts_enabled": is_notification_module_enabled("in_app_alerts"),
        "notification_unread_count": get_unread_count(
            request.user.id if request.user.is_authenticated else None
        ),
        **get_subscription_context(),
        "trial_days": get_pricing_config()["trial_days"],
    }

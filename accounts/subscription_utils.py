"""SaaS subscription limits: trial, free tier, and paid plans."""

import hashlib
import json
import os
import time
from datetime import date, timedelta

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

from .models import EmpMaster, SaasOrganization, SaasSubscription, Users
from .role_utils import ensure_default_roles, sync_user_role
from .subscription_pricing import get_pricing_config

DEFAULT_PAID_PLAN_KEY = "business"


def _pricing():
    return get_pricing_config()


def _debug_sub_log(location, message, data, hypothesis_id="H-SUB-LIMIT"):
    # #region agent log
    log_path = os.path.normpath(os.path.join(settings.BASE_DIR, "..", "debug-72a37d.log"))
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(
                    {
                        "sessionId": "72a37d",
                        "location": location,
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                        "hypothesisId": hypothesis_id,
                        "runId": "trial-full-access",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion


def get_active_subscription():
    return (
        SaasSubscription.objects.filter(status=SaasSubscription.STATUS_ACTIVE)
        .select_related("plan")
        .order_by("-updated_at")
        .first()
    )


def has_paid_subscription():
    return get_active_subscription() is not None


def get_organization():
    return SaasOrganization.objects.order_by("-created_at").first()


def _ensure_trial_end_date(org):
    if not org or org.status != SaasOrganization.STATUS_TRIAL:
        return org
    if not org.trial_ends_at:
        created = org.created_at.date() if org.created_at else date.today()
        org.trial_ends_at = created + timedelta(days=_pricing()["trial_days"])
        org.save(update_fields=["trial_ends_at"])
    return org


def has_active_trial():
    org = get_organization()
    if not org or org.status != SaasOrganization.STATUS_TRIAL:
        return False
    org = _ensure_trial_end_date(org)
    if org.trial_ends_at and org.trial_ends_at < date.today():
        return False
    return True


def trial_days_left():
    org = get_organization()
    if not org or not has_active_trial():
        return 0
    if not org.trial_ends_at:
        return _pricing()["trial_days"]
    return max(0, (org.trial_ends_at - date.today()).days)


def has_full_plan_access():
    return has_paid_subscription() or has_active_trial()


def get_employee_limit():
    cfg = _pricing()
    free_limit = cfg["free_max_employees"]
    trial_limit = cfg["trial_max_employees"]
    sub = get_active_subscription()
    if sub:
        if getattr(sub, "employee_count", None) and sub.employee_count > free_limit:
            return int(sub.employee_count)
        if sub.plan:
            return int(sub.plan.max_employees or free_limit)
    if has_active_trial():
        org = get_organization()
        return int(org.max_employees or trial_limit) if org else trial_limit
    org = get_organization()
    if org:
        return int(org.max_employees or free_limit)
    return free_limit


def count_employees():
    return EmpMaster.objects.count()


def employees_remaining():
    return max(0, get_employee_limit() - count_employees())


def can_add_employee(user=None):
    if user is not None and getattr(user, "is_superuser", False):
        return True
    return count_employees() < get_employee_limit()


def geo_location_enabled():
    enabled = has_full_plan_access()
    # #region agent log
    _debug_sub_log(
        "subscription_utils.py:geo_location_enabled",
        "gps access check",
        {
            "enabled": enabled,
            "paid": has_paid_subscription(),
            "trial_active": has_active_trial(),
            "trial_days_left": trial_days_left(),
        },
        "H-TRIAL-GPS",
    )
    # #endregion
    return enabled


def employee_limit_message():
    limit = get_employee_limit()
    if has_paid_subscription():
        return (
            f"Your plan allows up to {limit} employees. "
            "Upgrade your subscription to add more."
        )
    if has_active_trial():
        days = trial_days_left()
        cfg = _pricing()
        return (
            f"Your {cfg['trial_days']}-day trial allows up to {limit} employees with GPS enabled. "
            f"{days} day(s) remaining — subscribe to continue after trial."
        )
    return (
        f"Free plan includes up to {_pricing()['free_max_employees']} employees (no GPS). "
        "Start a free trial or subscribe for full access."
    )


def get_subscribe_url(plan_key=None):
    key = plan_key or DEFAULT_PAID_PLAN_KEY
    return reverse("subscribe_plan", kwargs={"plan_key": key})


def get_subscription_context():
    limit = get_employee_limit()
    current = count_employees()
    paid = has_paid_subscription()
    trial_active = has_active_trial()
    full_access = has_full_plan_access()
    cfg = _pricing()
    return {
        "subscription_paid": paid,
        "subscription_trial_active": trial_active,
        "subscription_trial_days_left": trial_days_left(),
        "subscription_trial_days": cfg["trial_days"],
        "subscription_geo_enabled": full_access,
        "subscription_full_features": full_access,
        "subscription_employee_limit": limit,
        "subscription_employee_count": current,
        "subscription_employees_remaining": max(0, limit - current),
        "subscription_at_limit": current >= limit,
        "subscription_free_tier": not paid and not trial_active,
        "subscription_free_limit": cfg["free_max_employees"],
    }


def provision_trial_organization(phone, email, full_name):
    """Full-feature trial: GPS, all modules — limits from Super Admin pricing settings."""
    phone = (phone or "").strip()
    cfg = _pricing()
    trial_end = date.today() + timedelta(days=cfg["trial_days"])
    trial_limit = cfg["trial_max_employees"]
    existing = SaasOrganization.objects.filter(admin_phone=phone).first()
    if existing:
        existing.status = SaasOrganization.STATUS_TRIAL
        existing.trial_ends_at = trial_end
        existing.max_employees = trial_limit
        existing.save(update_fields=["status", "trial_ends_at", "max_employees"])
        org = existing
    else:
        base_slug = slugify(full_name or phone)[:90] or "org"
        slug = base_slug
        counter = 1
        while SaasOrganization.objects.filter(org_slug=slug).exists():
            slug = f"{base_slug}-{counter}"[:100]
            counter += 1
        org = SaasOrganization.objects.create(
            org_name=full_name or "My Company",
            org_slug=slug,
            admin_name=full_name,
            admin_email=email,
            admin_phone=phone,
            status=SaasOrganization.STATUS_TRIAL,
            trial_ends_at=trial_end,
            max_employees=trial_limit,
        )
    _debug_sub_log(
        "subscription_utils.py:provision_trial_organization",
        "trial org provisioned",
        {
            "org_id": org.id,
            "trial_ends_at": str(org.trial_ends_at),
            "max_employees": org.max_employees,
            "phone": phone[-4:],
        },
        "H-TRIAL-GPS",
    )
    return org


def provision_free_organization(phone, email, full_name):
    """Limited free tier — used before paid subscription completes."""
    phone = (phone or "").strip()
    free_limit = _pricing()["free_max_employees"]
    existing = SaasOrganization.objects.filter(admin_phone=phone).first()
    if existing:
        if existing.max_employees < free_limit and not has_paid_subscription():
            existing.max_employees = free_limit
            existing.save(update_fields=["max_employees"])
        return existing

    base_slug = slugify(full_name or phone)[:90] or "org"
    slug = base_slug
    counter = 1
    while SaasOrganization.objects.filter(org_slug=slug).exists():
        slug = f"{base_slug}-{counter}"[:100]
        counter += 1

    org = SaasOrganization.objects.create(
        org_name=full_name or "My Company",
        org_slug=slug,
        admin_name=full_name,
        admin_email=email,
        admin_phone=phone,
        status=SaasOrganization.STATUS_TRIAL,
        max_employees=free_limit,
    )
    return org


def setup_company_owner_account(phone, email, full_name, password):
    """Activate HR admin portal access for company owner (trial / subscribe signup)."""
    ensure_default_roles()
    hashed = hashlib.md5(password.encode()).hexdigest()
    legacy = Users.objects.filter(contact=phone).first()
    if legacy:
        legacy.full_name = full_name
        legacy.email = email
        legacy.type = 1
        legacy.password = hashed
        legacy.save()
    else:
        legacy = Users.objects.create(
            full_name=full_name,
            email=email,
            password=hashed,
            contact=phone,
            type=1,
        )
    sync_user_role(legacy)
    return legacy

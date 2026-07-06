"""SaaS platform helpers and seed data."""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import (
    SaasContactInquiry,
    SaasOrganization,
    SaasPlatformConfig,
    SaasPricingPlan,
    SaasProduct,
    SaasService,
)
from .payroll_module_utils import PAYROLL_MODULES

HR_MODULES = [
    (
        "Employees",
        "fas fa-users",
        "Employee master, departments, designations, registration requests & role management.",
    ),
    (
        "Attendance",
        "far fa-check-square",
        "GPS & selfie check-in/out, attendance list, shift management, late coming reports.",
    ),
    (
        "Leaves",
        "fas fa-paper-plane",
        "Leave applications, leave balance, approval workflow & leave calendar.",
    ),
    (
        "Claims",
        "fas fa-receipt",
        "Expense claims, categories, submission, multi-level approvals & reimbursements.",
    ),
    (
        "Holiday Management",
        "fas fa-calendar-alt",
        "Company holiday calendar, public holidays, weekly offs & holiday planning.",
    ),
    (
        "Payroll",
        "fas fa-calculator",
        "End-to-end payroll — salary structure, processing, payslip & statutory compliance.",
    ),
    (
        "Notifications",
        "fas fa-bell",
        "Email, SMS, WhatsApp & in-app alerts for HR, managers and employees.",
    ),
    (
        "Reports",
        "fas fa-chart-line",
        "Attendance grid, monthly PDF reports, selfie & location logs, late coming analytics.",
    ),
    (
        "Visitor Management",
        "fas fa-handshake",
        "Visitor check-in records, client visits, gate pass & visitor history.",
    ),
    (
        "Super Admin",
        "fas fa-shield-alt",
        "Multi-organization SaaS control, landing CMS, plans & platform administration.",
    ),
    (
        "Settings",
        "fas fa-cog",
        "Company profile, payroll modules, API settings, system configuration & user roles.",
    ),
    (
        "Recruitment",
        "fas fa-user-tie",
        "Job posting, candidate database, interviews, offer letters & joining process.",
    ),
]

DEFAULT_PRODUCTS = [
    ("employees", "Employees", "fas fa-users", "Employee master, departments & registration", 1),
    ("attendance", "Attendance", "far fa-check-square", "GPS check-in/out, shifts & late reports", 2),
    ("leaves", "Leaves", "fas fa-paper-plane", "Leave requests, balance & approvals", 3),
    ("claims", "Claims", "fas fa-receipt", "Expense claims with approval workflow", 4),
    ("holidays", "Holiday Management", "fas fa-calendar-alt", "Holiday calendar & weekly offs", 5),
    ("payroll", "Payroll", "fas fa-calculator", "Salary, payslip & statutory compliance", 6),
    ("notifications", "Notifications", "fas fa-bell", "Email, SMS, WhatsApp & in-app alerts", 7),
    ("reports", "Reports", "fas fa-chart-line", "Attendance grid, PDF & analytics reports", 8),
    ("visitors", "Visitor Management", "fas fa-handshake", "Visitor records & client visits", 9),
    ("recruitment", "Recruitment", "fas fa-user-tie", "Jobs, candidates, interviews & offers", 10),
    ("settings", "Settings", "fas fa-cog", "Company, payroll & system configuration", 11),
    ("super-admin", "Super Admin", "fas fa-shield-alt", "Multi-org SaaS platform control", 12),
]

DEFAULT_SERVICES = [
    ("Implementation", "fas fa-rocket", "Onboarding, data migration & go-live support", 1),
    ("Training", "fas fa-chalkboard-teacher", "Admin and employee training sessions", 2),
    ("Custom Integration", "fas fa-plug", "API, biometric & third-party integrations", 3),
    ("Dedicated Support", "fas fa-headset", "Priority support with SLA", 4),
]

TRIAL_DAYS = 7

OFFICE_ADDRESS = (
    "3rd Floor, Office No. 11, Stellar Mall, beside JGCC College, "
    "Jayanagar, Vidya Nagar, Hubballi, Karnataka 580021"
)

LANDING_STATS = [
    ("6+", "Years HR Tech Experience"),
    ("50+", "Companies Onboarded"),
    ("50K+", "Employees Managed"),
    ("12+", "HR Modules Included"),
]

TRUSTED_PARTNERS = [
    ("Bharat Steel", "BS", "#e11d48"),
    ("Metro Retail", "MR", "#2563eb"),
    ("Sunrise Logistics", "SL", "#ea580c"),
    ("GreenLeaf Pharma", "GP", "#16a34a"),
    ("NeoTech IT", "NT", "#7c3aed"),
    ("Ocean Exports", "OE", "#0891b2"),
    ("Prime Auto", "PA", "#dc2626"),
    ("Zenith Realty", "ZR", "#172c78"),
    ("Delta Foods", "DF", "#ca8a04"),
    ("Swift Finance", "SF", "#0d9488"),
]

REVIEW_BADGES = [
    ("Google", "4.8", 5),
    ("Capterra", "4.9", 5),
    ("G2", "4.7", 5),
]

DEFAULT_PLANS = [
    {
        "plan_key": "starter",
        "plan_name": "Starter",
        "price_monthly": 999,
        "price_yearly": 9990,
        "max_employees": 25,
        "description": "For small teams getting started",
        "features": "All 12 HR modules\nAttendance & leave\nEmployee portal\nEmail support",
        "sort_order": 1,
    },
    {
        "plan_key": "professional",
        "plan_name": "Professional",
        "price_monthly": 2499,
        "price_yearly": 24990,
        "max_employees": 100,
        "description": "Growing companies with full HR needs",
        "features": "All HR + payroll modules\nPayslip & statutory India\nRecruitment & claims\nNotifications & reports\nPriority support",
        "is_popular": 1,
        "sort_order": 2,
    },
    {
        "plan_key": "enterprise",
        "plan_name": "Enterprise",
        "price_monthly": 4999,
        "price_yearly": 49990,
        "max_employees": 500,
        "description": "Large organizations & multi-location",
        "features": "Full QuickHR platform\nAll payroll sub-modules\nAPI & biometric\nSuper Admin & multi-org\nCustom SLA",
        "sort_order": 3,
    },
]


def ensure_saas_defaults():
    cfg, _ = SaasPlatformConfig.objects.get_or_create(
        pk=1,
        defaults={
            "hero_title": "Best HRMS Software for Growing Indian Businesses",
            "hero_subtitle": (
                "QuickHR includes every HRMS module — Employees, Attendance, Leaves, Claims, "
                "Holiday Management, Payroll, Notifications, Reports, Visitor Management, "
                "Recruitment, Settings & Super Admin. Start your 7-day free trial today."
            ),
            "tagline": "Complete HRMS for modern organizations",
            "about_body": (
                "QuickHR is a cloud-based Human Resource Management System built for Indian "
                "organizations. We help HR teams automate attendance, payroll, recruitment, "
                "and employee self-service — so you can focus on people, not paperwork."
            ),
            "footer_text": "© QuickHR HRMS. All rights reserved.",
            "support_email": "support@quickhr.in",
            "support_phone": "+91 6361212012",
            "support_phone_2": "+91 9535347161",
            "office_address": OFFICE_ADDRESS,
        },
    )
    contact_updates = {}
    if not cfg.support_email:
        contact_updates["support_email"] = "support@quickhr.in"
    if not cfg.support_phone or cfg.support_phone == "+91 98765 43210":
        contact_updates["support_phone"] = "+91 6361212012"
    if not cfg.support_phone_2:
        contact_updates["support_phone_2"] = "+91 9535347161"
    if not cfg.office_address:
        contact_updates["office_address"] = OFFICE_ADDRESS
    if contact_updates:
        for field, value in contact_updates.items():
            setattr(cfg, field, value)
        cfg.save(update_fields=list(contact_updates.keys()))
    branding_updates = {}
    if cfg.tagline and "indataai" in cfg.tagline.lower():
        branding_updates["tagline"] = "Complete HRMS for modern organizations"
    if cfg.footer_text and "indataai" in cfg.footer_text.lower():
        branding_updates["footer_text"] = "© QuickHR HRMS. All rights reserved."
    if cfg.support_email and "indataai" in cfg.support_email.lower():
        branding_updates["support_email"] = "support@quickhr.in"
    if branding_updates:
        for field, value in branding_updates.items():
            setattr(cfg, field, value)
        cfg.save(update_fields=list(branding_updates.keys()))
    if not cfg.about_body:
        cfg.about_body = (
            "QuickHR is a cloud-based Human Resource Management System built for Indian "
            "organizations."
        )
        cfg.save(update_fields=["about_body"])

    pricing_defaults = {}
    if not cfg.price_per_employee_monthly:
        pricing_defaults["price_per_employee_monthly"] = 1000
    if not cfg.min_paid_employees:
        pricing_defaults["min_paid_employees"] = 10
    if not cfg.yearly_months_billed:
        pricing_defaults["yearly_months_billed"] = 10
    if not getattr(cfg, "trial_days", None):
        pricing_defaults["trial_days"] = 7
    if not getattr(cfg, "trial_max_employees", None):
        pricing_defaults["trial_max_employees"] = 25
    if pricing_defaults:
        for field, value in pricing_defaults.items():
            setattr(cfg, field, value)
        cfg.save(update_fields=list(pricing_defaults.keys()))

    if not SaasPricingPlan.objects.exists():
        for p in DEFAULT_PLANS:
            SaasPricingPlan.objects.create(**p)

    if not SaasProduct.objects.exists():
        for slug, title, icon, short_desc, order in DEFAULT_PRODUCTS:
            SaasProduct.objects.create(
                slug=slug,
                title=title,
                icon=icon,
                short_desc=short_desc,
                sort_order=order,
                description=short_desc,
            )
    else:
        for slug, title, icon, short_desc, order in DEFAULT_PRODUCTS:
            SaasProduct.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "icon": icon,
                    "short_desc": short_desc,
                    "description": short_desc,
                    "sort_order": order,
                    "is_active": 1,
                },
            )

    if not SaasService.objects.exists():
        for title, icon, short_desc, order in DEFAULT_SERVICES:
            SaasService.objects.create(
                title=title,
                icon=icon,
                short_desc=short_desc,
                sort_order=order,
                description=short_desc,
            )

    return cfg


def get_platform_config():
    ensure_saas_defaults()
    return SaasPlatformConfig.objects.filter(pk=1).first()


def get_payroll_landing_modules():
    return [
        {
            "title": mod["name"],
            "icon": mod["icon"],
            "desc": mod["desc"],
        }
        for mod in PAYROLL_MODULES
        if mod["key"] != "payroll_settings"
    ]


def create_saas_lead(
    source,
    full_name,
    email,
    phone="",
    company="",
    plan_interest="",
    message="",
    subject="",
):
    """Record a marketing lead for Super Admin (registration, subscription, contact)."""
    from .models import SaasContactInquiry

    lead = SaasContactInquiry.objects.create(
        full_name=(full_name or "").strip()[:200],
        email=(email or "").strip()[:255],
        phone=(phone or "").strip()[:20],
        company=(company or "").strip()[:200],
        plan_interest=(plan_interest or "").strip()[:100],
        subject=(subject or source.replace("_", " ").title())[:200],
        message=(message or f"New {source} lead from QuickHR website.").strip(),
        source=(source or "contact")[:30],
        status="new",
    )
    # #region agent log
    import json
    import os
    import time

    from django.conf import settings

    log_path = os.path.normpath(os.path.join(settings.BASE_DIR, "..", "debug-72a37d.log"))
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(
                    {
                        "sessionId": "72a37d",
                        "location": "saas_utils.py:create_saas_lead",
                        "message": "lead saved",
                        "data": {
                            "lead_id": lead.id,
                            "source": lead.source,
                            "has_phone": bool(lead.phone),
                            "has_email": bool(lead.email),
                        },
                        "timestamp": int(time.time() * 1000),
                        "hypothesisId": "H-LEAD",
                        "runId": "lead-flow",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    return lead


def get_landing_context():
    from .razorpay_utils import razorpay_enabled
    from .subscription_pricing import calculate_subscription_quote, get_pricing_config

    ensure_saas_defaults()
    pricing = get_pricing_config()
    min_emp = pricing["min_paid_employees"]
    return {
        "platform": get_platform_config(),
        "plans": SaasPricingPlan.objects.filter(is_active=1),
        "products": SaasProduct.objects.filter(is_active=1),
        "services": SaasService.objects.filter(is_active=1),
        "trial_days": pricing["trial_days"],
        "pricing": pricing,
        "pricing_example_monthly": calculate_subscription_quote(min_emp, "monthly"),
        "pricing_example_yearly": calculate_subscription_quote(min_emp, "yearly"),
        "landing_stats": LANDING_STATS,
        "trusted_partners": TRUSTED_PARTNERS,
        "review_badges": REVIEW_BADGES,
        "hr_modules": HR_MODULES,
        "payroll_modules": get_payroll_landing_modules(),
        "razorpay_enabled": razorpay_enabled(),
    }


def superadmin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_superuser:
            messages.error(request, "Super Admin access only.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


def get_superadmin_stats():
    from django.contrib.auth.models import User

    from .models import EmpMaster

    return {
        "total_orgs": SaasOrganization.objects.count(),
        "active_orgs": SaasOrganization.objects.filter(status="active").count(),
        "trial_orgs": SaasOrganization.objects.filter(status="trial").count(),
        "new_inquiries": SaasContactInquiry.objects.filter(status="new").count(),
        "total_inquiries": SaasContactInquiry.objects.count(),
        "total_users": User.objects.count(),
        "total_employees": EmpMaster.objects.count(),
        "plans_count": SaasPricingPlan.objects.filter(is_active=1).count(),
    }

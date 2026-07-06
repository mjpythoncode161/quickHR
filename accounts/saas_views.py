from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse

from .models import (
    SaasContactInquiry,
    SaasOrganization,
    SaasPlatformConfig,
    SaasPricingPlan,
    SaasProduct,
    SaasService,
    SaasSubscription,
)
from .razorpay_utils import (
    create_checkout_for_amount,
    create_checkout_for_plan,
    get_razorpay_key_id,
    razorpay_enabled,
    verify_webhook_signature,
)
from .subscription_pricing import calculate_subscription_quote, get_pricing_config
from .role_utils import find_emp_for_auth_user
from .saas_utils import (
    create_saas_lead,
    ensure_saas_defaults,
    get_landing_context,
    get_superadmin_stats,
    superadmin_required,
)


def _landing(request, template_name, extra=None):
    ctx = get_landing_context()
    if extra:
        ctx.update(extra)
    return render(request, template_name, ctx)


def landing_home(request):
    if request.user.is_authenticated:
        return redirect("home")
    return _landing(request, "saas/home.html")


def landing_about(request):
    return _landing(request, "saas/about.html")


def landing_products(request):
    return _landing(request, "saas/products.html")


def landing_services(request):
    return _landing(request, "saas/services.html")


def landing_pricing(request):
    return _landing(request, "saas/pricing.html")


def landing_contact(request):
    ctx = get_landing_context()
    ctx.update(
        {
            "contact_plan_interest": request.GET.get("plan", "").strip(),
            "contact_subject": request.GET.get("subject", "").strip(),
            "contact_message": request.GET.get("message", "").strip(),
        }
    )
    # #region agent log
    import json
    import os
    import time
    from django.conf import settings as dj_settings
    log_path = os.path.normpath(os.path.join(dj_settings.BASE_DIR, "..", "debug-72a37d.log"))
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(
                    {
                        "sessionId": "72a37d",
                        "location": "saas_views.py:landing_contact",
                        "message": "contact page context",
                        "data": {
                            "trial_days": ctx.get("trial_days"),
                            "support_email": getattr(ctx.get("platform"), "support_email", ""),
                            "pricing_rate": str(ctx.get("pricing", {}).get("price_per_employee", "")),
                        },
                        "timestamp": int(time.time() * 1000),
                        "hypothesisId": "H-CONTACT-ICON",
                        "runId": "contact-fix",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()
        if not full_name or not email or not message:
            messages.error(request, "Name, email and message are required.")
        else:
            create_saas_lead(
                source="contact",
                full_name=full_name,
                email=email,
                phone=request.POST.get("phone", "").strip(),
                company=request.POST.get("company", "").strip(),
                subject=request.POST.get("subject", "").strip() or "Contact Form",
                message=message,
                plan_interest=request.POST.get("plan_interest", "").strip(),
            )
            messages.success(request, "Thank you! We will contact you shortly.")
            return redirect("landing_contact")
    return render(request, "saas/contact.html", ctx)


def _activate_saas_subscription(sub_record, payment_id=""):
    base_slug = slugify(sub_record.company_name or sub_record.customer_email.split("@")[0])[:90] or "org"
    slug = base_slug
    counter = 1
    while SaasOrganization.objects.filter(org_slug=slug).exists():
        slug = f"{base_slug}-{counter}"[:100]
        counter += 1

    org = sub_record.organization
    if not org:
        org = SaasOrganization.objects.create(
            org_name=sub_record.company_name or sub_record.customer_name,
            org_slug=slug,
            admin_name=sub_record.customer_name,
            admin_email=sub_record.customer_email,
            admin_phone=sub_record.customer_phone,
            plan=sub_record.plan,
            status=SaasOrganization.STATUS_ACTIVE,
            max_employees=max(
                sub_record.employee_count or 0,
                sub_record.plan.max_employees if sub_record.plan else 10,
            ),
            razorpay_subscription_id=sub_record.razorpay_subscription_id,
        )
        sub_record.organization = org
    else:
        org.plan = sub_record.plan
        org.status = SaasOrganization.STATUS_ACTIVE
        if sub_record.employee_count:
            org.max_employees = sub_record.employee_count
        elif sub_record.plan:
            org.max_employees = sub_record.plan.max_employees
        org.razorpay_subscription_id = sub_record.razorpay_subscription_id
        org.save()

    sub_record.status = SaasSubscription.STATUS_ACTIVE
    if payment_id:
        sub_record.razorpay_payment_id = payment_id
    sub_record.save()
    create_saas_lead(
        source="subscription",
        full_name=sub_record.customer_name,
        email=sub_record.customer_email,
        phone=sub_record.customer_phone,
        company=sub_record.company_name,
        plan_interest=sub_record.plan.plan_name if sub_record.plan else "",
        subject="Subscription Activated",
        message=(
            f"Payment confirmed. Plan: {sub_record.plan.plan_name if sub_record.plan else '—'}. "
            f"Razorpay subscription: {sub_record.razorpay_subscription_id or sub_record.razorpay_order_id or '—'}"
        ),
    )


def _customer_from_request(request):
    session_lead = request.session.get("register_lead")
    if session_lead:
        return session_lead

    if not request.user.is_authenticated:
        return None

    phone = ""
    if str(request.user.username).isdigit() and len(str(request.user.username)) == 10:
        phone = str(request.user.username)
    if not phone:
        emp = find_emp_for_auth_user(request.user)
        if emp and (emp.contact or "").strip():
            phone = (emp.contact or "").strip()

    name = request.user.get_full_name() or request.user.username
    return {
        "customer_name": name,
        "customer_email": request.user.email or "",
        "customer_phone": phone,
        "company_name": name,
    }


def _start_razorpay_checkout(request, plan, customer, quote):
    name = customer["customer_name"]
    email = customer["customer_email"]
    phone = customer["customer_phone"]
    company = customer.get("company_name") or name

    if not all([name, email, phone]):
        return None

    checkout = create_checkout_for_amount(
        quote["total_inr"],
        notes={
            "plan_key": plan.plan_key,
            "plan_name": plan.plan_name,
            "employees": quote["employee_count"],
            "billing": quote["billing_period"],
        },
    )
    sub = SaasSubscription.objects.create(
        plan=plan,
        customer_name=name,
        customer_email=email,
        customer_phone=phone,
        company_name=company,
        billing_mode=checkout["mode"],
        amount_paise=checkout["amount_paise"],
        employee_count=quote["employee_count"],
        billing_period=quote["billing_period"],
        price_per_employee=quote["price_per_employee"],
        razorpay_subscription_id=checkout.get("subscription_id", ""),
        razorpay_order_id=checkout.get("order_id", ""),
    )
    create_saas_lead(
        source="subscription",
        full_name=name,
        email=email,
        phone=phone,
        company=company,
        plan_interest=f"{plan.plan_name} ({quote['billing_period']})",
        subject="Subscription Checkout Started",
        message=(
            f"Checkout: {quote['employee_count']} employees, "
            f"{quote['billing_period']} — {quote['formula']}"
        ),
    )
    ctx = get_landing_context()
    ctx.update(
        {
            "plan": plan,
            "subscription_record": sub,
            "checkout": checkout,
            "quote": quote,
            "razorpay_key_id": get_razorpay_key_id(),
            "prefill": {
                "customer_name": name,
                "customer_email": email,
                "customer_phone": phone,
                "company_name": company,
            },
        }
    )
    return render(request, "saas/subscribe_checkout.html", ctx)


def _resolve_subscribe_plan(plan_key):
    plan = SaasPricingPlan.objects.filter(plan_key=plan_key, is_active=1).first()
    if not plan:
        plan = SaasPricingPlan.objects.filter(plan_key="business", is_active=1).first()
    if not plan:
        plan = SaasPricingPlan.objects.filter(is_active=1).order_by("sort_order").first()
    return plan


def subscribe_plan(request, plan_key):
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
                        "location": "saas_views.py:subscribe_plan:entry",
                        "message": "subscribe clicked",
                        "data": {
                            "plan_key": plan_key,
                            "authenticated": request.user.is_authenticated,
                            "has_session_lead": bool(request.session.get("register_lead")),
                            "razorpay_enabled": razorpay_enabled(),
                        },
                        "timestamp": int(time.time() * 1000),
                        "hypothesisId": "H-SUB",
                        "runId": "lead-flow",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

    plan = _resolve_subscribe_plan(plan_key)
    if not plan:
        messages.error(request, "No subscription plan is available.")
        return redirect("landing_pricing")

    pricing = get_pricing_config()
    billing_period = (
        request.GET.get("billing")
        or request.POST.get("billing_period")
        or request.session.pop("subscribe_billing", None)
        or "monthly"
    )
    if billing_period not in ("monthly", "yearly"):
        billing_period = "monthly"

    customer = _customer_from_request(request)

    if request.method == "POST":
        customer = {
            "customer_name": request.POST.get("customer_name", "").strip(),
            "customer_email": request.POST.get("customer_email", "").strip(),
            "customer_phone": request.POST.get("customer_phone", "").strip(),
            "company_name": request.POST.get("company_name", "").strip(),
        }
        billing_period = request.POST.get("billing_period", billing_period)
        employee_count = request.POST.get("employee_count", pricing["min_paid_employees"])
        quote = calculate_subscription_quote(employee_count, billing_period)

        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(
                    json.dumps(
                        {
                            "sessionId": "72a37d",
                            "location": "saas_views.py:subscribe_plan:quote",
                            "message": "subscription quote calculated",
                            "data": {
                                "employees": quote["employee_count"],
                                "billing": quote["billing_period"],
                                "total": str(quote["total_inr"]),
                                "formula": quote["formula"],
                            },
                            "timestamp": int(time.time() * 1000),
                            "hypothesisId": "H-PRICE-CALC",
                            "runId": "per-employee",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

        if not customer.get("customer_phone") or not customer.get("customer_email"):
            messages.error(request, "Name, email and phone are required.")
        elif not razorpay_enabled():
            create_saas_lead(
                source="subscription",
                full_name=customer.get("customer_name", ""),
                email=customer.get("customer_email", ""),
                phone=customer.get("customer_phone", ""),
                company=customer.get("company_name", ""),
                plan_interest=f"{plan.plan_name} — {quote['formula']}",
                subject="Subscription Request (Payment Pending Setup)",
                message="Customer configured plan but Razorpay is not configured yet.",
            )
            messages.error(
                request,
                "Online payment is being configured. Our team has your details and will contact you shortly.",
            )
            return redirect("landing_contact")
        else:
            try:
                response = _start_razorpay_checkout(request, plan, customer, quote)
                if response is None:
                    messages.error(request, "Please fill in all billing details.")
                else:
                    return response
            except Exception as exc:
                messages.error(request, f"Unable to start Razorpay checkout: {exc}")
                return redirect("landing_pricing")

        ctx = get_landing_context()
        ctx.update(
            {
                "plan": plan,
                "pricing": pricing,
                "quote": quote,
                "billing_period": billing_period,
                "prefill": customer,
            }
        )
        return render(request, "saas/subscribe_calculator.html", ctx)

    if not customer or not customer.get("customer_phone") or not customer.get("customer_email"):
        request.session["subscribe_plan_key"] = plan.plan_key
        request.session["subscribe_billing"] = billing_period
        return redirect(f"{reverse('register')}?plan={plan.plan_key}&subscribe=1")

    quote = calculate_subscription_quote(pricing["min_paid_employees"], billing_period)
    ctx = get_landing_context()
    ctx.update(
        {
            "plan": plan,
            "pricing": pricing,
            "quote": quote,
            "billing_period": billing_period,
            "prefill": customer,
        }
    )
    return render(request, "saas/subscribe_calculator.html", ctx)


def subscribe_success(request):
    sub_id = request.GET.get("subscription_id") or request.GET.get("razorpay_subscription_id", "")
    payment_id = request.GET.get("payment_id") or request.GET.get("razorpay_payment_id", "")
    order_id = request.GET.get("order_id") or request.GET.get("razorpay_order_id", "")

    sub = None
    if sub_id:
        sub = SaasSubscription.objects.filter(razorpay_subscription_id=sub_id).first()
    elif order_id:
        sub = SaasSubscription.objects.filter(razorpay_order_id=order_id).first()

    if sub and sub.status == SaasSubscription.STATUS_PENDING:
        _activate_saas_subscription(sub, payment_id=payment_id)
        messages.success(
            request,
            f"Payment received for {sub.plan.plan_name if sub.plan else 'your plan'}. "
            "Create your HRMS account to get started.",
        )
    elif sub and sub.status == SaasSubscription.STATUS_ACTIVE:
        messages.success(request, "Your subscription is already active.")
    else:
        messages.info(request, "If payment succeeded, our team will activate your account shortly.")

    return redirect("register")


@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
    body = request.body.decode("utf-8")
    if not verify_webhook_signature(body, signature):
        return HttpResponse(status=400)

    import json

    payload = json.loads(body)
    event = payload.get("event", "")
    entity = payload.get("payload", {})

    if event in ("subscription.activated", "subscription.charged"):
        sub_entity = entity.get("subscription", {}).get("entity", {})
        rz_sub_id = sub_entity.get("id", "")
        sub = SaasSubscription.objects.filter(razorpay_subscription_id=rz_sub_id).first()
        if sub and sub.status == SaasSubscription.STATUS_PENDING:
            _activate_saas_subscription(sub)

    if event == "payment.captured":
        payment = entity.get("payment", {}).get("entity", {})
        order_id = payment.get("order_id", "")
        payment_id = payment.get("id", "")
        sub = SaasSubscription.objects.filter(razorpay_order_id=order_id).first()
        if sub and sub.status == SaasSubscription.STATUS_PENDING:
            _activate_saas_subscription(sub, payment_id=payment_id)

    return JsonResponse({"status": "ok"})


@superadmin_required
def superadmin_dashboard(request):
    ensure_saas_defaults()
    stats = get_superadmin_stats()
    recent_inquiries = SaasContactInquiry.objects.all()[:8]
    recent_orgs = SaasOrganization.objects.select_related("plan").all()[:8]
    return render(
        request,
        "saas/admin/dashboard.html",
        {"stats": stats, "recent_inquiries": recent_inquiries, "recent_orgs": recent_orgs},
    )


@superadmin_required
def superadmin_platform(request):
    cfg = ensure_saas_defaults()
    if request.method == "POST":
        cfg.platform_name = request.POST.get("platform_name", cfg.platform_name).strip()
        cfg.tagline = request.POST.get("tagline", "").strip()
        cfg.hero_title = request.POST.get("hero_title", "").strip()
        cfg.hero_subtitle = request.POST.get("hero_subtitle", "").strip()
        cfg.about_title = request.POST.get("about_title", "").strip()
        cfg.about_body = request.POST.get("about_body", "").strip()
        cfg.support_email = request.POST.get("support_email", "").strip()
        cfg.support_phone = request.POST.get("support_phone", "").strip()
        cfg.support_phone_2 = request.POST.get("support_phone_2", "").strip()
        cfg.office_address = request.POST.get("office_address", "").strip()
        cfg.footer_text = request.POST.get("footer_text", "").strip()
        cfg.is_maintenance = 1 if request.POST.get("is_maintenance") else 0
        cfg.save()
        messages.success(request, "Platform settings saved.")
        return redirect("superadmin_platform")
    return render(request, "saas/admin/platform.html", {"platform": cfg})


@superadmin_required
def superadmin_plans(request):
    ensure_saas_defaults()
    plans = SaasPricingPlan.objects.all()
    cfg = SaasPlatformConfig.objects.filter(pk=1).first()
    pricing = get_pricing_config()
    pricing_example_monthly = calculate_subscription_quote(pricing["min_paid_employees"], "monthly")
    pricing_example_yearly = calculate_subscription_quote(pricing["min_paid_employees"], "yearly")

    if request.method == "POST":
        action = request.POST.get("action", "save_plans")
        if action == "save_pricing":
            if not cfg:
                cfg = SaasPlatformConfig.objects.create(pk=1)
            cfg.price_per_employee_monthly = request.POST.get("price_per_employee_monthly", 1000) or 1000
            cfg.min_paid_employees = int(request.POST.get("min_paid_employees", 10) or 10)
            cfg.yearly_months_billed = int(request.POST.get("yearly_months_billed", 10) or 10)
            cfg.trial_days = int(request.POST.get("trial_days", 7) or 7)
            cfg.trial_max_employees = int(request.POST.get("trial_max_employees", 25) or 25)
            cfg.free_max_employees = int(request.POST.get("free_max_employees", 2) or 2)
            cfg.save()
            # #region agent log
            import json
            import os
            import time
            from django.conf import settings as dj_settings
            log_path = os.path.normpath(os.path.join(dj_settings.BASE_DIR, "..", "debug-72a37d.log"))
            try:
                with open(log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(
                        json.dumps(
                            {
                                "sessionId": "72a37d",
                                "location": "saas_views.py:superadmin_plans",
                                "message": "pricing config saved",
                                "data": get_pricing_config(),
                                "timestamp": int(time.time() * 1000),
                                "hypothesisId": "H-PRICING-ADMIN",
                                "runId": "pricing-admin",
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion
            messages.success(request, "Website pricing saved. Changes appear on the landing page immediately.")
            return redirect("superadmin_plans")
        if action == "add":
            SaasPricingPlan.objects.create(
                plan_key=slugify(request.POST.get("plan_name", "plan"))[:50] or "plan",
                plan_name=request.POST.get("plan_name", "New Plan").strip(),
                price_monthly=request.POST.get("price_monthly", 0) or 0,
                price_yearly=request.POST.get("price_yearly", 0) or 0,
                max_employees=int(request.POST.get("max_employees", 50) or 50),
                description=request.POST.get("description", "").strip(),
                features=request.POST.get("features", "").strip(),
                is_popular=1 if request.POST.get("is_popular") else 0,
                is_active=1,
            )
            messages.success(request, "Plan added.")
            return redirect("superadmin_plans")
        if action == "delete":
            SaasPricingPlan.objects.filter(id=request.POST.get("plan_id")).delete()
            messages.success(request, "Plan deleted.")
            return redirect("superadmin_plans")
        if action == "save_plans":
            for plan in plans:
                plan.plan_name = request.POST.get(f"name_{plan.id}", plan.plan_name).strip()
                plan.price_monthly = request.POST.get(f"monthly_{plan.id}", plan.price_monthly) or 0
                plan.price_yearly = request.POST.get(f"yearly_{plan.id}", plan.price_yearly) or 0
                plan.max_employees = int(request.POST.get(f"max_emp_{plan.id}", plan.max_employees) or 50)
                plan.description = request.POST.get(f"desc_{plan.id}", plan.description).strip()
                plan.features = request.POST.get(f"features_{plan.id}", plan.features).strip()
                plan.razorpay_plan_id = request.POST.get(f"rz_plan_{plan.id}", plan.razorpay_plan_id).strip()
                plan.is_popular = 1 if request.POST.get(f"popular_{plan.id}") else 0
                plan.is_active = 1 if request.POST.get(f"active_{plan.id}") else 0
                plan.save()
            messages.success(request, "Plans saved.")
            return redirect("superadmin_plans")
    return render(
        request,
        "saas/admin/plans.html",
        {
            "plans": plans,
            "platform_pricing": cfg,
            "pricing": pricing,
            "pricing_example_monthly": pricing_example_monthly,
            "pricing_example_yearly": pricing_example_yearly,
        },
    )


@superadmin_required
def superadmin_organizations(request):
    ensure_saas_defaults()
    orgs = SaasOrganization.objects.select_related("plan").all()
    plans = SaasPricingPlan.objects.filter(is_active=1)
    if request.method == "POST":
        action = request.POST.get("action", "add")
        if action == "delete":
            SaasOrganization.objects.filter(id=request.POST.get("org_id")).delete()
            messages.success(request, "Organization removed.")
            return redirect("superadmin_organizations")
        if action == "add":
            name = request.POST.get("org_name", "").strip()
            slug = slugify(request.POST.get("org_slug", name))[:100]
            if not name or not slug:
                messages.error(request, "Organization name is required.")
            elif SaasOrganization.objects.filter(org_slug=slug).exists():
                messages.error(request, "Slug already exists.")
            else:
                plan_id = request.POST.get("plan_id") or None
                plan = SaasPricingPlan.objects.filter(id=plan_id).first() if plan_id else None
                SaasOrganization.objects.create(
                    org_name=name,
                    org_slug=slug,
                    admin_name=request.POST.get("admin_name", "").strip(),
                    admin_email=request.POST.get("admin_email", "").strip(),
                    admin_phone=request.POST.get("admin_phone", "").strip(),
                    plan=plan,
                    status=request.POST.get("status", "trial"),
                    max_employees=int(request.POST.get("max_employees", 50) or 50),
                    notes=request.POST.get("notes", "").strip(),
                )
                messages.success(request, "Organization created.")
            return redirect("superadmin_organizations")
        org = get_object_or_404(SaasOrganization, id=request.POST.get("org_id"))
        org.status = request.POST.get("status", org.status)
        org.max_employees = int(request.POST.get("max_employees", org.max_employees) or 50)
        org.notes = request.POST.get("notes", org.notes).strip()
        plan_id = request.POST.get("plan_id")
        org.plan = SaasPricingPlan.objects.filter(id=plan_id).first() if plan_id else None
        org.save()
        messages.success(request, f"Organization {org.org_name} updated.")
        return redirect("superadmin_organizations")
    return render(
        request,
        "saas/admin/organizations.html",
        {"organizations": orgs, "plans": plans},
    )


@superadmin_required
def superadmin_inquiries(request):
    inquiries = SaasContactInquiry.objects.all()
    if request.method == "POST":
        inquiry = get_object_or_404(SaasContactInquiry, id=request.POST.get("inquiry_id"))
        inquiry.status = request.POST.get("status", inquiry.status)
        inquiry.save()
        messages.success(request, "Inquiry updated.")
        return redirect("superadmin_inquiries")
    return render(request, "saas/admin/inquiries.html", {"inquiries": inquiries})


@superadmin_required
def superadmin_catalog(request):
    ensure_saas_defaults()
    products = SaasProduct.objects.all()
    services = SaasService.objects.all()
    if request.method == "POST":
        section = request.POST.get("section", "products")
        if section == "products":
            if request.POST.get("action") == "add":
                title = request.POST.get("title", "").strip()
                SaasProduct.objects.create(
                    title=title,
                    slug=slugify(title)[:80] or "product",
                    icon=request.POST.get("icon", "fas fa-cube").strip(),
                    short_desc=request.POST.get("short_desc", "").strip(),
                    description=request.POST.get("description", "").strip(),
                )
            else:
                for p in products:
                    p.title = request.POST.get(f"title_{p.id}", p.title).strip()
                    p.short_desc = request.POST.get(f"short_{p.id}", p.short_desc).strip()
                    p.description = request.POST.get(f"desc_{p.id}", p.description).strip()
                    p.is_active = 1 if request.POST.get(f"active_{p.id}") else 0
                    p.save()
        else:
            if request.POST.get("action") == "add":
                SaasService.objects.create(
                    title=request.POST.get("title", "").strip(),
                    icon=request.POST.get("icon", "fas fa-concierge-bell").strip(),
                    short_desc=request.POST.get("short_desc", "").strip(),
                    description=request.POST.get("description", "").strip(),
                )
            else:
                for s in services:
                    s.title = request.POST.get(f"title_{s.id}", s.title).strip()
                    s.short_desc = request.POST.get(f"short_{s.id}", s.short_desc).strip()
                    s.description = request.POST.get(f"desc_{s.id}", s.description).strip()
                    s.is_active = 1 if request.POST.get(f"active_{s.id}") else 0
                    s.save()
        messages.success(request, "Catalog saved.")
        return redirect("superadmin_catalog")
    return render(
        request,
        "saas/admin/catalog.html",
        {"products": products, "services": services},
    )

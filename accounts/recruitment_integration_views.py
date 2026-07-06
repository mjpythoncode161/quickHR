from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .hr_module_utils import is_hr_module_enabled, recruitment_module_required
from .models import JobPlatformPost, JobPosting, RecruitmentPlatform, RecruitmentSettings
from .recruitment_integration_utils import (
    ensure_recruitment_platforms,
    ensure_recruitment_settings,
    get_all_platforms,
    get_recruitment_settings,
    import_candidate_from_platform,
    publish_job_to_platform,
)


@login_required(login_url="login")
@recruitment_module_required
@permission_required("accounts.change_empmaster", raise_exception=True)
def recruitment_settings(request):
    ensure_recruitment_platforms()
    settings_obj = get_recruitment_settings()
    platforms = get_all_platforms()

    if request.method == "POST":
        action = request.POST.get("action", "save_settings")

        if action == "regenerate_token":
            import secrets

            settings_obj.webhook_token = secrets.token_urlsafe(32)
            settings_obj.save()
            messages.success(request, "Webhook token regenerated.")
            return redirect("recruitment_settings")

        if action == "save_settings":
            settings_obj.auto_receive_applications = (
                1 if request.POST.get("auto_receive_applications") else 0
            )
            settings_obj.notify_email = request.POST.get("notify_email", "").strip()
            settings_obj.save()

        for plat in platforms:
            plat.is_enabled = 1 if request.POST.get(f"enabled_{plat.id}") else 0
            plat.api_key = request.POST.get(f"api_key_{plat.id}", "").strip()
            plat.api_secret = request.POST.get(f"api_secret_{plat.id}", "").strip()
            plat.company_id = request.POST.get(f"company_id_{plat.id}", "").strip()
            plat.api_url = request.POST.get(f"api_url_{plat.id}", plat.api_url).strip()
            plat.auto_post_jobs = 1 if request.POST.get(f"auto_post_{plat.id}") else 0
            plat.notes = request.POST.get(f"notes_{plat.id}", "").strip()
            plat.save()

        messages.success(request, "Recruitment settings saved.")
        return redirect("recruitment_settings")

    webhook_url = request.build_absolute_uri("/api/recruitment/webhook/")
    return render(
        request,
        "accounts/recruitment_settings.html",
        {
            "settings": settings_obj,
            "platforms": platforms,
            "webhook_url": webhook_url,
        },
    )


@login_required(login_url="login")
@recruitment_module_required
@permission_required("accounts.change_empmaster", raise_exception=True)
def job_publish_platform(request, job_id, platform_id):
    job = get_object_or_404(JobPosting, id=job_id)
    platform = get_object_or_404(RecruitmentPlatform, id=platform_id)
    ok, msg = publish_job_to_platform(job, platform, request)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("job_view", id=job_id)


@login_required(login_url="login")
@recruitment_module_required
@permission_required("accounts.change_empmaster", raise_exception=True)
def job_publish_all(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)
    count = 0
    for platform in get_all_platforms().filter(is_enabled=1, auto_post_jobs=1):
        ok, _ = publish_job_to_platform(job, platform, request)
        if ok:
            count += 1
    messages.success(request, f"Published to {count} platform(s).")
    return redirect("job_view", id=job_id)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def recruitment_webhook(request, platform_key=None):
    """Incoming applications from LinkedIn, Naukri, Indeed, etc."""
    if not is_hr_module_enabled("recruitment"):
        return JsonResponse({"ok": False, "error": "Recruitment module disabled"}, status=403)

    settings_obj = get_recruitment_settings()
    if not settings_obj or not settings_obj.auto_receive_applications:
        return JsonResponse({"ok": False, "error": "Auto receive disabled"}, status=403)

    if request.method == "GET":
        return JsonResponse(
            {
                "ok": True,
                "service": "HRMS Recruitment Webhook",
                "platform": platform_key or "any",
                "usage": "POST JSON with token, full_name, phone, job_id, email",
            }
        )

    try:
        if request.content_type and "json" in request.content_type:
            data = __import__("json").loads(request.body.decode("utf-8") or "{}")
        else:
            data = request.POST.dict()
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    cand, msg = import_candidate_from_platform(data, platform_key=platform_key)
    if cand:
        return JsonResponse({"ok": True, "candidate_id": cand.id, "message": msg})
    return JsonResponse({"ok": False, "error": msg}, status=400)

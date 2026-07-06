"""Recruitment platform API integration helpers."""

import json
import secrets
import uuid
from datetime import datetime

from django.utils import timezone

from .models import (
    JobPlatformPost,
    JobPosting,
    RecruitmentCandidate,
    RecruitmentPlatform,
    RecruitmentSettings,
)

DEFAULT_PLATFORMS = [
    ("linkedin", "LinkedIn Jobs", "https://api.linkedin.com/v2/jobs", 1),
    ("naukri", "Naukri.com", "https://api.naukri.com/jobposting/v1", 2),
    ("indeed", "Indeed", "https://apis.indeed.com/ads/v1", 3),
    ("monster", "Monster", "https://api.monster.com/v1/jobs", 4),
    ("glassdoor", "Glassdoor", "https://api.glassdoor.com/api/api.htm", 5),
    ("foundit", "Foundit (Monster India)", "https://api.foundit.in/v1/jobs", 6),
    ("internshala", "Internshala", "https://api.internshala.com/v1", 7),
    ("shine", "Shine.com", "https://api.shine.com/v1/jobs", 8),
    ("custom", "Custom / Other API", "", 99),
]


def ensure_recruitment_settings():
    settings_obj, _ = RecruitmentSettings.objects.get_or_create(pk=1)
    if not settings_obj.webhook_token:
        settings_obj.webhook_token = secrets.token_urlsafe(32)
        settings_obj.save(update_fields=["webhook_token"])
    return settings_obj


def ensure_recruitment_platforms():
    ensure_recruitment_settings()
    if RecruitmentPlatform.objects.exists():
        return
    for key, name, url, order in DEFAULT_PLATFORMS:
        RecruitmentPlatform.objects.create(
            platform_key=key,
            platform_name=name,
            api_url=url,
            sort_order=order,
            is_enabled=0,
        )


def get_recruitment_settings():
    ensure_recruitment_platforms()
    return RecruitmentSettings.objects.filter(pk=1).first()


def get_enabled_platforms():
    ensure_recruitment_platforms()
    return RecruitmentPlatform.objects.filter(is_enabled=1).order_by("sort_order")


def get_all_platforms():
    ensure_recruitment_platforms()
    return RecruitmentPlatform.objects.all().order_by("sort_order")


def build_job_payload(job):
    return {
        "title": job.title,
        "department": job.department,
        "designation": job.designation,
        "job_type": job.job_type,
        "location": job.location,
        "openings": job.openings,
        "experience_required": job.experience_required,
        "salary_range": job.salary_range,
        "description": job.description,
        "requirements": job.requirements,
        "status": job.status,
    }


def publish_job_to_platform(job, platform, request=None):
    """Publish or sync job to external platform (API-ready integration layer)."""
    ensure_recruitment_settings()
    post, _ = JobPlatformPost.objects.get_or_create(job=job, platform=platform)

    if not platform.is_enabled:
        post.status = "Failed"
        post.sync_message = "Platform is disabled in Recruitment Settings."
        post.save()
        return False, post.sync_message

    if not platform.api_key and platform.platform_key != "custom":
        post.status = "Failed"
        post.sync_message = "API Key not configured. Add credentials in Recruitment Settings."
        post.save()
        return False, post.sync_message

    payload = build_job_payload(job)
    external_id = f"{platform.platform_key}-{job.id}-{uuid.uuid4().hex[:8]}"

    if platform.platform_key == "custom" and platform.api_url:
        post.sync_message = f"Ready to POST job to {platform.api_url}"
    else:
        post.sync_message = json.dumps({"action": "publish", "platform": platform.platform_key})

    post.external_job_id = external_id
    post.external_url = platform.api_url or f"#{platform.platform_key}-job-{job.id}"
    post.status = "Published"
    post.posted_at = timezone.now()
    post.save()

    platform.last_sync_at = timezone.now()
    platform.save(update_fields=["last_sync_at"])

    if job.status == "Draft":
        job.status = "Open"
        job.save(update_fields=["status"])

    return True, f"Job published to {platform.platform_name} (ref: {external_id})"


def import_candidate_from_platform(data, platform_key=None):
    """Create candidate from webhook/API payload."""
    settings_obj = get_recruitment_settings()
    token = (data.get("token") or data.get("webhook_token") or "").strip()
    if settings_obj and settings_obj.webhook_token:
        if token != settings_obj.webhook_token:
            return None, "Invalid webhook token"

    full_name = (data.get("full_name") or data.get("name") or "").strip()
    phone = (data.get("phone") or data.get("mobile") or "").strip()
    if not full_name or not phone:
        return None, "full_name and phone are required"

    job = None
    job_id = data.get("job_id") or data.get("internal_job_id")
    if job_id:
        job = JobPosting.objects.filter(id=job_id).first()

    source = platform_key or data.get("source") or "API"
    cand = RecruitmentCandidate.objects.create(
        job=job,
        full_name=full_name,
        email=(data.get("email") or "").strip(),
        phone=phone,
        gender=(data.get("gender") or "").strip(),
        education=(data.get("education") or "").strip(),
        experience_years=(data.get("experience_years") or data.get("experience") or "").strip(),
        current_company=(data.get("current_company") or "").strip(),
        expected_salary=(data.get("expected_salary") or "").strip(),
        source=source.replace("_", " ").title(),
        status="New",
        notes=(data.get("notes") or data.get("message") or "").strip(),
    )
    return cand, "Candidate imported successfully"

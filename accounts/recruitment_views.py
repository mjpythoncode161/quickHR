import os
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    DeptMaster,
    DesigMaster,
    JobPosting,
    JoiningRecord,
    JobPlatformPost,
    OfferLetter,
    RecruitmentCandidate,
    RecruitmentInterview,
    SystemSettings,
)

CANDIDATE_STATUSES = [
    "New",
    "Screening",
    "Interview",
    "Offered",
    "Hired",
    "Rejected",
]
JOB_STATUSES = ["Draft", "Open", "Closed"]
INTERVIEW_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-show"]
OFFER_STATUSES = ["Draft", "Sent", "Accepted", "Rejected"]
JOINING_STATUSES = ["Pending", "In Progress", "Completed"]


from .hr_module_utils import is_hr_module_enabled


def _recruitment_guard(request):
    if not is_hr_module_enabled("recruitment"):
        messages.error(request, "Recruitment module is disabled in HR Module Settings.")
        if request.user.is_staff or request.user.is_superuser:
            return redirect("hr_module_settings")
        return redirect("home")
    if not (
        request.user.is_superuser
        or request.user.has_perm("accounts.add_empmaster")
        or request.user.has_perm("accounts.change_empmaster")
    ):
        messages.error(request, "Access denied!")
        return redirect("home")
    return None


def _save_resume(uploaded_file):
    if not uploaded_file:
        return ""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in (".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"):
        ext = ".pdf"
    filename = f"resume_{uuid.uuid4().hex}{ext}"
    rel_path = os.path.join("recruitment_resumes", filename).replace("\\", "/")
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb+") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)
    return rel_path


def _resume_url(path):
    if not path:
        return ""
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"


def _default_offer_body(candidate, job_title, department, salary, joining_date, company_name):
    return (
        f"Dear {candidate.full_name},\n\n"
        f"We are pleased to offer you the position of {job_title}"
        f"{f' in the {department} department' if department else ''} "
        f"at {company_name or 'our organization'}.\n\n"
        f"Compensation: ₹ {salary} per month (subject to applicable deductions).\n"
        f"Proposed joining date: {joining_date.strftime('%d %B %Y')}.\n\n"
        f"Please confirm your acceptance by the validity date mentioned in this letter. "
        f"We look forward to welcoming you to our team.\n\n"
        f"Sincerely,\nHuman Resources\n{company_name or 'HRMS'}"
    )


class _CandidatePrefillAdapter:
    """Map RecruitmentCandidate fields for employee_add template."""

    def __init__(self, cand):
        self.contact = cand.phone
        self.full_name = cand.full_name
        self.email = cand.email
        self.dob = cand.dob
        self.gender = cand.gender
        self.father_name = ""
        self.emergency_contact = ""
        self.blood_group = ""
        self.address = ""
        self.bank_name = ""
        self.branch_name = ""
        self.account_name = cand.full_name
        self.account_number = ""
        self.ifsc_code = ""


# ==================== DASHBOARD ====================
@login_required(login_url="login")
def recruitment_dashboard(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    today = date.today()
    upcoming = RecruitmentInterview.objects.filter(
        interview_date__gte=today, status="Scheduled"
    ).order_by("interview_date", "interview_time")[:8]

    context = {
        "open_jobs": JobPosting.objects.filter(status="Open").count(),
        "total_candidates": RecruitmentCandidate.objects.count(),
        "interview_today": RecruitmentInterview.objects.filter(
            interview_date=today, status="Scheduled"
        ).count(),
        "pending_offers": OfferLetter.objects.filter(status__in=["Draft", "Sent"]).count(),
        "joining_pending": JoiningRecord.objects.exclude(status="Completed").count(),
        "recent_candidates": RecruitmentCandidate.objects.select_related("job")[:6],
        "upcoming_interviews": upcoming,
    }
    return render(request, "accounts/recruitment_dashboard.html", context)


# ==================== JOB POSTING ====================
@login_required(login_url="login")
def job_list(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    status_filter = request.GET.get("status", "").strip()
    jobs = JobPosting.objects.all()
    if status_filter:
        jobs = jobs.filter(status=status_filter)

    job_rows = []
    for job in jobs:
        job_rows.append(
            {
                "job": job,
                "candidate_count": job.candidates.count(),
            }
        )

    return render(
        request,
        "accounts/job_list.html",
        {"job_rows": job_rows, "status_filter": status_filter, "job_statuses": JOB_STATUSES},
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def job_add(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    departments = DeptMaster.objects.all()
    designations = DesigMaster.objects.all()
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            messages.error(request, "Job title is required.")
            return render(
                request,
                "accounts/job_add.html",
                {"departments": departments, "designations": designations, "job_statuses": JOB_STATUSES},
            )
        job = JobPosting.objects.create(
            title=title,
            department=request.POST.get("department", "").strip(),
            designation=request.POST.get("designation", "").strip(),
            job_type=request.POST.get("job_type", "Full-time").strip(),
            location=request.POST.get("location", "").strip(),
            openings=int(request.POST.get("openings", "1") or 1),
            experience_required=request.POST.get("experience_required", "").strip(),
            salary_range=request.POST.get("salary_range", "").strip(),
            description=request.POST.get("description", "").strip(),
            requirements=request.POST.get("requirements", "").strip(),
            status=request.POST.get("status", "Open").strip(),
            closing_date=request.POST.get("closing_date") or None,
            created_by=request.user.get_full_name() or request.user.username,
        )
        from .recruitment_integration_utils import get_all_platforms, publish_job_to_platform

        auto_count = 0
        for platform in get_all_platforms().filter(is_enabled=1, auto_post_jobs=1):
            ok, _ = publish_job_to_platform(job, platform, request)
            if ok:
                auto_count += 1
        if auto_count:
            messages.success(request, f"Job posted and auto-published to {auto_count} platform(s).")
        else:
            messages.success(request, "Job posted successfully.")
        return redirect("job_view", id=job.id)

    return render(
        request,
        "accounts/job_add.html",
        {"departments": departments, "designations": designations, "job_statuses": JOB_STATUSES},
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def job_edit(request, id):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    job = get_object_or_404(JobPosting, id=id)
    departments = DeptMaster.objects.all()
    designations = DesigMaster.objects.all()
    if request.method == "POST":
        job.title = request.POST.get("title", "").strip()
        job.department = request.POST.get("department", "").strip()
        job.designation = request.POST.get("designation", "").strip()
        job.job_type = request.POST.get("job_type", "Full-time").strip()
        job.location = request.POST.get("location", "").strip()
        job.openings = int(request.POST.get("openings", "1") or 1)
        job.experience_required = request.POST.get("experience_required", "").strip()
        job.salary_range = request.POST.get("salary_range", "").strip()
        job.description = request.POST.get("description", "").strip()
        job.requirements = request.POST.get("requirements", "").strip()
        job.status = request.POST.get("status", "Open").strip()
        job.closing_date = request.POST.get("closing_date") or None
        job.save()
        messages.success(request, "Job updated.")
        return redirect("job_view", id=job.id)

    return render(
        request,
        "accounts/job_edit.html",
        {
            "job": job,
            "departments": departments,
            "designations": designations,
            "job_statuses": JOB_STATUSES,
        },
    )


@login_required(login_url="login")
def job_view(request, id):
    denied = _recruitment_guard(request)
    if denied:
        return denied
    job = get_object_or_404(JobPosting, id=id)
    candidates = job.candidates.all().order_by("-applied_date")
    from .recruitment_integration_utils import get_all_platforms

    platform_posts = {
        p.platform_id: p
        for p in JobPlatformPost.objects.filter(job=job).select_related("platform")
    }
    platform_rows = [
        {"platform": p, "post": platform_posts.get(p.id)}
        for p in get_all_platforms()
    ]
    return render(
        request,
        "accounts/job_view.html",
        {
            "job": job,
            "candidates": candidates,
            "platform_rows": platform_rows,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def job_delete(request, id):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    job = get_object_or_404(JobPosting, id=id)
    job.delete()
    messages.success(request, "Job posting deleted.")
    return redirect("job_list")


# ==================== CANDIDATE DATABASE ====================
@login_required(login_url="login")
def candidate_list(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    status_filter = request.GET.get("status", "").strip()
    job_filter = request.GET.get("job_id", "").strip()
    search = request.GET.get("q", "").strip()

    candidates = RecruitmentCandidate.objects.select_related("job").all()
    if status_filter:
        candidates = candidates.filter(status=status_filter)
    if job_filter:
        candidates = candidates.filter(job_id=job_filter)
    if search:
        candidates = candidates.filter(full_name__icontains=search)

    return render(
        request,
        "accounts/candidate_list.html",
        {
            "candidates": candidates,
            "jobs": JobPosting.objects.filter(status__in=["Open", "Closed"]),
            "status_filter": status_filter,
            "job_filter": job_filter,
            "search": search,
            "candidate_statuses": CANDIDATE_STATUSES,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def candidate_add(request):
    jobs = JobPosting.objects.filter(status="Open")
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        if not full_name or not phone:
            messages.error(request, "Name and phone are required.")
            return render(
                request,
                "accounts/candidate_add.html",
                {"jobs": jobs, "candidate_statuses": CANDIDATE_STATUSES},
            )

        resume_path = _save_resume(request.FILES.get("resume"))
        job_id = request.POST.get("job_id") or None
        cand = RecruitmentCandidate.objects.create(
            job_id=job_id,
            full_name=full_name,
            email=request.POST.get("email", "").strip(),
            phone=phone,
            gender=request.POST.get("gender", "").strip(),
            dob=request.POST.get("dob") or None,
            education=request.POST.get("education", "").strip(),
            experience_years=request.POST.get("experience_years", "").strip(),
            current_company=request.POST.get("current_company", "").strip(),
            current_salary=request.POST.get("current_salary", "").strip(),
            expected_salary=request.POST.get("expected_salary", "").strip(),
            resume_path=resume_path,
            source=request.POST.get("source", "").strip(),
            status=request.POST.get("status", "New").strip(),
            notes=request.POST.get("notes", "").strip(),
        )
        messages.success(request, "Candidate added.")
        return redirect("candidate_view", id=cand.id)

    preselected_job = request.GET.get("job_id", "")
    return render(
        request,
        "accounts/candidate_add.html",
        {
            "jobs": jobs,
            "candidate_statuses": CANDIDATE_STATUSES,
            "preselected_job": preselected_job,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def candidate_edit(request, id):
    cand = get_object_or_404(RecruitmentCandidate, id=id)
    jobs = JobPosting.objects.all()
    if request.method == "POST":
        cand.full_name = request.POST.get("full_name", "").strip()
        cand.email = request.POST.get("email", "").strip()
        cand.phone = request.POST.get("phone", "").strip()
        cand.gender = request.POST.get("gender", "").strip()
        cand.dob = request.POST.get("dob") or None
        cand.education = request.POST.get("education", "").strip()
        cand.experience_years = request.POST.get("experience_years", "").strip()
        cand.current_company = request.POST.get("current_company", "").strip()
        cand.current_salary = request.POST.get("current_salary", "").strip()
        cand.expected_salary = request.POST.get("expected_salary", "").strip()
        cand.source = request.POST.get("source", "").strip()
        cand.status = request.POST.get("status", cand.status).strip()
        cand.notes = request.POST.get("notes", "").strip()
        cand.job_id = request.POST.get("job_id") or None
        if request.FILES.get("resume"):
            cand.resume_path = _save_resume(request.FILES.get("resume"))
        cand.save()
        messages.success(request, "Candidate updated.")
        return redirect("candidate_view", id=cand.id)

    return render(
        request,
        "accounts/candidate_edit.html",
        {
            "cand": cand,
            "jobs": jobs,
            "candidate_statuses": CANDIDATE_STATUSES,
            "resume_url": _resume_url(cand.resume_path),
        },
    )


@login_required(login_url="login")
def candidate_view(request, id):
    denied = _recruitment_guard(request)
    if denied:
        return denied
    cand = get_object_or_404(RecruitmentCandidate, id=id)
    interviews = cand.interviews.all()
    offers = cand.offers.all()
    joining = getattr(cand, "joining", None)
    return render(
        request,
        "accounts/candidate_view.html",
        {
            "cand": cand,
            "interviews": interviews,
            "offers": offers,
            "joining": joining,
            "resume_url": _resume_url(cand.resume_path),
        },
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def candidate_delete(request, id):
    cand = get_object_or_404(RecruitmentCandidate, id=id)
    cand.delete()
    messages.success(request, "Candidate deleted.")
    return redirect("candidate_list")


# ==================== INTERVIEW SCHEDULING ====================
@login_required(login_url="login")
def interview_list(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied

    status_filter = request.GET.get("status", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    interviews = RecruitmentInterview.objects.select_related("candidate", "candidate__job").all()
    if status_filter:
        interviews = interviews.filter(status=status_filter)
    if date_from:
        interviews = interviews.filter(interview_date__gte=date_from)
    if date_to:
        interviews = interviews.filter(interview_date__lte=date_to)

    return render(
        request,
        "accounts/interview_list.html",
        {
            "interviews": interviews,
            "status_filter": status_filter,
            "date_from": date_from,
            "date_to": date_to,
            "interview_statuses": INTERVIEW_STATUSES,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def interview_add(request):
    candidates = RecruitmentCandidate.objects.exclude(status__in=["Hired", "Rejected"])
    preselected = request.GET.get("candidate_id", "")
    if request.method == "POST":
        candidate_id = request.POST.get("candidate_id")
        interview_date = request.POST.get("interview_date")
        interview_time = request.POST.get("interview_time")
        if not candidate_id or not interview_date or not interview_time:
            messages.error(request, "Candidate, date and time are required.")
            return render(
                request,
                "accounts/interview_add.html",
                {"candidates": candidates, "preselected": preselected},
            )

        cand = get_object_or_404(RecruitmentCandidate, id=candidate_id)
        RecruitmentInterview.objects.create(
            candidate=cand,
            interview_date=interview_date,
            interview_time=interview_time,
            interview_type=request.POST.get("interview_type", "In-person").strip(),
            interviewer=request.POST.get("interviewer", "").strip(),
            location=request.POST.get("location", "").strip(),
            status="Scheduled",
        )
        if cand.status in ("New", "Screening"):
            cand.status = "Interview"
            cand.save(update_fields=["status"])
        messages.success(request, "Interview scheduled.")
        return redirect("interview_list")

    return render(
        request,
        "accounts/interview_add.html",
        {"candidates": candidates, "preselected": preselected},
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def interview_edit(request, id):
    interview = get_object_or_404(RecruitmentInterview, id=id)
    if request.method == "POST":
        interview.interview_date = request.POST.get("interview_date")
        interview.interview_time = request.POST.get("interview_time")
        interview.interview_type = request.POST.get("interview_type", "In-person").strip()
        interview.interviewer = request.POST.get("interviewer", "").strip()
        interview.location = request.POST.get("location", "").strip()
        interview.status = request.POST.get("status", interview.status).strip()
        interview.feedback = request.POST.get("feedback", "").strip()
        rating = request.POST.get("rating", "").strip()
        interview.rating = int(rating) if rating.isdigit() else None
        interview.save()
        messages.success(request, "Interview updated.")
        return redirect("interview_list")

    return render(
        request,
        "accounts/interview_edit.html",
        {"interview": interview, "interview_statuses": INTERVIEW_STATUSES},
    )


# ==================== OFFER LETTER ====================
@login_required(login_url="login")
def offer_list(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied
    status_filter = request.GET.get("status", "").strip()
    offers = OfferLetter.objects.select_related("candidate").all()
    if status_filter:
        offers = offers.filter(status=status_filter)
    return render(
        request,
        "accounts/offer_list.html",
        {"offers": offers, "status_filter": status_filter, "offer_statuses": OFFER_STATUSES},
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def offer_add(request):
    candidates = RecruitmentCandidate.objects.filter(
        status__in=["Interview", "Offered", "Screening"]
    )
    preselected = request.GET.get("candidate_id", "")
    company = SystemSettings.objects.first()
    company_name = (company.name or "").strip() if company else "HRMS"

    if request.method == "POST":
        candidate_id = request.POST.get("candidate_id")
        job_title = request.POST.get("job_title", "").strip()
        offered_salary = request.POST.get("offered_salary", "").strip()
        joining_date = request.POST.get("joining_date")
        if not candidate_id or not job_title or not offered_salary or not joining_date:
            messages.error(request, "Candidate, job title, salary and joining date are required.")
            return render(
                request,
                "accounts/offer_add.html",
                {"candidates": candidates, "preselected": preselected, "company_name": company_name},
            )

        cand = get_object_or_404(RecruitmentCandidate, id=candidate_id)
        department = request.POST.get("department", "").strip()
        joining_dt = date.fromisoformat(joining_date)
        letter_body = request.POST.get("letter_body", "").strip()
        if not letter_body:
            letter_body = _default_offer_body(
                cand, job_title, department, offered_salary, joining_dt, company_name
            )

        offer = OfferLetter.objects.create(
            candidate=cand,
            job_title=job_title,
            department=department,
            offered_salary=offered_salary,
            joining_date=joining_date,
            valid_until=request.POST.get("valid_until") or None,
            status=request.POST.get("status", "Draft").strip(),
            letter_body=letter_body,
        )
        cand.status = "Offered"
        cand.save(update_fields=["status"])
        messages.success(request, "Offer letter created.")
        return redirect("offer_view", id=offer.id)

    return render(
        request,
        "accounts/offer_add.html",
        {"candidates": candidates, "preselected": preselected, "company_name": company_name},
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def offer_edit(request, id):
    offer = get_object_or_404(OfferLetter, id=id)
    company = SystemSettings.objects.first()
    company_name = (company.name or "").strip() if company else "HRMS"

    if request.method == "POST":
        offer.job_title = request.POST.get("job_title", "").strip()
        offer.department = request.POST.get("department", "").strip()
        offer.offered_salary = request.POST.get("offered_salary", "").strip()
        offer.joining_date = request.POST.get("joining_date")
        offer.valid_until = request.POST.get("valid_until") or None
        offer.status = request.POST.get("status", offer.status).strip()
        offer.letter_body = request.POST.get("letter_body", "").strip()
        offer.save()
        if offer.status == "Accepted":
            offer.candidate.status = "Offered"
            offer.candidate.save(update_fields=["status"])
        messages.success(request, "Offer letter updated.")
        return redirect("offer_view", id=offer.id)

    return render(
        request,
        "accounts/offer_edit.html",
        {"offer": offer, "offer_statuses": OFFER_STATUSES, "company_name": company_name},
    )


@login_required(login_url="login")
def offer_view(request, id):
    denied = _recruitment_guard(request)
    if denied:
        return denied
    offer = get_object_or_404(OfferLetter, id=id)
    company = SystemSettings.objects.first()
    return render(
        request,
        "accounts/offer_letter.html",
        {
            "offer": offer,
            "company": company,
            "company_name": (company.name or "HRMS") if company else "HRMS",
        },
    )


# ==================== JOINING PROCESS ====================
@login_required(login_url="login")
def joining_list(request):
    denied = _recruitment_guard(request)
    if denied:
        return denied
    status_filter = request.GET.get("status", "").strip()
    records = JoiningRecord.objects.select_related("candidate", "offer").all()
    if status_filter:
        records = records.filter(status=status_filter)
    record_rows = []
    for r in records:
        doc_done = sum(
            [
                r.id_proof,
                r.address_proof,
                r.education_cert,
                r.previous_employer,
                r.bank_details,
                r.photo_submitted,
            ]
        )
        record_rows.append({"record": r, "doc_done": doc_done})
    return render(
        request,
        "accounts/joining_list.html",
        {
            "record_rows": record_rows,
            "status_filter": status_filter,
            "joining_statuses": JOINING_STATUSES,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def joining_add(request):
    candidates = RecruitmentCandidate.objects.filter(
        status__in=["Offered", "Hired"]
    ).exclude(joining__isnull=False)
    offers = OfferLetter.objects.filter(status__in=["Sent", "Accepted"])
    preselected = request.GET.get("candidate_id", "")

    if request.method == "POST":
        candidate_id = request.POST.get("candidate_id")
        joining_date = request.POST.get("joining_date")
        if not candidate_id or not joining_date:
            messages.error(request, "Candidate and joining date are required.")
            return render(
                request,
                "accounts/joining_add.html",
                {"candidates": candidates, "offers": offers, "preselected": preselected},
            )

        cand = get_object_or_404(RecruitmentCandidate, id=candidate_id)
        offer_id = request.POST.get("offer_id") or None
        JoiningRecord.objects.create(
            candidate=cand,
            offer_id=offer_id,
            joining_date=joining_date,
            status="Pending",
            notes=request.POST.get("notes", "").strip(),
        )
        messages.success(request, "Joining process started.")
        return redirect("joining_list")

    return render(
        request,
        "accounts/joining_add.html",
        {"candidates": candidates, "offers": offers, "preselected": preselected},
    )


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def joining_edit(request, id):
    record = get_object_or_404(JoiningRecord, id=id)
    if request.method == "POST":
        record.joining_date = request.POST.get("joining_date")
        record.id_proof = 1 if request.POST.get("id_proof") else 0
        record.address_proof = 1 if request.POST.get("address_proof") else 0
        record.education_cert = 1 if request.POST.get("education_cert") else 0
        record.previous_employer = 1 if request.POST.get("previous_employer") else 0
        record.bank_details = 1 if request.POST.get("bank_details") else 0
        record.photo_submitted = 1 if request.POST.get("photo_submitted") else 0
        record.notes = request.POST.get("notes", "").strip()
        record.status = request.POST.get("status", record.status).strip()

        docs = [
            record.id_proof,
            record.address_proof,
            record.education_cert,
            record.previous_employer,
            record.bank_details,
            record.photo_submitted,
        ]
        if record.status == "Pending" and any(docs):
            record.status = "In Progress"
        if all(docs) and record.status != "Completed":
            record.status = "Completed"
            record.completed_at = timezone.now()
            record.candidate.status = "Hired"
            record.candidate.save(update_fields=["status"])

        record.save()
        messages.success(request, "Joining record updated.")
        return redirect("joining_edit", id=record.id)

    doc_count = sum(
        [
            record.id_proof,
            record.address_proof,
            record.education_cert,
            record.previous_employer,
            record.bank_details,
            record.photo_submitted,
        ]
    )
    return render(
        request,
        "accounts/joining_edit.html",
        {
            "record": record,
            "joining_statuses": JOINING_STATUSES,
            "doc_count": doc_count,
            "doc_total": 6,
        },
    )


@login_required(login_url="login")
@permission_required("accounts.add_empmaster", raise_exception=True)
def joining_convert_employee(request, id):
    """Start employee onboarding from completed joining."""
    record = get_object_or_404(JoiningRecord, id=id)
    cand = record.candidate
    if record.emp_id:
        messages.info(request, "Employee already created for this candidate.")
        return redirect("employee_list")

    messages.info(request, "Complete employee profile for the new hire.")
    return redirect(f"{reverse('employee_add')}?candidate_id={cand.id}")

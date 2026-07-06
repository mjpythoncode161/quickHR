from django.db import models




class AttendanceMaster(models.Model):
    emp_id = models.IntegerField()
    full_name = models.CharField(max_length=255)
    check_in = models.TimeField()
    check_out = models.TimeField(blank=True, null=True)
    worked_hours = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    worked_day = models.CharField(max_length=20, blank=True, null=True)
    att_date = models.DateField()
    photo = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.CharField(max_length=255)
    longitude = models.CharField(max_length=255)
    out_photo = models.CharField(max_length=255, blank=True, null=True)
    out_lati = models.CharField(max_length=250)
    out_long = models.CharField(max_length=250)
    attendance_status = models.CharField(max_length=250)
    location_status = models.CharField(max_length=50, blank=True, null=True)
    is_paid = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    

    class Meta:
        managed = False
        db_table = "attendance_master"


class AttendanceReq(models.Model):
    emp_id = models.CharField(max_length=50)
    reg_date = models.DateField()
    full_name = models.CharField(max_length=100)
    reason = models.TextField()
    attachment = models.CharField(max_length=250)
    check_in = models.TimeField()
    check_out = models.TimeField()
    approval_status = models.CharField(max_length=250)
    status = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "attendance_req"


class DeptMaster(models.Model):
    dept_name = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = "dept_master"

    def __str__(self):
        return self.dept_name


class DesigMaster(models.Model):
    dept_name = models.CharField(max_length=255)
    desig_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "desig_master"

    def __str__(self):
        return self.desig_name


class EmpItemMaster(models.Model):
    emp_id = models.CharField(max_length=255)
    item_name = models.CharField(max_length=255, blank=True, null=True)
    item_amt = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    item_amt_type = models.CharField(max_length=50, blank=True, null=True)
    item_type = models.CharField(max_length=50, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "emp_item_master"


class EmpMaster(models.Model):
    emp_id = models.CharField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    present_addr = models.TextField(blank=True, null=True)
    perm_addr = models.TextField(blank=True, null=True)
    join_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    emp_type = models.CharField(max_length=50, blank=True, null=True)
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    longitude = models.DecimalField(
        max_digits=10, decimal_places=8, blank=True, null=True
    )
    latitude = models.DecimalField(
        max_digits=11, decimal_places=8, blank=True, null=True
    )
    dept = models.CharField(max_length=255, blank=True, null=True)
    desig = models.CharField(max_length=255, blank=True, null=True)
    salary_type = models.CharField(max_length=50, blank=True, null=True)
    salary_amt = models.CharField(max_length=255)
    full_abs_fine = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    half_abd_fine = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    yearly_leaves = models.IntegerField(blank=True, null=True)
    bank = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    branch_name = models.CharField(max_length=255, blank=True, null=True)
    account_name = models.CharField(max_length=255)
    account_no = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    entried_by = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    total_yearly_leaves = models.CharField(max_length=250)
    profile_photo = models.CharField(max_length=250)
    blood_group = models.CharField(max_length=250)
    father_name = models.CharField(max_length=250)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    gps_tracking = models.IntegerField(default=1, blank=True, null=True)
    late_attendance_penalty = models.IntegerField(default=1, blank=True, null=True)
    photo_selfie = models.IntegerField(default=1, blank=True, null=True)
    week_off = models.CharField(max_length=50, blank=True, null=True, default="5,6")
    employee_code = models.CharField(max_length=100, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    official_email = models.CharField(max_length=255, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    education = models.CharField(max_length=255, blank=True, null=True)
    work_experience = models.CharField(max_length=255, blank=True, null=True)
    employment_status = models.CharField(max_length=50, blank=True, null=True)
    shift = models.CharField(max_length=100, blank=True, null=True)
    work_mode = models.CharField(max_length=50, blank=True, null=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)
    aadhar_no = models.CharField(max_length=20, blank=True, null=True)
    passport_no = models.CharField(max_length=50, blank=True, null=True)
    driving_license = models.CharField(max_length=50, blank=True, null=True)
    notice_period_days = models.IntegerField(blank=True, null=True)
    biometric_enabled = models.IntegerField(default=0, blank=True, null=True)
    biometric_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    

    class Meta:
        managed = False
        db_table = "emp_master"

    def __str__(self):
        return self.full_name or self.emp_id


class EmpTemp(models.Model):
    full_name = models.CharField(max_length=150)
    contact = models.CharField(unique=True, max_length=15)
    email = models.CharField(unique=True, max_length=150)
    password = models.CharField(max_length=255)
    dob = models.DateField()
    gender = models.CharField(max_length=50)
    address = models.TextField(blank=True, null=True)
    father_name = models.CharField(max_length=150, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    caste = models.CharField(max_length=50, blank=True, null=True)
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    qualification = models.CharField(max_length=100, blank=True, null=True)
    work = models.CharField(max_length=150, blank=True, null=True)
    experience = models.CharField(max_length=20, blank=True, null=True)
    bank = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=150, blank=True, null=True)
    branch_name = models.CharField(max_length=150, blank=True, null=True)
    account_name = models.CharField(max_length=150, blank=True, null=True)
    account_number = models.CharField(max_length=30, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(
        max_length=8, default="PENDING"
    )  # PENDING, APPROVED, REJECTED
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "emp_temp"

    def __str__(self):
        return self.full_name


class Events(models.Model):
    event_title = models.CharField(max_length=255)
    event_desc = models.TextField()
    event_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "events"

    def __str__(self):
        return self.event_title


class HolidayMaster(models.Model):
    holiday_tital = models.CharField(max_length=255)
    holiday_date = models.DateField()

    class Meta:
        managed = False
        db_table = "holiday_master"

    def __str__(self):
        return self.holiday_tital


class LeaveMaster(models.Model):
    leave_type = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    is_paid = models.IntegerField(default=1, blank=True, null=True)
    allow_half_day = models.IntegerField(default=0, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "leave_master"

    def __str__(self):
        return self.leave_type


class LeaveRequest(models.Model):
    emp_id = models.IntegerField()
    full_name = models.CharField(max_length=255, blank=True, null=True)
    leave_type = models.CharField(max_length=255, blank=True, null=True)
    leave_duration = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_status = models.IntegerField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    approved_by = models.CharField(max_length=255, blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    total_leaves = models.IntegerField(default=0)
    yearly_leaves = models.IntegerField(default=0)
    is_paid = models.IntegerField()

    class Meta:
        managed = False
        db_table = "leave_request"


class LogoMaster(models.Model):
    image_name = models.CharField(max_length=250)
    image_path = models.CharField(max_length=250)
    created_at = models.DateField()

    class Meta:
        managed = False
        db_table = "logo_master"


class SystemSettings(models.Model):
    name = models.TextField()
    email = models.CharField(max_length=200)
    contact = models.CharField(max_length=20)
    address = models.TextField()
    cover_img = models.TextField()

    class Meta:
        managed = False
        db_table = "system_settings"


class ApiSettings(models.Model):

    api_token = models.CharField(max_length=128, blank=True, default="")
    api_enabled = models.IntegerField(default=1)
    biometric_enabled = models.IntegerField(default=1)
    device_name = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_settings"
        verbose_name = "API Settings"
        verbose_name_plural = "API Settings"

    def __str__(self):
        return "API Settings"


class RoleMaster(models.Model):
    name = models.CharField(max_length=100, unique=True)
    legacy_type = models.IntegerField(unique=True)
    group_name = models.CharField(max_length=100)
    is_staff = models.IntegerField(default=0)
    description = models.TextField(blank=True, default="")
    is_active = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_master"
        ordering = ["legacy_type"]

    def __str__(self):
        return self.name


class ShiftMaster(models.Model):
    shift_name = models.CharField(max_length=100, unique=True)
    check_in = models.TimeField()
    check_out = models.TimeField()
    grace_minutes = models.IntegerField(default=10)
    description = models.TextField(blank=True, default="")
    is_active = models.IntegerField(default=1)
    rotation_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shift_master"
        ordering = ["rotation_order", "shift_name"]

    def __str__(self):
        return self.shift_name

    def time_range_display(self):
        return f"{self.check_in.strftime('%I:%M %p')} – {self.check_out.strftime('%I:%M %p')}"


class TitleMaster(models.Model):
    title_update = models.CharField(max_length=250)
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "title_master"


class Users(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    password = models.TextField()
    type = models.IntegerField(
        default=2
    )  # 1=Admin, 2=Employee, 3=Account
    contact = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self):
        return self.full_name


class ClientVisitor(models.Model):
    """Records client / visitor meetings added by field employees."""

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="client_visitors",
        db_column="user_id",
    )
    emp_id = models.CharField(max_length=255, blank=True, null=True)
    emp_name = models.CharField(max_length=255, blank=True, null=True)
    client_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    visit_date = models.DateField()
    photo = models.ImageField(upload_to="visitor_photos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "client_visitor"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client_name} — {self.emp_name or self.user.username}"


class EmployeeLocationTracking(models.Model):
    """Stores GPS location updates for employees during their work session."""

    user_id = models.IntegerField()
    emp_id = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=11, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_date = models.DateField(blank=True, null=True)
    is_checkin_point = models.BooleanField(default=False)
    is_checkout_point = models.BooleanField(default=False)

    class Meta:
        db_table = "employee_location_tracking"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.full_name or self.emp_id} @ {self.timestamp}"


class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, default="")
    designation = models.CharField(max_length=255, blank=True, default="")
    job_type = models.CharField(max_length=50, default="Full-time")
    location = models.CharField(max_length=255, blank=True, default="")
    openings = models.IntegerField(default=1)
    experience_required = models.CharField(max_length=100, blank=True, default="")
    salary_range = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, default="Open")
    posted_date = models.DateField(auto_now_add=True)
    closing_date = models.DateField(blank=True, null=True)
    created_by = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_posting"
        ordering = ["-posted_date", "-id"]

    def __str__(self):
        return self.title


class RecruitmentCandidate(models.Model):
    job = models.ForeignKey(
        JobPosting, on_delete=models.SET_NULL, null=True, blank=True, related_name="candidates"
    )
    full_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=20)
    gender = models.CharField(max_length=10, blank=True, default="")
    dob = models.DateField(blank=True, null=True)
    education = models.CharField(max_length=255, blank=True, default="")
    experience_years = models.CharField(max_length=50, blank=True, default="")
    current_company = models.CharField(max_length=255, blank=True, default="")
    current_salary = models.CharField(max_length=100, blank=True, default="")
    expected_salary = models.CharField(max_length=100, blank=True, default="")
    resume_path = models.CharField(max_length=500, blank=True, default="")
    source = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=30, default="New")
    notes = models.TextField(blank=True, default="")
    applied_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recruitment_candidate"
        ordering = ["-applied_date", "-id"]

    def __str__(self):
        return self.full_name


class RecruitmentInterview(models.Model):
    candidate = models.ForeignKey(
        RecruitmentCandidate, on_delete=models.CASCADE, related_name="interviews"
    )
    interview_date = models.DateField()
    interview_time = models.TimeField()
    interview_type = models.CharField(max_length=50, default="In-person")
    interviewer = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, default="Scheduled")
    feedback = models.TextField(blank=True, default="")
    rating = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recruitment_interview"
        ordering = ["-interview_date", "-interview_time"]

    def __str__(self):
        return f"{self.candidate.full_name} — {self.interview_date}"


class OfferLetter(models.Model):
    candidate = models.ForeignKey(
        RecruitmentCandidate, on_delete=models.CASCADE, related_name="offers"
    )
    job_title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, default="")
    offered_salary = models.CharField(max_length=100)
    joining_date = models.DateField()
    offer_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, default="Draft")
    letter_body = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "offer_letter"
        ordering = ["-offer_date", "-id"]

    def __str__(self):
        return f"Offer — {self.candidate.full_name}"


class JoiningRecord(models.Model):
    candidate = models.OneToOneField(
        RecruitmentCandidate, on_delete=models.CASCADE, related_name="joining"
    )
    offer = models.ForeignKey(
        OfferLetter, on_delete=models.SET_NULL, null=True, blank=True
    )
    joining_date = models.DateField()
    id_proof = models.IntegerField(default=0)
    address_proof = models.IntegerField(default=0)
    education_cert = models.IntegerField(default=0)
    previous_employer = models.IntegerField(default=0)
    bank_details = models.IntegerField(default=0)
    photo_submitted = models.IntegerField(default=0)
    status = models.CharField(max_length=30, default="Pending")
    emp_id = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "joining_record"
        ordering = ["-joining_date"]

    def __str__(self):
        return f"Joining — {self.candidate.full_name}"


class SalaryStructureConfig(models.Model):
    """Company-wide salary breakdown settings for employee forms."""

    salary_base_mode = models.CharField(max_length=20, default="gross")
    salary_field_label = models.CharField(max_length=100, default="Gross Salary (₹)")
    show_basic_row = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "salary_structure_config"
        verbose_name = "Salary Structure Config"

    def __str__(self):
        return "Salary Structure Settings"


class SalaryComponentRule(models.Model):
    component_name = models.CharField(max_length=100)
    calc_method = models.CharField(max_length=20, default="fixed")
    rate_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    item_type = models.CharField(max_length=20, default="Earning")
    sort_order = models.IntegerField(default=0)
    is_active = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "salary_component_rule"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.component_name


class PayrollModuleConfig(models.Model):
    """On/off toggles for payroll features in Settings and sidebar."""

    employee_salary_setup = models.IntegerField(default=1)
    salary_structure = models.IntegerField(default=1)
    deductions = models.IntegerField(default=0)
    employer_contributions = models.IntegerField(default=0)
    attendance_integration = models.IntegerField(default=1)
    payroll_processing = models.IntegerField(default=0)
    statutory_compliance = models.IntegerField(default=0)
    payslip = models.IntegerField(default=1)
    payroll_reports = models.IntegerField(default=0)
    payroll_approvals = models.IntegerField(default=0)
    payroll_settings = models.IntegerField(default=1)
    extra_ot_working = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payroll_module_config"
        verbose_name = "Payroll Module Config"

    def __str__(self):
        return "Payroll Module Settings"


class ExtraOtConfig(models.Model):
    """Extra overtime (OT) pay settings — applies to all employees."""

    RATE_MULTIPLIER = "multiplier"
    RATE_FIXED = "fixed_hourly"

    CALC_SHIFT_OT = "shift_overtime"
    CALC_SLAB_HALF_FULL = "slab_half_full"

    BASIS_OT_ONLY = "ot_only"
    BASIS_TOTAL_WORKED = "total_worked"

    enabled = models.IntegerField(default=0)
    calc_policy = models.CharField(max_length=30, default=CALC_SHIFT_OT)
    hours_basis = models.CharField(max_length=20, default=BASIS_OT_ONLY)
    half_day_threshold_hours = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    full_day_threshold_hours = models.DecimalField(max_digits=5, decimal_places=2, default=8.0)
    ot_rate_mode = models.CharField(max_length=20, default=RATE_MULTIPLIER)
    ot_multiplier = models.DecimalField(max_digits=6, decimal_places=2, default=2.0)
    ot_hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    working_days_per_month = models.IntegerField(default=26)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "extra_ot_config"
        verbose_name = "Extra OT Config"

    def __str__(self):
        return "Extra OT Settings"


class ShiftRotationConfig(models.Model):
    """Automatic rotation-wise shift assignment for attendance."""

    enabled = models.IntegerField(default=0)
    cycle_days = models.IntegerField(default=7)
    rotation_start_date = models.DateField(blank=True, null=True)
    stagger_employees = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shift_rotation_config"
        verbose_name = "Shift Rotation Config"

    def __str__(self):
        return "Shift Rotation Settings"


class HrModuleConfig(models.Model):
    """On/off toggles for HR features (Claims, Recruitment, etc.)."""

    claims = models.IntegerField(default=0)
    recruitment = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hr_module_config"
        verbose_name = "HR Module Config"

    def __str__(self):
        return "HR Module Settings"


class ClaimCategory(models.Model):
    """Dynamic claim type categories for expense claims dropdown."""

    category_name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "claim_category"
        ordering = ["sort_order", "category_name"]
        verbose_name_plural = "Claim categories"

    def __str__(self):
        return self.category_name


class ExpenseClaim(models.Model):
    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2
    STATUS_PAID = 3

    emp_id = models.CharField(max_length=50)
    full_name = models.CharField(max_length=255, blank=True, default="")
    claim_type = models.CharField(max_length=100)
    claim_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True, default="")
    receipt_note = models.CharField(max_length=255, blank=True, default="")
    status = models.IntegerField(default=0)
    admin_remarks = models.TextField(blank=True, default="")
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "expense_claim"
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.full_name} — {self.claim_type} — ₹{self.amount}"

    @property
    def status_label(self):
        return {0: "Pending", 1: "Approved", 2: "Rejected", 3: "Paid"}.get(
            self.status, "Pending"
        )

    @property
    def status_badge(self):
        return {
            0: "warning",
            1: "success",
            2: "danger",
            3: "info",
        }.get(self.status, "secondary")


class RecruitmentSettings(models.Model):
    """Company recruitment & API integration settings."""

    webhook_token = models.CharField(max_length=128, blank=True, default="")
    auto_receive_applications = models.IntegerField(default=1)
    notify_email = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruitment_settings"

    def __str__(self):
        return "Recruitment Settings"


class RecruitmentPlatform(models.Model):
    """Job board / platform API connection."""

    platform_key = models.CharField(max_length=50, unique=True)
    platform_name = models.CharField(max_length=100)
    is_enabled = models.IntegerField(default=0)
    api_key = models.CharField(max_length=500, blank=True, default="")
    api_secret = models.CharField(max_length=500, blank=True, default="")
    company_id = models.CharField(max_length=255, blank=True, default="")
    api_url = models.CharField(max_length=500, blank=True, default="")
    auto_post_jobs = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recruitment_platform"
        ordering = ["sort_order", "platform_name"]

    def __str__(self):
        return self.platform_name


class JobPlatformPost(models.Model):
    """Job published to an external platform."""

    job = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="platform_posts"
    )
    platform = models.ForeignKey(
        RecruitmentPlatform, on_delete=models.CASCADE, related_name="job_posts"
    )
    external_job_id = models.CharField(max_length=255, blank=True, default="")
    external_url = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=30, default="Pending")
    sync_message = models.TextField(blank=True, default="")
    posted_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_platform_post"
        unique_together = [("job", "platform")]

    def __str__(self):
        return f"{self.job.title} → {self.platform.platform_name}"


class NotificationModuleConfig(models.Model):
    """On/off toggles for notification channels and features."""

    email_notifications = models.IntegerField(default=0)
    sms_notifications = models.IntegerField(default=0)
    whatsapp_notifications = models.IntegerField(default=0)
    push_notifications = models.IntegerField(default=0)
    in_app_alerts = models.IntegerField(default=1)
    reminders = models.IntegerField(default=0)
    notification_settings = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_module_config"
        verbose_name = "Notification Module Config"

    def __str__(self):
        return "Notification Module Settings"


class NotificationChannelConfig(models.Model):
    """Email, SMS and WhatsApp API credentials."""

    smtp_host = models.CharField(max_length=255, blank=True, default="")
    smtp_port = models.IntegerField(default=587)
    smtp_user = models.CharField(max_length=255, blank=True, default="")
    smtp_password = models.CharField(max_length=255, blank=True, default="")
    smtp_use_tls = models.IntegerField(default=1)
    from_email = models.CharField(max_length=255, blank=True, default="")
    from_name = models.CharField(max_length=255, blank=True, default="")

    sms_provider = models.CharField(max_length=50, blank=True, default="msg91")
    sms_api_key = models.CharField(max_length=500, blank=True, default="")
    sms_api_secret = models.CharField(max_length=500, blank=True, default="")
    sms_sender_id = models.CharField(max_length=20, blank=True, default="")
    sms_api_url = models.CharField(max_length=500, blank=True, default="")

    whatsapp_provider = models.CharField(max_length=50, blank=True, default="meta")
    whatsapp_api_key = models.CharField(max_length=500, blank=True, default="")
    whatsapp_api_secret = models.CharField(max_length=500, blank=True, default="")
    whatsapp_phone_id = models.CharField(max_length=100, blank=True, default="")
    whatsapp_api_url = models.CharField(
        max_length=500, blank=True, default="https://graph.facebook.com/v18.0"
    )

    push_provider = models.CharField(max_length=50, blank=True, default="fcm")
    push_server_key = models.CharField(max_length=500, blank=True, default="")
    push_project_id = models.CharField(max_length=200, blank=True, default="")
    push_sender_id = models.CharField(max_length=200, blank=True, default="")

    admin_notify_email = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_channel_config"

    def __str__(self):
        return "Notification Channel Settings"


class NotificationEventTemplate(models.Model):
    """Templates for automated alerts by event type."""

    event_key = models.CharField(max_length=80, unique=True)
    event_name = models.CharField(max_length=150)
    email_enabled = models.IntegerField(default=1)
    sms_enabled = models.IntegerField(default=0)
    whatsapp_enabled = models.IntegerField(default=0)
    push_enabled = models.IntegerField(default=0)
    in_app_enabled = models.IntegerField(default=1)
    email_subject = models.CharField(max_length=255, blank=True, default="")
    email_body = models.TextField(blank=True, default="")
    sms_body = models.CharField(max_length=500, blank=True, default="")
    whatsapp_body = models.TextField(blank=True, default="")
    push_body = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.IntegerField(default=1)

    class Meta:
        db_table = "notification_event_template"
        ordering = ["sort_order", "event_name"]

    def __str__(self):
        return self.event_name


class NotificationLog(models.Model):
    """Sent notification history."""

    channel = models.CharField(max_length=20)
    event_key = models.CharField(max_length=80, blank=True, default="")
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, default="Pending")
    error_message = models.TextField(blank=True, default="")
    emp_id = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel} → {self.recipient} ({self.status})"


class MobileDeviceToken(models.Model):
    """FCM / mobile push device tokens for employees."""

    user_id = models.IntegerField(blank=True, null=True)
    emp_id = models.CharField(max_length=50, blank=True, default="")
    device_token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=20, blank=True, default="android")
    device_name = models.CharField(max_length=200, blank=True, default="")
    is_active = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mobile_device_token"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.emp_id or self.user_id} — {self.platform}"


class NotificationReminder(models.Model):
    """Scheduled reminders and alerts."""

    title = models.CharField(max_length=200)
    message = models.TextField()
    channel = models.CharField(max_length=30, default="all")
    recipient_type = models.CharField(max_length=30, default="all_employees")
    recipient_value = models.CharField(max_length=255, blank=True, default="")
    schedule_date = models.DateField(blank=True, null=True)
    schedule_time = models.TimeField(blank=True, null=True)
    repeat_type = models.CharField(max_length=20, default="none")
    is_active = models.IntegerField(default=1)
    last_sent_at = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification_reminder"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class InAppNotification(models.Model):
    """In-app notification inbox for portal users."""

    user_id = models.IntegerField()
    emp_id = models.CharField(max_length=50, blank=True, default="")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link_url = models.CharField(max_length=500, blank=True, default="")
    is_read = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "in_app_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SaasPlatformConfig(models.Model):
    """Global SaaS platform branding and landing copy."""

    platform_name = models.CharField(max_length=150, default="QuickHR")
    tagline = models.CharField(max_length=255, default="Complete HRMS for modern organizations")
    hero_title = models.CharField(max_length=255, default="All-in-One HRMS SaaS Platform")
    hero_subtitle = models.TextField(
        default="Attendance, payroll, recruitment, claims & more — one cloud platform for your entire workforce."
    )
    about_title = models.CharField(max_length=200, default="About QuickHR")
    about_body = models.TextField(blank=True, default="")
    support_email = models.CharField(max_length=255, default="support@quickhr.in")
    support_phone = models.CharField(max_length=30, blank=True, default="+91 6361212012")
    support_phone_2 = models.CharField(max_length=30, blank=True, default="")
    office_address = models.TextField(blank=True, default="")
    footer_text = models.CharField(max_length=255, blank=True, default="")
    price_per_employee_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    min_paid_employees = models.IntegerField(default=10)
    yearly_months_billed = models.IntegerField(
        default=10,
        help_text="Months charged on yearly plan (e.g. 10 = pay for 10 months, get 12)",
    )
    trial_days = models.IntegerField(default=7)
    trial_max_employees = models.IntegerField(default=25)
    free_max_employees = models.IntegerField(default=2)
    is_maintenance = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_platform_config"

    def __str__(self):
        return self.platform_name


class SaasPricingPlan(models.Model):
    plan_key = models.CharField(max_length=50, unique=True)
    plan_name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="INR")
    max_employees = models.IntegerField(default=50)
    description = models.TextField(blank=True, default="")
    features = models.TextField(blank=True, default="")
    razorpay_plan_id = models.CharField(max_length=80, blank=True, default="")
    is_popular = models.IntegerField(default=0)
    is_active = models.IntegerField(default=1)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "saas_pricing_plan"
        ordering = ["sort_order", "price_monthly"]

    def __str__(self):
        return self.plan_name

    def feature_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]


class SaasProduct(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True)
    icon = models.CharField(max_length=80, default="fas fa-cube")
    short_desc = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.IntegerField(default=1)

    class Meta:
        db_table = "saas_product"
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


class SaasService(models.Model):
    title = models.CharField(max_length=150)
    icon = models.CharField(max_length=80, default="fas fa-concierge-bell")
    short_desc = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_active = models.IntegerField(default=1)

    class Meta:
        db_table = "saas_service"
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


class SaasOrganization(models.Model):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"

    org_name = models.CharField(max_length=200)
    org_slug = models.SlugField(max_length=100, unique=True)
    admin_name = models.CharField(max_length=200, blank=True, default="")
    admin_email = models.CharField(max_length=255, blank=True, default="")
    admin_phone = models.CharField(max_length=20, blank=True, default="")
    plan = models.ForeignKey(
        SaasPricingPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organizations",
    )
    status = models.CharField(max_length=20, default=STATUS_TRIAL)
    max_employees = models.IntegerField(default=50)
    trial_ends_at = models.DateField(blank=True, null=True)
    razorpay_subscription_id = models.CharField(max_length=80, blank=True, default="")
    razorpay_customer_id = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_organization"
        ordering = ["-created_at"]

    def __str__(self):
        return self.org_name


class SaasContactInquiry(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, default="")
    company = models.CharField(max_length=200, blank=True, default="")
    subject = models.CharField(max_length=200, blank=True, default="")
    message = models.TextField()
    plan_interest = models.CharField(max_length=100, blank=True, default="")
    source = models.CharField(max_length=30, blank=True, default="contact")
    status = models.CharField(max_length=20, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "saas_contact_inquiry"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.email}"


class SaasSubscription(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    BILLING_SUBSCRIPTION = "subscription"
    BILLING_ORDER = "order"

    plan = models.ForeignKey(
        SaasPricingPlan,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subscriptions",
    )
    organization = models.ForeignKey(
        SaasOrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    customer_name = models.CharField(max_length=200, blank=True, default="")
    customer_email = models.CharField(max_length=255, blank=True, default="")
    customer_phone = models.CharField(max_length=20, blank=True, default="")
    company_name = models.CharField(max_length=200, blank=True, default="")
    razorpay_subscription_id = models.CharField(max_length=80, blank=True, default="")
    razorpay_order_id = models.CharField(max_length=80, blank=True, default="")
    razorpay_payment_id = models.CharField(max_length=80, blank=True, default="")
    billing_mode = models.CharField(max_length=20, default=BILLING_SUBSCRIPTION)
    status = models.CharField(max_length=20, default=STATUS_PENDING)
    amount_paise = models.IntegerField(default=0)
    employee_count = models.IntegerField(default=10)
    billing_period = models.CharField(max_length=10, default="monthly")
    price_per_employee = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_subscription"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_email} — {self.plan_id} ({self.status})"

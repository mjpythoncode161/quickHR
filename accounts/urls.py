from django.urls import path
from . import views
from . import recruitment_views as recruitment
from . import salary_structure_views
from . import payroll_module_views
from . import extra_ot_views
from . import shift_rotation_views
from . import hr_module_views
from . import claims_views
from . import recruitment_integration_views as recruitment_api
from . import notification_views
from . import saas_views
from .hr_module_utils import get_hr_hub_items
from .notification_module_utils import get_notification_hub_items


urlpatterns = [
    # Public SaaS landing website
    path("", saas_views.landing_home, name="landing_home"),
    path("about/", saas_views.landing_about, name="landing_about"),
    path("products/", saas_views.landing_products, name="landing_products"),
    path("services/", saas_views.landing_services, name="landing_services"),
    path("pricing/", saas_views.landing_pricing, name="landing_pricing"),
    path("contact/", saas_views.landing_contact, name="landing_contact"),
    path("subscribe/<slug:plan_key>/", saas_views.subscribe_plan, name="subscribe_plan"),
    path("subscribe/success/", saas_views.subscribe_success, name="subscribe_success"),
    path("webhooks/razorpay/", saas_views.razorpay_webhook, name="razorpay_webhook"),
    path("login/", views.login, name="login"),
    path("home/", views.home, name="home"),
    # Authentication URLs
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("manage_account/", views.manage_account, name="manage_account"),
    # Password Reset URLs
    path("forgot_password/", views.forgot_password, name="forgot_password"),
    path(
        "reset_password/<uidb64>/<token>/", views.reset_password, name="reset_password"
    ),
    path("reset_password_sent/", views.reset_password_sent, name="reset_password_sent"),
    path(
        "reset_password_complete/",
        views.reset_password_complete,
        name="reset_password_complete",
    ),
    # User Management URLs
    path("user_list/", views.user_list, name="user_list"),
    path("user_add/", views.user_add, name="user_add"),
    path("user_edit/<int:id>/", views.user_edit, name="user_edit"),
    path("user_delete/<int:id>/", views.user_delete, name="user_delete"),
    path("role_settings/", views.role_settings, name="role_settings"),
    path("role_assign/", views.role_assign, name="role_assign"),
    # Registration Request Management URLs
    path("reg_user_list/", views.reg_user_list, name="reg_user_list"),
    path("reg_user_approve/<int:id>/", views.reg_user_approve, name="reg_user_approve"),
    path("reg_user_reject/<int:id>/", views.reg_user_reject, name="reg_user_reject"),
    path(
        "get_employee_by_mobile/",
        views.get_employee_by_mobile,
        name="get_employee_by_mobile",
    ),
    path("department_add/", views.department_add, name="department_add"),
    path("department_list/", views.department_list, name="department_list"),
    path(
        "department_delete/<int:id>/", views.department_delete, name="department_delete"
    ),
    path("department_edit/<int:id>/", views.department_edit, name="department_edit"),
    path("designation_add/", views.designation_add, name="designation_add"),
    path("designation_list/", views.designation_list, name="designation_list"),
    path("designation_edit/<int:id>/", views.designation_edit, name="designation_edit"),
    path(
        "designation_delete/<int:id>/",
        views.designation_delete,
        name="designation_delete",
    ),
    path("employee_list/", views.employee_list, name="employee_list"),
    path("employee_view/<int:id>/", views.employee_view, name="employee_view"),
    path("employee_add/", views.employee_add, name="employee_add"),
    path("employee_edit/<int:id>/", views.employee_edit, name="employee_edit"),
    path("employee_delete/<int:id>/", views.employee_delete, name="employee_delete"),
    # Attendance URLs
    path("employee_checkin/", views.employee_checkin, name="employee_checkin"),
    path("employee_checkout/", views.employee_checkout, name="employee_checkout"),
    path("attendance_list/", views.attendance_list, name="attendance_list"),
    path("attendance_add/", views.attendance_add, name="attendance_add"),
    path("attendance_edit/<int:id>/", views.attendance_edit, name="attendance_edit"),
    path(
        "attendance_detail/<int:id>/", views.attendance_detail, name="attendance_detail"
    ),
    path("attendance_req_list/", views.attendance_req_list, name="attendance_req_list"),
    path("attendance_req_add/", views.attendance_req_add, name="attendance_req_add"),
    path("attendance_req_status_update/<int:id>/",
        views.attendance_req_status_update,
        name="attendance_req_status_update",
    ),
    path("shift_list/", views.shift_list, name="shift_list"),
    path("shift_add/", views.shift_add, name="shift_add"),
    path("shift_edit/<int:id>/", views.shift_edit, name="shift_edit"),
    path("shift_delete/<int:id>/", views.shift_delete, name="shift_delete"),
    path(
        "shift_rotation_settings/",
        shift_rotation_views.shift_rotation_settings,
        name="shift_rotation_settings",
    ),
    path(
        "hr_module_settings/",
        hr_module_views.hr_module_settings,
        name="hr_module_settings",
    ),
    path("late_coming_report/", views.late_coming_report, name="late_coming_report"),
    # Leaves URLs
    path("leave_list/", views.leave_list, name="leave_list"),
    path("leave_add/", views.leave_add, name="leave_add"),
    path("leave_approval_list/", views.leave_approval_list, name="leave_approval_list"),
    path(
        "leave_status_update/<int:id>/",
        views.leave_status_update,
        name="leave_status_update",
    ),
    path("leave_approve/<int:id>/", views.leave_approve, name="leave_approve"),
    path("leave_reject/<int:id>/", views.leave_reject, name="leave_reject"),
    # Claims URLs
    path("claim_list/", claims_views.claim_list, name="claim_list"),
    path("claim_add/", claims_views.claim_add, name="claim_add"),
    path("claim_approval_list/", claims_views.claim_approval_list, name="claim_approval_list"),
    path("claim_status_update/<int:id>/", claims_views.claim_status_update, name="claim_status_update"),
    path("claim_category_settings/", claims_views.claim_category_settings, name="claim_category_settings"),
    # Holiday URLs
    path("holiday_list/", views.holiday_list, name="holiday_list"),
    path("holiday_add/", views.holiday_add, name="holiday_add"),
    path("holiday_delete/<int:id>/", views.holiday_delete, name="holiday_delete"),
    # Payslip URLs
    path("payslip_generate/", views.payslip_generate, name="payslip_generate"),
    # Settings URLs
    path("company_settings/", views.company_settings, name="company_settings"),
    path("api_settings/", views.api_settings, name="api_settings"),
    path("settings_hub/", views.settings_hub, name="settings_hub"),
    path(
        "salary_structure_settings/",
        salary_structure_views.salary_structure_settings,
        name="salary_structure_settings",
    ),
    path(
        "payroll_module_settings/",
        payroll_module_views.payroll_module_settings,
        name="payroll_module_settings",
    ),
    path(
        "payroll/module/<str:module_key>/",
        payroll_module_views.payroll_module_page,
        name="payroll_module_page",
    ),
    path(
        "extra_ot_working/",
        extra_ot_views.extra_ot_working,
        name="extra_ot_working",
    ),
    # Reports URLs
    path("attendance_report/", views.attendance_report, name="attendance_report"),
    path(
        "monthly_attendance_report/",
        views.monthly_attendance_report,
        name="monthly_attendance_report",
    ),
    path(
        "self_attendance_report/",
        views.self_attendance_report,
        name="self_attendance_report",
    ),
    # Location Tracking URLs
    path(
        "save_location_update/", views.save_location_update, name="save_location_update"
    ),
    path(
        "employee_location_map/<str:emp_id>/<str:session_date>/",
        views.employee_location_map,
        name="employee_location_map",
    ),
    # Visitor / Client Management URLs
    path("visitor_add/", views.visitor_add, name="visitor_add"),
    path("visitor_list/", views.visitor_list, name="visitor_list"),
    path("visitor_view/<int:id>/", views.visitor_view, name="visitor_view"),
    path("visitor_edit/<int:id>/", views.visitor_edit, name="visitor_edit"),
    path("visitor_delete/<int:id>/", views.visitor_delete, name="visitor_delete"),
    # Recruitment Management
    path("recruitment/", recruitment.recruitment_dashboard, name="recruitment_dashboard"),
    path("job_list/", recruitment.job_list, name="job_list"),
    path("job_add/", recruitment.job_add, name="job_add"),
    path("job_edit/<int:id>/", recruitment.job_edit, name="job_edit"),
    path("job_view/<int:id>/", recruitment.job_view, name="job_view"),
    path("job_delete/<int:id>/", recruitment.job_delete, name="job_delete"),
    path("candidate_list/", recruitment.candidate_list, name="candidate_list"),
    path("candidate_add/", recruitment.candidate_add, name="candidate_add"),
    path("candidate_edit/<int:id>/", recruitment.candidate_edit, name="candidate_edit"),
    path("candidate_view/<int:id>/", recruitment.candidate_view, name="candidate_view"),
    path("candidate_delete/<int:id>/", recruitment.candidate_delete, name="candidate_delete"),
    path("interview_list/", recruitment.interview_list, name="interview_list"),
    path("interview_add/", recruitment.interview_add, name="interview_add"),
    path("interview_edit/<int:id>/", recruitment.interview_edit, name="interview_edit"),
    path("offer_list/", recruitment.offer_list, name="offer_list"),
    path("offer_add/", recruitment.offer_add, name="offer_add"),
    path("offer_edit/<int:id>/", recruitment.offer_edit, name="offer_edit"),
    path("offer_view/<int:id>/", recruitment.offer_view, name="offer_view"),
    path("joining_list/", recruitment.joining_list, name="joining_list"),
    path("joining_add/", recruitment.joining_add, name="joining_add"),
    path("joining_edit/<int:id>/", recruitment.joining_edit, name="joining_edit"),
    path(
        "joining_convert/<int:id>/",
        recruitment.joining_convert_employee,
        name="joining_convert_employee",
    ),
    # Recruitment platform API integration
    path(
        "recruitment_settings/",
        recruitment_api.recruitment_settings,
        name="recruitment_settings",
    ),
    path(
        "job_publish_platform/<int:job_id>/<int:platform_id>/",
        recruitment_api.job_publish_platform,
        name="job_publish_platform",
    ),
    path(
        "job_publish_all/<int:job_id>/",
        recruitment_api.job_publish_all,
        name="job_publish_all",
    ),
    path(
        "api/recruitment/webhook/",
        recruitment_api.recruitment_webhook,
        name="recruitment_webhook",
    ),
    path(
        "api/recruitment/webhook/<str:platform_key>/",
        recruitment_api.recruitment_webhook,
        name="recruitment_webhook_platform",
    ),
    # Notification Center
    path(
        "notification_module_settings/",
        notification_views.notification_module_settings,
        name="notification_module_settings",
    ),
    path(
        "notification_channel_settings/",
        notification_views.notification_channel_settings,
        name="notification_channel_settings",
    ),
    path(
        "notification_center/",
        notification_views.notification_center,
        name="notification_center",
    ),
    path(
        "mobile_push_dashboard/",
        notification_views.mobile_push_dashboard,
        name="mobile_push_dashboard",
    ),
    path(
        "notification_templates/",
        notification_views.notification_templates,
        name="notification_templates",
    ),
    path(
        "notification_reminders/",
        notification_views.notification_reminders,
        name="notification_reminders",
    ),
    path(
        "notification_log/",
        notification_views.notification_log,
        name="notification_log",
    ),
    path(
        "my_notifications/",
        notification_views.my_notifications,
        name="my_notifications",
    ),
    path(
        "notification_mark_read/<int:id>/",
        notification_views.notification_mark_read,
        name="notification_mark_read",
    ),
    path(
        "notification_mark_all_read/",
        notification_views.notification_mark_all_read,
        name="notification_mark_all_read",
    ),
    # Super Admin (SaaS platform — Django superuser only)
    path("superadmin/", saas_views.superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin/platform/", saas_views.superadmin_platform, name="superadmin_platform"),
    path("superadmin/plans/", saas_views.superadmin_plans, name="superadmin_plans"),
    path(
        "superadmin/organizations/",
        saas_views.superadmin_organizations,
        name="superadmin_organizations",
    ),
    path("superadmin/inquiries/", saas_views.superadmin_inquiries, name="superadmin_inquiries"),
    path("superadmin/catalog/", saas_views.superadmin_catalog, name="superadmin_catalog"),
]

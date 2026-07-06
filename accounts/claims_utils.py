"""Dynamic claim category helpers."""

from .models import ClaimCategory

DEFAULT_CLAIM_CATEGORIES = [
    ("Travel Claim", "Travel, taxi, flight, train expenses"),
    ("Fuel/Petrol Claim", "Fuel and petrol reimbursement"),
    ("Food/Meal Claim", "Meals during work travel or client visits"),
    ("Hotel/Accommodation Claim", "Hotel and lodging expenses"),
    ("Medical Reimbursement", "Medical bills and health expenses"),
    ("Telephone/Mobile Bill Claim", "Mobile and telephone bills"),
    ("Internet/Wi-Fi Claim", "Internet and Wi-Fi charges"),
    ("Office Expense Claim", "Stationery, supplies, office costs"),
    ("Client Entertainment Claim", "Client meetings and entertainment"),
    ("Training & Certification Claim", "Courses, exams, certifications"),
    ("Vehicle Maintenance Claim", "Vehicle service and maintenance"),
    ("Uniform Claim", "Uniform and workwear"),
    ("Relocation Claim", "Relocation and shifting expenses"),
    ("Other Expense Claim", "Any other reimbursable expense"),
]


def ensure_claim_category_defaults():
    if ClaimCategory.objects.exists():
        return
    for idx, (name, desc) in enumerate(DEFAULT_CLAIM_CATEGORIES):
        ClaimCategory.objects.create(
            category_name=name,
            description=desc,
            sort_order=idx + 1,
            is_active=1,
        )


def get_active_claim_categories():
    ensure_claim_category_defaults()
    return list(ClaimCategory.objects.filter(is_active=1).order_by("sort_order", "category_name"))


def get_all_claim_categories():
    ensure_claim_category_defaults()
    return ClaimCategory.objects.all().order_by("sort_order", "category_name")


def resolve_claim_type_name(category_id=None, category_name=""):
    if category_id:
        cat = ClaimCategory.objects.filter(id=category_id, is_active=1).first()
        if cat:
            return cat.category_name
    name = (category_name or "").strip()
    if name:
        return name
    return ""

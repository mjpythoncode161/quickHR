from django.db import migrations, models


DEFAULT_CATEGORIES = [
    ("Travel Claim", "Travel, taxi, flight, train expenses", 1),
    ("Fuel/Petrol Claim", "Fuel and petrol reimbursement", 2),
    ("Food/Meal Claim", "Meals during work travel or client visits", 3),
    ("Hotel/Accommodation Claim", "Hotel and lodging expenses", 4),
    ("Medical Reimbursement", "Medical bills and health expenses", 5),
    ("Telephone/Mobile Bill Claim", "Mobile and telephone bills", 6),
    ("Internet/Wi-Fi Claim", "Internet and Wi-Fi charges", 7),
    ("Office Expense Claim", "Stationery, supplies, office costs", 8),
    ("Client Entertainment Claim", "Client meetings and entertainment", 9),
    ("Training & Certification Claim", "Courses, exams, certifications", 10),
    ("Vehicle Maintenance Claim", "Vehicle service and maintenance", 11),
    ("Uniform Claim", "Uniform and workwear", 12),
    ("Relocation Claim", "Relocation and shifting expenses", 13),
    ("Other Expense Claim", "Any other reimbursable expense", 14),
]


def seed_categories(apps, schema_editor):
    ClaimCategory = apps.get_model("accounts", "ClaimCategory")
    if ClaimCategory.objects.exists():
        return
    for name, desc, order in DEFAULT_CATEGORIES:
        ClaimCategory.objects.create(
            category_name=name,
            description=desc,
            sort_order=order,
            is_active=1,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0030_hr_modules_claims"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClaimCategory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category_name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.IntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "claim_category",
                "ordering": ["sort_order", "category_name"],
                "verbose_name_plural": "Claim categories",
            },
        ),
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]

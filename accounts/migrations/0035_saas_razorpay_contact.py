# Generated migration for SaaS contact, Razorpay billing

from django.db import migrations, models


OFFICE_ADDRESS = (
    "3rd Floor, Office No. 11, Stellar Mall, beside JGCC College, "
    "Jayanagar, Vidya Nagar, Hubballi, Karnataka 580021"
)


def seed_contact_defaults(apps, schema_editor):
    SaasPlatformConfig = apps.get_model("accounts", "SaasPlatformConfig")
    cfg = SaasPlatformConfig.objects.filter(pk=1).first()
    if not cfg:
        return
    changed = False
    if not cfg.support_email or cfg.support_email == "support@quickhr.in":
        cfg.support_email = "team@indataai.in"
        changed = True
    if not cfg.support_phone:
        cfg.support_phone = "+91 6361212012"
        changed = True
    if not cfg.support_phone_2:
        cfg.support_phone_2 = "+91 9535347161"
        changed = True
    if not cfg.office_address:
        cfg.office_address = OFFICE_ADDRESS
        changed = True
    if changed:
        cfg.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0034_saas_platform"),
    ]

    operations = [
        migrations.AddField(
            model_name="saasplatformconfig",
            name="office_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="saasplatformconfig",
            name="support_phone_2",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="saaspricingplan",
            name="razorpay_plan_id",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="saasorganization",
            name="razorpay_customer_id",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="saasorganization",
            name="razorpay_subscription_id",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.CreateModel(
            name="SaasSubscription",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(blank=True, default="", max_length=200)),
                ("customer_email", models.CharField(blank=True, default="", max_length=255)),
                ("customer_phone", models.CharField(blank=True, default="", max_length=20)),
                ("company_name", models.CharField(blank=True, default="", max_length=200)),
                ("razorpay_subscription_id", models.CharField(blank=True, default="", max_length=80)),
                ("razorpay_order_id", models.CharField(blank=True, default="", max_length=80)),
                ("razorpay_payment_id", models.CharField(blank=True, default="", max_length=80)),
                ("billing_mode", models.CharField(default="subscription", max_length=20)),
                ("status", models.CharField(default="pending", max_length=20)),
                ("amount_paise", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="subscriptions",
                        to="accounts.saasorganization",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="subscriptions",
                        to="accounts.saaspricingplan",
                    ),
                ),
            ],
            options={
                "db_table": "saas_subscription",
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(seed_contact_defaults, migrations.RunPython.noop),
    ]

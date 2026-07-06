# Saas lead source field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0035_saas_razorpay_contact"),
    ]

    operations = [
        migrations.AddField(
            model_name="saascontactinquiry",
            name="source",
            field=models.CharField(
                blank=True,
                default="contact",
                max_length=30,
                help_text="contact, registration, subscription, trial",
            ),
        ),
    ]

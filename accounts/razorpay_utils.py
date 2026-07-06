"""Razorpay subscription and order helpers for QuickHR SaaS billing."""

from decimal import Decimal

from django.conf import settings


def razorpay_enabled():
    return bool(getattr(settings, "RAZORPAY_KEY_ID", "") and getattr(settings, "RAZORPAY_KEY_SECRET", ""))


def get_razorpay_key_id():
    return getattr(settings, "RAZORPAY_KEY_ID", "")


def get_razorpay_client():
    if not razorpay_enabled():
        return None
    import razorpay

    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_checkout_for_amount(amount_inr, notes=None):
    """Create a Razorpay order for a calculated INR amount."""
    client = get_razorpay_client()
    if client is None:
        raise RuntimeError("Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")

    amount_paise = int(Decimal(str(amount_inr)) * 100)
    if amount_paise < 100:
        raise ValueError("Amount must be at least ₹1")

    order_notes = {k: str(v) for k, v in (notes or {}).items()}
    order = client.order.create(
        {
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": order_notes,
        }
    )
    return {
        "mode": "order",
        "order_id": order.get("id", ""),
        "amount_paise": amount_paise,
    }


def create_checkout_for_plan(plan):
    """Legacy helper — uses plan monthly price as flat order amount."""
    return create_checkout_for_amount(
        plan.price_monthly,
        notes={"plan_key": plan.plan_key, "plan_name": plan.plan_name},
    )


def verify_webhook_signature(body, signature):
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    import razorpay

    client = get_razorpay_client()
    if client is None:
        return False
    try:
        client.utility.verify_webhook_signature(body, signature, secret)
        return True
    except Exception:
        return False

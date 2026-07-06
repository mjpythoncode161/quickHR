"""Mobile push notification API — device registration and broadcast."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.notification_service import (
    broadcast_push_to_organization,
    register_device_token,
)
from api.auth_helpers import require_api_token


@api_view(["POST"])
@require_api_token
def push_register_api(request):
    """
    Register FCM device token from mobile app.
    Body: { "device_token", "emp_id", "user_id", "platform", "device_name" }
    """
    device_token = (request.data.get("device_token") or "").strip()
    if not device_token:
        return Response(
            {"status": False, "message": "device_token is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    emp_id = (request.data.get("emp_id") or "").strip()
    user_id = request.data.get("user_id")
    try:
        user_id = int(user_id) if user_id not in (None, "") else None
    except (TypeError, ValueError):
        user_id = None

    platform = (request.data.get("platform") or "android").strip().lower()
    device_name = (request.data.get("device_name") or "").strip()

    token_obj = register_device_token(
        device_token=device_token,
        emp_id=emp_id,
        user_id=user_id,
        platform=platform,
        device_name=device_name,
    )
    return Response(
        {
            "status": True,
            "message": "Device registered for push notifications",
            "id": token_obj.id,
        }
    )


@api_view(["POST"])
@require_api_token
def push_broadcast_api(request):
    """
    Send push notification to all organization employees (or filtered).
    Body: { "title", "message", "emp_id" (optional single), "department" (optional) }
    """
    title = (request.data.get("title") or "").strip()
    message = (request.data.get("message") or "").strip()
    if not title or not message:
        return Response(
            {"status": False, "message": "title and message are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    emp_id = (request.data.get("emp_id") or "").strip() or None
    department = (request.data.get("department") or "").strip() or None

    result = broadcast_push_to_organization(
        title=title,
        message=message,
        emp_id=emp_id,
        department=department,
        event_key="api_broadcast",
    )
    return Response({"status": True, **result})

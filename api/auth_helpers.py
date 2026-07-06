from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from accounts.api_settings_utils import get_api_settings, is_valid_api_token


def _extract_token(request):
    auth = request.headers.get("Authorization") or request.META.get(
        "HTTP_AUTHORIZATION", ""
    )
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (
        request.headers.get("X-API-Token")
        or request.META.get("HTTP_X_API_TOKEN")
        or request.data.get("api_token")
        or request.POST.get("api_token")
        or request.GET.get("api_token")
        or ""
    ).strip()


def require_api_token(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        settings = get_api_settings()
        if not settings.api_enabled:
            return Response(
                {"status": False, "message": "API access is disabled"},
                status=status.HTTP_403_FORBIDDEN,
            )
        token = _extract_token(request)
        if not is_valid_api_token(token):
            return Response(
                {"status": False, "message": "Invalid or missing API token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return view_func(request, *args, **kwargs)

    return wrapper

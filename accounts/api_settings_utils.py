import secrets

from .models import ApiSettings


def get_api_settings():
    settings = ApiSettings.objects.first()
    if not settings:
        settings = ApiSettings.objects.create(
            api_token=secrets.token_urlsafe(48),
            api_enabled=1,
            biometric_enabled=1,
        )
    elif not (settings.api_token or "").strip():
        settings.api_token = secrets.token_urlsafe(48)
        settings.save(update_fields=["api_token", "updated_at"])
    return settings


def regenerate_api_token(settings=None):
    if settings is None:
        settings = get_api_settings()
    settings.api_token = secrets.token_urlsafe(48)
    settings.save(update_fields=["api_token", "updated_at"])
    return settings.api_token


def is_valid_api_token(token):
    if not token:
        return False
    settings = ApiSettings.objects.first()
    if not settings or not settings.api_enabled:
        return False
    return secrets.compare_digest(
        str(token).strip(), str(settings.api_token or "").strip()
    )

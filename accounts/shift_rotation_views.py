from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import ShiftMaster, ShiftRotationConfig
from .shift_rotation_utils import ensure_shift_rotation_defaults, get_rotation_shifts
from .shift_utils import ensure_default_shifts


@login_required(login_url="login")
@permission_required("accounts.change_empmaster", raise_exception=True)
def shift_rotation_settings(request):
    ensure_default_shifts()
    ensure_shift_rotation_defaults()
    config = ShiftRotationConfig.objects.get(pk=1)
    shifts = ShiftMaster.objects.filter(is_active=1).order_by("rotation_order", "shift_name")

    if request.method == "POST":
        config.enabled = 1 if request.POST.get("enabled") else 0
        config.cycle_days = max(1, int(request.POST.get("cycle_days", "7") or 7))
        start = request.POST.get("rotation_start_date", "").strip()
        if start:
            config.rotation_start_date = start
        config.stagger_employees = 1 if request.POST.get("stagger_employees") else 0
        config.save()

        for shift in shifts:
            order_val = request.POST.get(f"order_{shift.id}", shift.rotation_order)
            try:
                shift.rotation_order = int(order_val or 0)
            except (TypeError, ValueError):
                shift.rotation_order = 0
            shift.save(update_fields=["rotation_order"])

        # #region agent log
        try:
            import json
            import time
            from pathlib import Path

            payload = {
                "sessionId": "72a37d",
                "hypothesisId": "SR1",
                "location": "shift_rotation_views.py",
                "message": "shift_rotation_saved",
                "data": {
                    "enabled": config.enabled,
                    "cycle_days": config.cycle_days,
                    "stagger": config.stagger_employees,
                },
                "timestamp": int(time.time() * 1000),
            }
            log_path = Path(__file__).resolve().parent.parent.parent / "debug-72a37d.log"
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        # #endregion

        messages.success(request, "Shift rotation settings saved.")
        return redirect("shift_rotation_settings")

    if not config.rotation_start_date:
        config.rotation_start_date = timezone.localdate()

    return render(
        request,
        "accounts/shift_rotation_settings.html",
        {
            "config": config,
            "shifts": shifts,
            "rotation_shifts": get_rotation_shifts(),
        },
    )

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import UserProfile


def _require_role(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            profile = getattr(request.user, "profile", None)
            if profile is None or profile.role != role:
                raise PermissionDenied("No tenés permiso para ver esta página.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


patient_required = _require_role(UserProfile.Role.PATIENT)
professional_required = _require_role(UserProfile.Role.PROFESSIONAL)


def staff_required(view_func):
    """Mismo patrón que patient_required/professional_required, pero para
    el panel de administración (is_staff), que no es parte de UserProfile."""

    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("No tienes permiso para ver esta página.")
        return view_func(request, *args, **kwargs)

    return wrapped

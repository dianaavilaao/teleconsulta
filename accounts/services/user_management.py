"""
Lógica de negocio para la gestión de usuarios desde el panel de admin
propio (/panel/usuarios/), que reemplaza al Django Admin (ver
consultations/admin.py y accounts/admin.py).

Se separa de las vistas por el mismo criterio que el resto del proyecto:
aquí vive la regla de "qué significa cada rol" — admin es `is_staff` sin
UserProfile; paciente/profesional es un UserProfile con ese `role`. La
vista solo arma el formulario y llama a estas funciones.
"""

from __future__ import annotations

from django.contrib.auth.models import User

from accounts.models import UserProfile

ADMIN_ROLE = "admin"

# Universo de roles que puede asignar el panel de admin: los de UserProfile
# más "admin" (que no es un UserProfile.Role, se resuelve con is_staff).
ROLE_CHOICES = list(UserProfile.Role.choices) + [(ADMIN_ROLE, "Admin")]


def role_of(user: User) -> str:
    """Rol actual de un usuario, para mostrarlo en el panel y precargar el form de edición."""
    if user.is_staff:
        return ADMIN_ROLE
    profile = getattr(user, "profile", None)
    return profile.role if profile else ""


def create_user_with_role(*, username: str, password: str, first_name: str, role: str) -> User:
    user = User.objects.create_user(username=username, password=password, first_name=first_name)
    if role == ADMIN_ROLE:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    else:
        UserProfile.objects.create(user=user, role=role)
    return user


def update_user_role(user: User, role: str) -> User:
    """
    Ajusta is_staff/UserProfile para que `user` quede con `role`, sea cual
    sea el rol que tenía antes (admin <-> paciente <-> profesional).
    """
    if role == ADMIN_ROLE:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        UserProfile.objects.filter(user=user).delete()
        return user

    if user.is_staff:
        user.is_staff = False
        user.save(update_fields=["is_staff"])

    profile, created = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
    if not created and profile.role != role:
        profile.role = role
        profile.save(update_fields=["role"])
    return user

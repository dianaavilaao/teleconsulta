from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """
    Extiende al User nativo de Django con un rol de negocio.

    El rol "admin" no se modela aqui: se resuelve con `user.is_staff`,
    que ademas le da acceso gratis al Django Admin para crear
    teleconsultas (requisito del enunciado: "formulario simple").
    """

    class Role(models.TextChoices):
        PATIENT = "patient", "Paciente"
        PROFESSIONAL = "professional", "Profesional"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_patient(self) -> bool:
        return self.role == self.Role.PATIENT

    @property
    def is_professional(self) -> bool:
        return self.role == self.Role.PROFESSIONAL

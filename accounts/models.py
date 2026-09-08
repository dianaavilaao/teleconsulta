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
    # Solo tiene sentido para profesionales: si no está disponible, no debe
    # ofrecerse como opción al crear consultas NUEVAS (ver
    # ConsultationCreateForm). No afecta consultas ya creadas ni asignadas.
    is_available = models.BooleanField("Disponible", default=True)

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


class AccessibilityPreferences(models.Model):
    """
    Preferencias de accesibilidad atadas a la cuenta (no al navegador).

    A propósito NO vive dentro de UserProfile: UserProfile es específico
    de paciente/profesional, pero el admin (is_staff) no tiene UserProfile
    y también debe poder usar el menú de accesibilidad — cualquier rol
    logueado puede tener (o no) una fila acá.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accessibility_prefs",
    )
    font_scale = models.CharField(
        max_length=10,
        choices=[("normal", "Normal"), ("lg", "Grande"), ("xl", "Muy grande")],
        default="normal",
    )
    high_contrast = models.BooleanField(default=False)
    reduce_motion = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencias de accesibilidad"
        verbose_name_plural = "Preferencias de accesibilidad"

    def __str__(self):
        return f"Accesibilidad de {self.user.username}"

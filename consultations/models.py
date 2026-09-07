from django.conf import settings
from django.db import models
from django.utils import timezone


class Consultation(models.Model):
    """
    Entidad central del dominio. Representa una teleconsulta desde que
    el admin la crea hasta que se completa.

    Importante: nada fuera de `services/state_machine.py` deberia
    escribir directamente en `status`. Las vistas llaman al servicio,
    el servicio valida la transicion y guarda el modelo.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        WAITING_INTAKE = "waiting_intake", "Esperando intake"
        READY = "ready", "Lista"
        BOTH_PRESENT = "both_present", "Ambos presentes"
        IN_PROGRESS = "in_progress", "En curso"
        COMPLETED = "completed", "Completada"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultations_as_patient",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultations_as_professional",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="consultations_created",
        help_text="Admin que creo la teleconsulta.",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    scheduled_at = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha/hora planificada de la teleconsulta.",
    )
    patient_joined_at = models.DateTimeField(null=True, blank=True)
    professional_joined_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Briefing generado por IA (services/briefing.py) a partir del intake
    # confirmado por el paciente. Se persiste para no tener que regenerarlo
    # (y gastar cuota de API) cada vez que el profesional recarga la
    # página; el profesional decide cuándo pedir una versión nueva.
    ai_briefing = models.JSONField(null=True, blank=True)
    ai_briefing_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Consulta #{self.pk} - {self.patient} / {self.professional} ({self.status})"

    @property
    def is_finished(self) -> bool:
        return self.status == self.Status.COMPLETED


class IntakeForm(models.Model):
    """
    Formulario pre-consulta que completa el paciente en la sala de espera.
    Uno a uno con Consultation: cada consulta tiene un unico intake que
    se va editando hasta que el paciente confirma / hasta que empieza la consulta.
    """

    consultation = models.OneToOneField(
        Consultation, on_delete=models.CASCADE, related_name="intake"
    )
    reason = models.TextField("Motivo de consulta", blank=True)
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    consent_given = models.BooleanField("Consentimiento informado", default=False)
    current_medications = models.TextField("Medicamentos actuales", blank=True)
    allergies = models.TextField("Alergias", blank=True)
    # Síntomas confirmados por el paciente (sugeridos por IA en base a
    # `reason` vía services/symptom_extraction.py, editables antes de
    # confirmar). Puramente informativo: no participa en ReadinessService.
    symptoms = models.JSONField("Síntomas confirmados", default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intake"
        verbose_name_plural = "Intakes"

    def __str__(self):
        return f"Intake de consulta #{self.consultation_id}"

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = timezone.now().date()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years


class Diagnosis(models.Model):
    """
    Registro clínico interno que el profesional puede cargar una vez que
    la consulta terminó (opcional: no todas las consultas requieren uno).

    Importante — privacidad: esto NUNCA debe llegar al paciente. A
    diferencia de IntakeForm (que el paciente escribe y el profesional
    lee), Diagnosis es en un solo sentido: lo escribe el profesional y
    solo lo lee él mismo (y el admin, en modo lectura). No se serializa en
    RealtimeNotifier ni se expone en ninguna vista con @patient_required.
    """

    class ConnectionIssues(models.TextChoices):
        NONE = "none", "No hubo problemas de conexión"
        PATIENT = "patient", "Sí, por parte del paciente"
        PROFESSIONAL = "professional", "Sí, por parte del profesional"
        BOTH = "both", "Sí, por ambas partes"

    consultation = models.OneToOneField(
        Consultation, on_delete=models.CASCADE, related_name="diagnosis"
    )
    diagnosis_text = models.TextField("Diagnóstico", blank=True)
    recommendations = models.TextField("Recomendaciones", blank=True)
    follow_up_needed = models.BooleanField("Requiere seguimiento", default=False)
    follow_up_notes = models.TextField("Notas de seguimiento", blank=True)
    # Control de sesión ("Sobre la sesión" en el form): a diferencia del
    # resto de Diagnosis (que es 100% privado), esto sí lo ve el admin en
    # su panel — es información operativa (¿hay que revisar la
    # infraestructura de videollamada?), no clínica.
    connection_issues = models.CharField(
        "¿Hubo problemas de conexión?",
        max_length=20,
        choices=ConnectionIssues.choices,
        default=ConnectionIssues.NONE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="diagnoses_created",
        help_text="Profesional que registró el diagnóstico.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diagnóstico"
        verbose_name_plural = "Diagnósticos"

    def __str__(self):
        return f"Diagnóstico de consulta #{self.consultation_id}"

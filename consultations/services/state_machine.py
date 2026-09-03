"""
Máquina de estados de la Consultation.

Regla de oro del proyecto: ninguna vista escribe `consultation.status`
directamente. Todas las transiciones pasan por acá, así:

- Queda un único lugar que conoce las reglas ("¿quién puede hacer qué,
  y cuándo?").
- Cada transición válida es la oportunidad natural para notificar por
  WebSocket a quienes están mirando la sala (paciente/profesional),
  sin repetir esa lógica en cada vista.

Estados (Consultation.Status):
    scheduled -> waiting_intake -> ready -> both_present -> in_progress -> completed

Transiciones modeladas:
    patient_join(consultation)      : scheduled|waiting_intake -> waiting_intake
                                       (además marca patient_joined_at)
    submit_intake(consultation, readiness)
                                     : waiting_intake|ready -> ready (si can_start)
                                       ready -> waiting_intake (si deja de cumplir,
                                       ej. el paciente edita y saca el consentimiento)
                                       Si el profesional ya estaba presente y el
                                       intake queda "ready", se sube directo a
                                       both_present.
    professional_join(consultation) : marca professional_joined_at.
                                       Si el paciente ya está "ready", sube a
                                       both_present.
    start(consultation)             : both_present -> in_progress (solo profesional)
    complete(consultation)          : in_progress -> completed (solo profesional)
"""

from __future__ import annotations

from django.utils import timezone

from consultations.models import Consultation
from consultations.services.readiness import ReadinessResult


class InvalidTransition(Exception):
    """Se intentó una transición de estado no permitida para el estado actual."""


class ConsultationStateMachine:
    def __init__(self, consultation: Consultation, notifier=None):
        self.consultation = consultation
        # `notifier` es inyectado para desacoplar la máquina de estados de
        # Channels; en producción es RealtimeNotifier, en tests puede ser
        # un stub o None.
        self.notifier = notifier

    # ---- acciones del paciente -------------------------------------------------

    def patient_join(self) -> Consultation:
        c = self.consultation
        if c.status not in (Consultation.Status.SCHEDULED, Consultation.Status.WAITING_INTAKE):
            # Reingresar a una consulta ya avanzada no es un error: es un
            # no-op para no romper un refresh de página.
            return c

        if not c.patient_joined_at:
            c.patient_joined_at = timezone.now()

        if c.status == Consultation.Status.SCHEDULED:
            c.status = Consultation.Status.WAITING_INTAKE

        c.save()
        self._notify()
        return c

    def submit_intake(self, readiness: ReadinessResult) -> Consultation:
        c = self.consultation
        if c.status in (Consultation.Status.IN_PROGRESS, Consultation.Status.COMPLETED):
            raise InvalidTransition(
                "No se puede modificar el intake una vez iniciada o completada la consulta."
            )

        if readiness.can_start:
            if c.professional_joined_at:
                c.status = Consultation.Status.BOTH_PRESENT
            else:
                c.status = Consultation.Status.READY
        else:
            # Si el paciente edita el intake y ahora falta algo bloqueante,
            # retrocedemos el estado (ej. desmarcó el consentimiento).
            c.status = Consultation.Status.WAITING_INTAKE

        c.save()
        self._notify()
        return c

    # ---- acciones del profesional ----------------------------------------------

    def professional_join(self) -> Consultation:
        c = self.consultation
        if c.status == Consultation.Status.COMPLETED:
            return c

        if not c.professional_joined_at:
            c.professional_joined_at = timezone.now()

        if c.status == Consultation.Status.READY:
            c.status = Consultation.Status.BOTH_PRESENT

        c.save()
        self._notify()
        return c

    def start(self) -> Consultation:
        c = self.consultation
        if c.status != Consultation.Status.BOTH_PRESENT:
            raise InvalidTransition(
                "Solo se puede iniciar la consulta cuando paciente y profesional "
                "están presentes y el intake está listo."
            )
        c.status = Consultation.Status.IN_PROGRESS
        c.started_at = timezone.now()
        c.save()
        self._notify()
        return c

    def complete(self) -> Consultation:
        c = self.consultation
        if c.status != Consultation.Status.IN_PROGRESS:
            raise InvalidTransition("Solo se puede finalizar una consulta que está en curso.")
        c.status = Consultation.Status.COMPLETED
        c.completed_at = timezone.now()
        c.save()
        self._notify()
        return c

    # ---- internals ---------------------------------------------------------

    def _notify(self):
        if self.notifier is not None:
            self.notifier.broadcast_state(self.consultation)

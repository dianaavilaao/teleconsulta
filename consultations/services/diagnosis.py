"""
Servicio de dominio para el registro de diagnóstico post-consulta.

Sigue el mismo espíritu que `state_machine.py`: concentra en un único
lugar la regla de negocio ("¿cuándo se puede escribir un diagnóstico?"),
para que la vista no valide nada de negocio por su cuenta — solo llama al
servicio y captura la excepción de dominio si corresponde.

Privacidad: este servicio solo guarda datos. No dispara ningún broadcast
por WebSocket — a propósito, porque `RealtimeNotifier` transmite a un
grupo compartido entre paciente y profesional, y el diagnóstico es un
registro interno que el paciente nunca debe recibir.
"""

from __future__ import annotations

from consultations.models import Consultation, Diagnosis


class DiagnosisNotAllowed(Exception):
    """Se intentó crear/editar un diagnóstico fuera de una consulta completada."""


class DiagnosisService:
    @staticmethod
    def save(consultation: Consultation, professional, data: dict) -> Diagnosis:
        if consultation.status != Consultation.Status.COMPLETED:
            raise DiagnosisNotAllowed(
                "Solo se puede registrar un diagnóstico una vez que la consulta está completada."
            )

        diagnosis, _ = Diagnosis.objects.get_or_create(consultation=consultation)
        diagnosis.diagnosis_text = (data.get("diagnosis_text") or "").strip()
        diagnosis.recommendations = (data.get("recommendations") or "").strip()
        diagnosis.follow_up_needed = bool(data.get("follow_up_needed"))
        diagnosis.follow_up_notes = (data.get("follow_up_notes") or "").strip()
        diagnosis.created_by = professional
        diagnosis.save()
        return diagnosis

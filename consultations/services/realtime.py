"""
Puente entre el dominio y Channels.

Se separa en su propio módulo para que `state_machine.py` no dependa
directamente de `channels` (facilita testear la máquina de estados sin
levantar un channel layer).
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.utils.formats import date_format

from consultations.services.presentation import build_status_steps
from consultations.services.readiness import ReadinessService

ADMIN_GROUP_NAME = "admin_consultations"


def group_name_for(consultation_id: int) -> str:
    return f"consultation_{consultation_id}"


def user_group_name(user_id: int) -> str:
    return f"user_consultations_{user_id}"


class RealtimeNotifier:
    def broadcast_state(self, consultation) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            group_name_for(consultation.id),
            {"type": "consultation.update", "payload": self._serialize(consultation)},
        )
        # Mismo evento, canal aparte: el panel de admin (/panel/consultas/)
        # muestra muchas consultas a la vez, no una sola — no tiene sentido
        # unirlo al grupo por-consulta de arriba. Va en un grupo fijo propio.
        async_to_sync(channel_layer.group_send)(
            ADMIN_GROUP_NAME,
            {"type": "admin.update", "payload": self._serialize_admin(consultation)},
        )

    def _serialize(self, consultation) -> dict:
        # OJO: consultas explícitas (no `consultation.intake`/`.diagnosis`)
        # a propósito. `patient_join`/`professional_join` ya llaman a este
        # método antes de que la vista guarde el intake/diagnóstico del
        # request (ver ConsultationStateMachine): si usáramos el accessor
        # de relación inversa, Django cachea ese primer valor (vacío) en la
        # instancia de `consultation`, y una notificación posterior en el
        # mismo request (ej. `submit_intake`, ya con el intake actualizado
        # en la base) seguía devolviendo esa foto vieja porque leía el
        # cache en vez de la base — el estado llegaba bien por WebSocket,
        # pero motivo/edad/medicamentos/alergias/blockers se quedaban
        # pisados hasta refrescar la página a mano.
        from consultations.models import Diagnosis, IntakeForm

        readiness = None
        intake = IntakeForm.objects.filter(consultation=consultation).first()
        if intake is not None:
            readiness = ReadinessService().evaluate(intake).to_dict()

        # Diagnosis: mismo criterio de privacidad por campo que
        # patient_history_detail (ver views.py) — nunca se manda
        # follow_up_notes ni connection_issues por este canal, porque este
        # grupo lo escucha también el paciente.
        diagnosis = Diagnosis.objects.filter(consultation=consultation).first()
        diagnosis_payload = None
        if diagnosis is not None:
            diagnosis_payload = {
                "diagnosis_text": diagnosis.diagnosis_text,
                "recommendations": diagnosis.recommendations,
                "follow_up_needed": diagnosis.follow_up_needed,
            }

        return {
            "id": consultation.id,
            "status": consultation.status,
            "status_display": consultation.get_status_display(),
            "patient_joined": consultation.patient_joined_at is not None,
            "professional_joined": consultation.professional_joined_at is not None,
            "readiness": readiness,
            "steps": build_status_steps(consultation.status),
            "symptoms": intake.symptoms if intake is not None else [],
            "intake": {
                "reason": intake.reason,
                "age": intake.age,
                "current_medications": intake.current_medications,
                "allergies": intake.allergies,
                "consent_given": intake.consent_given,
            }
            if intake is not None
            else None,
            "diagnosis": diagnosis_payload,
        }

    def notify_new_consultation(self, consultation) -> None:
        """
        El admin crea una consulta (panel_consultation_create) y tanto el
        paciente como el profesional pueden estar mirando SU LISTA en ese
        momento (/paciente/ o /profesional/) — todavía no entraron a
        ninguna sala puntual, así que el grupo por-consulta (group_name_for)
        no les sirve de nada. Por eso este es un grupo por-usuario aparte.
        """
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        payload = {
            "id": consultation.id,
            "patient_name": consultation.patient.get_full_name() or consultation.patient.username,
            "professional_name": consultation.professional.get_full_name() or consultation.professional.username,
            "scheduled_at_display": date_format(timezone.localtime(consultation.scheduled_at), "DATETIME_FORMAT"),
            "status_display": consultation.get_status_display(),
        }
        for user_id in (consultation.patient_id, consultation.professional_id):
            async_to_sync(channel_layer.group_send)(
                user_group_name(user_id),
                {"type": "consultation.created", "payload": payload},
            )

    def _serialize_admin(self, consultation) -> dict:
        """
        Versión resumida para /panel/consultas/: ni el paciente ni el
        profesional escuchan este grupo, así que acá no hace falta cuidar
        qué campos del diagnóstico van — igual solo mandamos lo que el
        template ya muestra (registrado/no, y si hubo problemas de conexión).
        """
        from consultations.models import Diagnosis

        diagnosis = Diagnosis.objects.filter(consultation=consultation).first()
        return {
            "id": consultation.id,
            "status": consultation.status,
            "status_display": consultation.get_status_display(),
            "diagnosis_registered": diagnosis is not None,
            "connection_issues": diagnosis.connection_issues if diagnosis is not None else None,
        }

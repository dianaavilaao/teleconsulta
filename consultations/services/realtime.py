"""
Puente entre el dominio y Channels.

Se separa en su propio módulo para que `state_machine.py` no dependa
directamente de `channels` (facilita testear la máquina de estados sin
levantar un channel layer).
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from consultations.services.presentation import build_status_steps
from consultations.services.readiness import ReadinessService


def group_name_for(consultation_id: int) -> str:
    return f"consultation_{consultation_id}"


class RealtimeNotifier:
    def broadcast_state(self, consultation) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        payload = self._serialize(consultation)
        async_to_sync(channel_layer.group_send)(
            group_name_for(consultation.id),
            {"type": "consultation.update", "payload": payload},
        )

    def _serialize(self, consultation) -> dict:
        readiness = None
        intake = getattr(consultation, "intake", None)
        if intake is not None:
            readiness = ReadinessService().evaluate(intake).to_dict()

        return {
            "id": consultation.id,
            "status": consultation.status,
            "status_display": consultation.get_status_display(),
            "patient_joined": consultation.patient_joined_at is not None,
            "professional_joined": consultation.professional_joined_at is not None,
            "readiness": readiness,
            "steps": build_status_steps(consultation.status),
        }

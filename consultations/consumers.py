import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from consultations.services.realtime import ADMIN_GROUP_NAME, group_name_for, user_group_name


class ConsultationConsumer(AsyncWebsocketConsumer):
    """
    Un consumer por sala de consulta. Tanto la vista del paciente como la
    del profesional abren un socket a `/ws/consultations/<id>/` y reciben
    el mismo evento cuando el estado cambia, sin necesidad de polling.

    El payload incluye valores del intake y del diagnóstico (ver
    RealtimeNotifier._serialize), así que no alcanza con estar logueado
    para conectarse: hay que ser el paciente, el profesional de ESA
    consulta puntual, o staff — si no, cerramos la conexión.
    """

    async def connect(self):
        self.consultation_id = self.scope["url_route"]["kwargs"]["consultation_id"]
        self.group_name = group_name_for(self.consultation_id)

        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return

        if not await self._user_belongs_to_consultation(user):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Handler invocado por group_send({"type": "consultation.update", ...})
    async def consultation_update(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    @database_sync_to_async
    def _user_belongs_to_consultation(self, user):
        from consultations.models import Consultation

        if user.is_staff:
            return True
        return Consultation.objects.filter(pk=self.consultation_id).filter(
            Q(patient=user) | Q(professional=user)
        ).exists()


class AdminConsultationsConsumer(AsyncWebsocketConsumer):
    """
    Canal único y compartido para /panel/consultas/ — a diferencia de
    ConsultationConsumer, no es por-consulta: el admin ve muchas consultas
    a la vez en una lista, así que todas empujan al mismo grupo fijo
    (ADMIN_GROUP_NAME) y el JS de la lista actualiza la fila que
    corresponda según el `id` que venga en cada mensaje.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated or not user.is_staff:
            await self.close()
            return

        await self.channel_layer.group_add(ADMIN_GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ADMIN_GROUP_NAME, self.channel_name)

    async def admin_update(self, event):
        await self.send(text_data=json.dumps(event["payload"]))


class UserConsultationsConsumer(AsyncWebsocketConsumer):
    """
    Un canal por usuario, no por consulta: lo usan /paciente/ y
    /profesional/ (las listas, antes de entrar a una sala puntual) para
    enterarse en el momento si el admin les crea una consulta nueva. El
    grupo sale del propio usuario logueado (`user.id`), nunca de un
    parámetro en la URL, así que no hace falta validar pertenencia: cada
    uno solo puede terminar en su propio grupo.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.group_name = user_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def consultation_created(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

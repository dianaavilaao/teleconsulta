import json

from channels.generic.websocket import AsyncWebsocketConsumer

from consultations.services.realtime import group_name_for


class ConsultationConsumer(AsyncWebsocketConsumer):
    """
    Un consumer por sala de consulta. Tanto la vista del paciente como la
    del profesional abren un socket a `/ws/consultations/<id>/` y reciben
    el mismo evento cuando el estado cambia, sin necesidad de polling.
    """

    async def connect(self):
        self.consultation_id = self.scope["url_route"]["kwargs"]["consultation_id"]
        self.group_name = group_name_for(self.consultation_id)

        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
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

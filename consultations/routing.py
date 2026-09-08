from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/consultations/(?P<consultation_id>\d+)/$",
        consumers.ConsultationConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/admin/consultations/$",
        consumers.AdminConsultationsConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/my-consultations/$",
        consumers.UserConsultationsConsumer.as_asgi(),
    ),
]

"""
ASGI config for the Teleconsulta project.

Sirve HTTP normal con Django y WebSockets con Channels sobre el mismo
proceso (monolito), enrutando por protocolo.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

import consultations.routing  # noqa: E402  (después de get_asgi_application)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(consultations.routing.websocket_urlpatterns)
        ),
    }
)

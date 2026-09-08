"""
Django settings for config project (Teleconsulta).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables de entorno desde .env (no versionado, ver .gitignore) si
# existe — ej. GROQ_API_KEY para las funciones de IA. No pisa variables que
# ya estén seteadas en el entorno real (override=False por defecto).
load_dotenv(BASE_DIR / ".env")

# El fallback solo existe para que el proyecto ande "out of the box" en
# desarrollo sin depender de un .env; nunca usar este valor si el proyecto
# se llega a desplegar de verdad — ahí SECRET_KEY tiene que venir del .env
# (o del entorno real) con una clave generada aparte, nunca la del fallback
# ni la vieja que estaba hardcodeada acá (quedó expuesta en el historial de
# git, así que se considera comprometida).
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-only-fallback-do-not-use-in-production"
)

DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    # Tiene que ir primero (antes que staticfiles): así "daphne" reemplaza
    # el comando runserver de Django por uno que sirve ASGI de verdad. Sin
    # esto, `manage.py runserver` corre el servidor WSGI de siempre, que no
    # entiende WebSockets — la app funciona por HTTP pero el tiempo real
    # (los cambios de estado que se ven sin recargar) no llega.
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "accounts",
    "consultations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.accessibility",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Channel layer: InMemory alcanza para la demo / un solo proceso.
# Para multi-proceso en producción se reemplazaría por channels_redis.core.RedisChannelLayer.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


# Database
# SQLite por defecto para que el proyecto corra sin dependencias externas.
# Se puede apuntar a Postgres seteando la variable de entorno DATABASE_URL
# (ver README) sin tocar código.
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"])}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "consultations:home"
LOGOUT_REDIRECT_URL = "login"

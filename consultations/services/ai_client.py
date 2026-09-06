"""
Cliente delgado para la API de Groq (formato compatible con OpenAI chat
completions). Se mantiene separado de los servicios de dominio
(`symptom_extraction.py`, `briefing.py`) para que ellos no sepan nada de
HTTP, API keys ni el formato específico de Groq — solo piden "completame
este prompt" y reciben texto de vuelta.

Cualquier falla (sin API key, error de red, timeout, rate limit, respuesta
inesperada) se traduce a `AIServiceUnavailable`, para que las capas de
arriba puedan degradar sin romper el flujo principal.
"""

from __future__ import annotations

import os

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq retira/renueva modelos con frecuencia; "llama-3.3-70b-versatile" (el
# sugerido originalmente) dejó de existir en su catálogo y la API empezó a
# responder 404 "model_not_found" — confirmado contra GET /v1/models. Si
# este modelo también se retira en el futuro, GET /v1/models (con la key
# activa) devuelve el catálogo vigente para elegir un reemplazo.
GROQ_MODEL = "openai/gpt-oss-20b"
REQUEST_TIMEOUT = 15


class AIServiceUnavailable(Exception):
    """La IA no pudo responder (sin API key, error de red, rate limit, respuesta inválida, etc.)."""


class GroqClient:
    def __init__(self, api_key: str | None = None, timeout: int = REQUEST_TIMEOUT):
        self.api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY")
        self.timeout = timeout

    def complete(self, system_prompt: str, user_prompt: str, *, json_mode: bool = False) -> str:
        if not self.api_key:
            raise AIServiceUnavailable(
                "GROQ_API_KEY no está configurada. Definila como variable de entorno para "
                "habilitar las funciones de IA."
            )

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AIServiceUnavailable(f"No se pudo contactar al servicio de IA: {exc}") from exc

        if response.status_code == 429:
            raise AIServiceUnavailable(
                "Se alcanzó el límite de uso del servicio de IA (rate limit). Probá de nuevo en unos minutos."
            )

        if response.status_code >= 400:
            raise AIServiceUnavailable(
                f"El servicio de IA respondió con un error ({response.status_code})."
            )

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError) as exc:
            raise AIServiceUnavailable("El servicio de IA devolvió una respuesta inesperada.") from exc

"""
Extrae síntomas mencionados en el motivo de consulta (texto libre del
paciente) usando la IA, guiada por el vocabulario canónico de
`symptom_vocabulary.py`.

Es puramente informativo/aditivo: cualquier falla (de red, de la API, o de
parseo de la respuesta) se traduce a `AIServiceUnavailable` — la misma
excepción que usa `ai_client.py` — para que la vista la capture y el
paciente pueda seguir completando su intake sin síntomas sugeridos.
"""

from __future__ import annotations

import json
import re

from .ai_client import AIServiceUnavailable, GroqClient
from .symptom_vocabulary import SYMPTOM_VOCABULARY

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _vocabulary_reference() -> str:
    lines = []
    for term, synonyms in SYMPTOM_VOCABULARY.items():
        if synonyms:
            lines.append(f"- {term} (sinónimos: {', '.join(synonyms)})")
        else:
            lines.append(f"- {term}")
    return "\n".join(lines)


_SYSTEM_PROMPT = f"""Eres un asistente clínico que identifica síntomas mencionados en un texto \
escrito por un paciente, en español. Usa como referencia (sin forzar coincidencia exacta) este \
vocabulario estandarizado de MedlinePlus:

{_vocabulary_reference()}

Reglas:
- Devuelve SOLO un JSON válido, sin texto adicional, con la forma: {{"symptoms": ["...", "..."]}}
- Prefiere los términos del vocabulario de referencia cuando el texto describa algo equivalente.
- Si el texto describe un síntoma que no está en el vocabulario, inclúyelo igual con una \
descripción breve en español.
- No inventes síntomas que no estén mencionados ni implícitos en el texto.
- Si no se menciona ningún síntoma, devuelve {{"symptoms": []}}.
"""


class SymptomExtractionService:
    def __init__(self, client: GroqClient | None = None):
        self.client = client or GroqClient()

    def extract(self, reason: str) -> list[str]:
        content = self.client.complete(_SYSTEM_PROMPT, reason, json_mode=True)
        return self._parse(content)

    def _parse(self, content: str) -> list[str]:
        match = _JSON_BLOCK_RE.search(content)
        if not match:
            raise AIServiceUnavailable("No se pudo interpretar la respuesta de la IA como síntomas.")

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise AIServiceUnavailable("No se pudo interpretar la respuesta de la IA como síntomas.") from exc

        symptoms = parsed.get("symptoms") if isinstance(parsed, dict) else None
        if not isinstance(symptoms, list):
            raise AIServiceUnavailable("La IA no devolvió una lista de síntomas válida.")

        return [str(s).strip() for s in symptoms if str(s).strip()]

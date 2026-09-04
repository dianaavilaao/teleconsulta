"""
Genera el briefing pre-consulta para el profesional a partir del intake que
ya confirmó el paciente (motivo, síntomas, edad, medicamentos, alergias).

Igual que `symptom_extraction.py`: cualquier falla se traduce a
`AIServiceUnavailable` para que la vista la capture y el profesional vea un
mensaje de error en vez de romper la página.
"""

from __future__ import annotations

import json
import re

from .ai_client import AIServiceUnavailable, GroqClient

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_PROMPT = """Eres un asistente clínico que prepara un briefing breve para un profesional \
de la salud antes de una teleconsulta, a partir de los datos que cargó el paciente. Responde en \
español.

Devuelve SOLO un JSON válido, sin texto adicional, con esta forma exacta:
{
  "summary": "síntesis breve del caso en 2-3 líneas",
  "topics_to_explore": ["tema a profundizar en la anamnesis 1", "..."],
  "suggested_questions": ["pregunta sugerida 1", "..."],
  "warning_signs": ["posible señal de alerta a explorar 1", "..."],
  "missing_or_inconsistent_data": ["dato faltante o inconsistente 1", "..."]
}

Básate únicamente en los datos provistos, no inventes información. Si un dato relevante (fecha \
de nacimiento/edad, medicamentos, alergias) no fue informado, menciónalo en \
"missing_or_inconsistent_data". Este briefing es material de apoyo: nunca reemplaza el juicio \
clínico del profesional.
"""


class BriefingService:
    def __init__(self, client: GroqClient | None = None):
        self.client = client or GroqClient()

    def generate(self, intake) -> dict:
        content = self.client.complete(_SYSTEM_PROMPT, self._build_prompt(intake), json_mode=True)
        return self._parse(content)

    def _build_prompt(self, intake) -> str:
        symptoms = ", ".join(intake.symptoms) if intake.symptoms else "(ninguno confirmado)"
        age = intake.age if intake.age is not None else "(no informada)"
        return (
            f"Motivo de consulta: {intake.reason or '(no informado)'}\n"
            f"Síntomas confirmados por el paciente: {symptoms}\n"
            f"Edad: {age}\n"
            f"Medicamentos actuales: {intake.current_medications or '(no informado)'}\n"
            f"Alergias: {intake.allergies or '(no informado)'}\n"
        )

    def _parse(self, content: str) -> dict:
        match = _JSON_BLOCK_RE.search(content)
        if not match:
            raise AIServiceUnavailable("No se pudo interpretar la respuesta de la IA como briefing.")

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise AIServiceUnavailable("No se pudo interpretar la respuesta de la IA como briefing.") from exc

        if not isinstance(parsed, dict):
            raise AIServiceUnavailable("La IA no devolvió un briefing con el formato esperado.")

        list_keys = [
            "topics_to_explore",
            "suggested_questions",
            "warning_signs",
            "missing_or_inconsistent_data",
        ]
        result = {"summary": str(parsed.get("summary") or "").strip()}
        for key in list_keys:
            value = parsed.get(key)
            result[key] = [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []
        return result

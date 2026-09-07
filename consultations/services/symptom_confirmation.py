"""
Validación compartida para la lista final de síntomas que confirma el
paciente (sugeridos por IA que sigan seleccionados + agregados
manualmente desde el vocabulario + "Otro"). La usan tanto el flujo
principal —guardar el intake completo en un único POST, ver
views.waiting_room— como el endpoint standalone
POST /paciente/<id>/confirmar-sintomas/ (no reimplementar esta regla en
dos lugares distintos).
"""

from __future__ import annotations

MAX_SYMPTOMS = 10


def validate_symptoms(symptoms) -> tuple[list[str], str | None]:
    """
    Valida y limpia una lista de síntomas ya parseada (no una cadena
    JSON). Devuelve (lista_limpia, error) — si hay error, el llamador no
    debe guardar nada.
    """
    if not isinstance(symptoms, list) or not all(isinstance(s, str) for s in symptoms):
        return [], "Formato de síntomas inválido."

    cleaned = [s.strip() for s in symptoms if s.strip()]
    if len(cleaned) > MAX_SYMPTOMS:
        return [], f"Máximo {MAX_SYMPTOMS} síntomas permitidos."

    return cleaned, None

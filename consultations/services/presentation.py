"""
Helper puramente de presentación: traduce el status actual de una
Consultation en una lista de pasos (done/current/upcoming) para dibujar
el stepper visual.

Vive separado de las vistas y de la máquina de estados a propósito: no
es una regla de negocio, es solo "cómo se ve" el estado — si mañana
cambia el diseño del stepper, no debería tocar `state_machine.py`.
"""

from consultations.models import Consultation


def build_status_steps(current_status: str) -> list[dict]:
    order = list(Consultation.Status)
    current_index = next(i for i, s in enumerate(order) if s.value == current_status)

    steps = []
    for i, status in enumerate(order):
        if i < current_index:
            state = "done"
        elif i == current_index:
            state = "current"
        else:
            state = "upcoming"
        steps.append({"code": status.value, "label": status.label, "state": state})
    return steps

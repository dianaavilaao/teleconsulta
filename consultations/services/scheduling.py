"""
Servicio de dominio para evitar choques de horario al agendar una
consulta. Mismo patrón que `diagnosis.py`/`eligibility.py`: la regla
("nadie puede tener dos consultas dentro de la misma ventana de
exclusividad") vive acá, no en el form.

`CONSULTATION_DURATION_MINUTES` se comparte con el Cambio 3 (ventana de
intake) — no lo dupliques, importalo desde acá.
"""

from __future__ import annotations

import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone

from consultations.models import Consultation

CONSULTATION_DURATION_MINUTES = 30


class SchedulingConflict(Exception):
    """Alguna de las personas involucradas ya tiene una consulta agendada dentro de la ventana de exclusividad."""


def find_conflicts(
    person, scheduled_at: datetime.datetime, exclude_consultation_id: int | None = None
) -> QuerySet:
    """
    Consultas donde `person` participa (como paciente O profesional) con
    `scheduled_at` dentro de +/- CONSULTATION_DURATION_MINUTES del horario
    que se está por agendar.
    """
    window = datetime.timedelta(minutes=CONSULTATION_DURATION_MINUTES)
    qs = Consultation.objects.filter(
        Q(patient=person) | Q(professional=person),
        scheduled_at__gte=scheduled_at - window,
        scheduled_at__lte=scheduled_at + window,
    )
    if exclude_consultation_id is not None:
        qs = qs.exclude(pk=exclude_consultation_id)
    return qs


def _describe_conflict(person, conflict: Consultation) -> str:
    name = person.get_full_name() or person.username
    hour = timezone.localtime(conflict.scheduled_at).strftime("%H:%M")
    return f"ya tiene una consulta agendada a las {hour} que se solapa con este horario."


def assert_no_scheduling_conflict(
    patient, professional, scheduled_at: datetime.datetime, exclude_consultation_id: int | None = None
) -> None:
    patient_conflict = find_conflicts(patient, scheduled_at, exclude_consultation_id).order_by(
        "scheduled_at"
    ).first()
    if patient_conflict:
        raise SchedulingConflict(
            f"El paciente {patient.get_full_name() or patient.username} "
            + _describe_conflict(patient, patient_conflict)
        )

    professional_conflict = find_conflicts(professional, scheduled_at, exclude_consultation_id).order_by(
        "scheduled_at"
    ).first()
    if professional_conflict:
        raise SchedulingConflict(
            f"El profesional {professional.get_full_name() or professional.username} "
            + _describe_conflict(professional, professional_conflict)
        )

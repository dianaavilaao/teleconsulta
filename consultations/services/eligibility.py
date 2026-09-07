"""
Servicio de dominio para validar la elegibilidad del paciente a partir de
su fecha de nacimiento.

Mismo patrón que `state_machine.py` (`InvalidTransition`) y
`diagnosis.py` (`DiagnosisNotAllowed`): la regla de negocio ("¿el paciente
es mayor de edad?") vive aquí, no en el form ni en las vistas. El form
(`IntakeSubmitForm.clean_birth_date`) solo llama a `validate_patient_age`
y traduce la excepción de dominio a un error de formulario.
"""

from __future__ import annotations

import datetime

from django.utils import timezone

MIN_PATIENT_AGE = 18


class UnderageError(Exception):
    """La fecha de nacimiento corresponde a una persona menor de MIN_PATIENT_AGE años."""


def calculate_age(birth_date: datetime.date) -> int:
    today = timezone.now().date()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def validate_patient_age(birth_date: datetime.date) -> None:
    if calculate_age(birth_date) < MIN_PATIENT_AGE:
        raise UnderageError(f"El paciente debe ser mayor de {MIN_PATIENT_AGE} años.")

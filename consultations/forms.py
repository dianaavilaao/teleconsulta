from django import forms

from accounts.models import UserProfile
from .models import Consultation, IntakeForm
from .services.eligibility import UnderageError, validate_patient_age
from .services.scheduling import SchedulingConflict, assert_no_scheduling_conflict


class ConsultationCreateForm(forms.ModelForm):
    """Formulario simple usado por el admin (vía Django Admin) para crear una teleconsulta."""

    # Declarado explícitamente (no solo vía Meta.widgets) para que el admin
    # no lo reemplace por SplitDateTimeField: ese form_class espera un widget
    # multivalor (fecha + hora por separado) y rompe al combinarse con el
    # input HTML5 "datetime-local" de un solo valor que usamos aquí.
    scheduled_at = forms.DateTimeField(
        label="Fecha y hora",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = Consultation
        fields = ["patient", "professional", "scheduled_at"]
        labels = {
            "patient": "Paciente",
            "professional": "Profesional",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = self.fields["patient"].queryset.filter(
            profile__role=UserProfile.Role.PATIENT
        )
        self.fields["patient"].empty_label = "Selecciona un paciente"
        self.fields["professional"].queryset = self.fields["professional"].queryset.filter(
            profile__role=UserProfile.Role.PROFESSIONAL,
            profile__is_available=True,
        )
        self.fields["professional"].empty_label = "Selecciona un profesional"

    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get("patient")
        professional = cleaned_data.get("professional")
        scheduled_at = cleaned_data.get("scheduled_at")

        # Solo tiene sentido chequear el choque de horario si los tres
        # campos ya son válidos por su cuenta (si alguno falló, ya hay un
        # error de campo y no hace falta agregar ruido acá).
        if patient and professional and scheduled_at:
            try:
                assert_no_scheduling_conflict(patient, professional, scheduled_at)
            except SchedulingConflict as exc:
                raise forms.ValidationError(str(exc))

        return cleaned_data


class IntakeSubmitForm(forms.ModelForm):
    """Formulario pre-consulta que completa el paciente en la sala de espera."""

    class Meta:
        model = IntakeForm
        fields = [
            "reason",
            "birth_date",
            "consent_given",
            "current_medications",
            "allergies",
        ]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3, "class": "w-full border rounded px-3 py-2"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "w-full border rounded px-3 py-2"}),
            "current_medications": forms.Textarea(attrs={"rows": 2, "class": "w-full border rounded px-3 py-2"}),
            "allergies": forms.Textarea(attrs={"rows": 2, "class": "w-full border rounded px-3 py-2"}),
            "consent_given": forms.CheckboxInput(attrs={"class": "mr-2"}),
        }
        labels = {
            "consent_given": "Doy mi consentimiento informado para la teleconsulta",
        }

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get("birth_date")
        # Vacío no es error acá: ReadinessService ya lo trata como warning
        # (no bloqueante), y esa regla no se toca ni se duplica.
        if not birth_date:
            return birth_date

        try:
            validate_patient_age(birth_date)
        except UnderageError:
            raise forms.ValidationError(
                "Debés ingresar una fecha de nacimiento correspondiente a una persona mayor de 18 años."
            )

        return birth_date

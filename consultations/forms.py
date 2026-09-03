from django import forms

from accounts.models import UserProfile
from .models import Consultation, IntakeForm


class ConsultationCreateForm(forms.ModelForm):
    """Formulario simple usado por el admin (vía Django Admin) para crear una teleconsulta."""

    class Meta:
        model = Consultation
        fields = ["patient", "professional", "scheduled_at"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = self.fields["patient"].queryset.filter(
            profile__role=UserProfile.Role.PATIENT
        )
        self.fields["professional"].queryset = self.fields["professional"].queryset.filter(
            profile__role=UserProfile.Role.PROFESSIONAL
        )


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

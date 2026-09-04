from django.urls import path

from . import views

app_name = "consultations"

urlpatterns = [
    path("", views.home, name="home"),
    path("paciente/", views.patient_list, name="patient_list"),
    path("paciente/<int:consultation_id>/", views.waiting_room, name="waiting_room"),
    path(
        "paciente/<int:consultation_id>/analizar-sintomas/",
        views.analyze_symptoms,
        name="analyze_symptoms",
    ),
    path(
        "paciente/<int:consultation_id>/confirmar-sintomas/",
        views.confirm_symptoms,
        name="confirm_symptoms",
    ),
    path(
        "paciente/<int:consultation_id>/vocabulario-sintomas/",
        views.symptom_vocabulary_list,
        name="symptom_vocabulary_list",
    ),
    path("profesional/", views.professional_list, name="professional_list"),
    path("profesional/<int:consultation_id>/", views.professional_room, name="professional_room"),
    path(
        "profesional/<int:consultation_id>/generar-briefing/",
        views.generate_briefing,
        name="generate_briefing",
    ),
]

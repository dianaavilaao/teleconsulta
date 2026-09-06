from django.urls import path

from . import views

app_name = "consultations"

urlpatterns = [
    path("", views.home, name="home"),
    path("paciente/", views.patient_list, name="patient_list"),
    path(
        "paciente/<int:consultation_id>/historial/",
        views.patient_history_detail,
        name="patient_history_detail",
    ),
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
    path("profesional/disponibilidad/", views.toggle_availability, name="toggle_availability"),
    path("profesional/<int:consultation_id>/", views.professional_room, name="professional_room"),
    path(
        "profesional/<int:consultation_id>/generar-briefing/",
        views.generate_briefing,
        name="generate_briefing",
    ),
    path(
        "profesional/<int:consultation_id>/diagnostico/",
        views.save_diagnosis,
        name="save_diagnosis",
    ),
    path("panel/consultas/", views.panel_consultation_list, name="panel_consultation_list"),
    path(
        "panel/consultas/nueva/",
        views.panel_consultation_create,
        name="panel_consultation_create",
    ),
]

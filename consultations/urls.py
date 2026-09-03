from django.urls import path

from . import views

app_name = "consultations"

urlpatterns = [
    path("", views.home, name="home"),
    path("paciente/", views.patient_list, name="patient_list"),
    path("paciente/<int:consultation_id>/", views.waiting_room, name="waiting_room"),
    path("profesional/", views.professional_list, name="professional_list"),
    path("profesional/<int:consultation_id>/", views.professional_room, name="professional_room"),
]

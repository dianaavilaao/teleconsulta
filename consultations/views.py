from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import patient_required, professional_required

from .forms import IntakeSubmitForm
from .models import Consultation, IntakeForm
from .services.presentation import build_status_steps
from .services.readiness import ReadinessService
from .services.realtime import RealtimeNotifier
from .services.state_machine import ConsultationStateMachine, InvalidTransition


def _state_machine(consultation: Consultation) -> ConsultationStateMachine:
    return ConsultationStateMachine(consultation, notifier=RealtimeNotifier())


@login_required
def home(request):
    """Redirige segun el rol: admins van al Django Admin, el resto a su lista."""
    if request.user.is_staff:
        return redirect("admin:index")

    profile = getattr(request.user, "profile", None)
    if profile and profile.is_patient:
        return redirect("consultations:patient_list")
    if profile and profile.is_professional:
        return redirect("consultations:professional_list")

    messages.error(request, "Tu usuario no tiene un rol asignado. Contacta al administrador.")
    return redirect("login")


@patient_required
def patient_list(request):
    consultations = Consultation.objects.filter(patient=request.user).select_related("professional")
    return render(request, "consultations/patient_list.html", {"consultations": consultations})


@professional_required
def professional_list(request):
    consultations = Consultation.objects.filter(professional=request.user).select_related("patient")
    return render(request, "consultations/professional_list.html", {"consultations": consultations})


@patient_required
def waiting_room(request, consultation_id):
    consultation = get_object_or_404(Consultation, pk=consultation_id, patient=request.user)
    intake, _ = IntakeForm.objects.get_or_create(consultation=consultation)

    sm = _state_machine(consultation)
    sm.patient_join()  # idempotente: no-op si ya esta avanzada

    if request.method == "POST":
        form = IntakeSubmitForm(request.POST, instance=intake)
        if form.is_valid():
            form.save()
            readiness = ReadinessService().evaluate(intake)
            try:
                sm.submit_intake(readiness)
            except InvalidTransition as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Informacion guardada.")
            return redirect("consultations:waiting_room", consultation_id=consultation.id)
    else:
        form = IntakeSubmitForm(instance=intake)

    readiness = ReadinessService().evaluate(intake)

    return render(
        request,
        "consultations/waiting_room.html",
        {
            "consultation": consultation,
            "form": form,
            "readiness": readiness,
            "steps": build_status_steps(consultation.status),
        },
    )


@professional_required
def professional_room(request, consultation_id):
    consultation = get_object_or_404(
        Consultation, pk=consultation_id, professional=request.user
    )
    intake = IntakeForm.objects.filter(consultation=consultation).first()

    sm = _state_machine(consultation)
    sm.professional_join()

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "start":
                sm.start()
                messages.success(request, "Consulta iniciada.")
            elif action == "complete":
                sm.complete()
                messages.success(request, "Consulta finalizada.")
        except InvalidTransition as exc:
            messages.error(request, str(exc))
        return redirect("consultations:professional_room", consultation_id=consultation.id)

    readiness = ReadinessService().evaluate(intake) if intake else None

    return render(
        request,
        "consultations/professional_room.html",
        {
            "consultation": consultation,
            "intake": intake,
            "readiness": readiness,
            "steps": build_status_steps(consultation.status),
        },
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import patient_required, professional_required, staff_required

<<<<<<< Updated upstream
from .forms import IntakeSubmitForm
from .models import Consultation, IntakeForm
=======
from .forms import ConsultationCreateForm, IntakeSubmitForm
from .models import Consultation, Diagnosis, IntakeForm
from .services.ai_client import AIServiceUnavailable
from .services.briefing import BriefingService
from .services.diagnosis import DiagnosisNotAllowed, DiagnosisService
>>>>>>> Stashed changes
from .services.presentation import build_status_steps
from .services.readiness import ReadinessService
from .services.realtime import RealtimeNotifier
from .services.state_machine import ConsultationStateMachine, InvalidTransition
<<<<<<< Updated upstream
=======
from .services.symptom_extraction import SymptomExtractionService
from .services.symptom_vocabulary import SYMPTOM_VOCABULARY

# Tope global de síntomas confirmables por intake: sugeridos por IA que
# sigan seleccionados + agregados manualmente desde el vocabulario + "Otro"
# (si tiene texto, cuenta 1). Se valida en waiting_room al guardar el
# intake (fuente de verdad) y se expone al template para que el frontend
# no lo duplique como número mágico.
MAX_SYMPTOMS = 5
>>>>>>> Stashed changes


def _parse_symptoms_field(raw: str | None) -> tuple[list[str], str | None]:
    """
    Parsea el campo oculto "symptoms" (JSON armado por el JS de
    waiting_room.html a partir de las etiquetas seleccionadas) que viaja
    junto con el resto del intake en un único POST. Devuelve
    (lista_limpia, error) — si hay error, el llamador no debe guardar nada.
    """
    if not raw:
        return [], None

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [], "No se pudo interpretar la lista de síntomas."

    if not isinstance(parsed, list) or not all(isinstance(s, str) for s in parsed):
        return [], "Formato de síntomas inválido."

    cleaned = [s.strip() for s in parsed if s.strip()]
    if len(cleaned) > MAX_SYMPTOMS:
        return [], f"Máximo {MAX_SYMPTOMS} síntomas permitidos."

    return cleaned, None


def _state_machine(consultation: Consultation) -> ConsultationStateMachine:
    return ConsultationStateMachine(consultation, notifier=RealtimeNotifier())


@login_required
def home(request):
    """Redirige segun el rol: admins van a su panel propio, el resto a su lista."""
    if request.user.is_staff:
        return redirect("consultations:panel_consultation_list")

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


@patient_required
def patient_history_detail(request, consultation_id):
    """
    Detalle de solo lectura de una consulta pasada, para el historial del
    paciente. A propósito NO incluye nada de Diagnosis en el contexto: eso
    es un registro interno del profesional (ver Diagnosis en models.py) y
    el paciente nunca debe poder verlo, en ninguna vista.
    """
    consultation = get_object_or_404(Consultation, pk=consultation_id, patient=request.user)
    intake = IntakeForm.objects.filter(consultation=consultation).first()
    return render(
        request,
        "consultations/patient_history_detail.html",
        {"consultation": consultation, "intake": intake},
    )


@professional_required
def professional_list(request):
    consultations = Consultation.objects.filter(professional=request.user).select_related(
        "patient", "diagnosis"
    )
    return render(request, "consultations/professional_list.html", {"consultations": consultations})


@professional_required
@require_POST
def toggle_availability(request):
    """
    Alterna la disponibilidad del profesional logueado. Solo afecta si
    puede ser asignado a consultas NUEVAS de ahí en adelante (ver
    ConsultationCreateForm) — no toca ninguna consulta ya creada.
    """
    profile = request.user.profile
    profile.is_available = not profile.is_available
    profile.save(update_fields=["is_available"])
    return JsonResponse({"is_available": profile.is_available})


@patient_required
def waiting_room(request, consultation_id):
    consultation = get_object_or_404(Consultation, pk=consultation_id, patient=request.user)
    intake, _ = IntakeForm.objects.get_or_create(consultation=consultation)

    sm = _state_machine(consultation)
    sm.patient_join()  # idempotente: no-op si ya esta avanzada

    if request.method == "POST":
        form = IntakeSubmitForm(request.POST, instance=intake)
        symptoms, symptoms_error = _parse_symptoms_field(request.POST.get("symptoms"))
        if symptoms_error:
            messages.error(request, symptoms_error)
        elif form.is_valid():
            intake = form.save(commit=False)
            intake.symptoms = symptoms
            intake.save()
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
    diagnosis = Diagnosis.objects.filter(consultation=consultation).first()

    return render(
        request,
        "consultations/professional_room.html",
        {
            "consultation": consultation,
            "intake": intake,
            "readiness": readiness,
            "steps": build_status_steps(consultation.status),
            "diagnosis": diagnosis,
        },
    )
<<<<<<< Updated upstream
=======


def _parse_json_body(request) -> dict | None:
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


@patient_required
@require_POST
def analyze_symptoms(request, consultation_id):
    """
    Sugiere síntomas a partir de un texto libre (todavía no guardado en el
    intake). No persiste nada: es la vista que dispara "Analizar síntomas".
    """
    get_object_or_404(Consultation, pk=consultation_id, patient=request.user)

    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    reason = (payload.get("reason") or "").strip()
    if not reason:
        return JsonResponse({"error": "El motivo de consulta está vacío."}, status=400)

    try:
        symptoms = SymptomExtractionService().extract(reason)
    except AIServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    return JsonResponse({"symptoms": symptoms})


@patient_required
@require_GET
def symptom_vocabulary_list(request, consultation_id):
    """
    Lista de solo lectura de los términos canónicos de SYMPTOM_VOCABULARY,
    para que el frontend arme el dropdown de "+ Agregar síntoma" sin
    hardcodear el vocabulario en el template. No llama a la IA.
    """
    get_object_or_404(Consultation, pk=consultation_id, patient=request.user)
    return JsonResponse({"symptoms": list(SYMPTOM_VOCABULARY.keys())})


@professional_required
@require_POST
def generate_briefing(request, consultation_id):
    """Genera (o regenera) el briefing de IA y lo persiste en la consulta."""
    consultation = get_object_or_404(
        Consultation, pk=consultation_id, professional=request.user
    )
    intake = IntakeForm.objects.filter(consultation=consultation).first()
    if not intake or not intake.symptoms:
        return JsonResponse(
            {"error": "El paciente todavía no confirmó síntomas."}, status=400
        )

    try:
        briefing = BriefingService().generate(intake)
    except AIServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    consultation.ai_briefing = briefing
    consultation.ai_briefing_generated_at = timezone.now()
    consultation.save(update_fields=["ai_briefing", "ai_briefing_generated_at"])

    return JsonResponse(
        {
            "briefing": briefing,
            "generated_at": consultation.ai_briefing_generated_at.isoformat(),
        }
    )


@professional_required
@require_POST
def save_diagnosis(request, consultation_id):
    """
    Guarda (crea o actualiza) el diagnóstico interno del profesional.
    Registro solo para el profesional/admin: nunca se transmite al
    paciente (ver Diagnosis en models.py y DiagnosisService).
    """
    consultation = get_object_or_404(
        Consultation, pk=consultation_id, professional=request.user
    )

    data = {
        "diagnosis_text": request.POST.get("diagnosis_text", ""),
        "recommendations": request.POST.get("recommendations", ""),
        "follow_up_needed": request.POST.get("follow_up_needed") == "on",
        "follow_up_notes": request.POST.get("follow_up_notes", ""),
    }

    try:
        DiagnosisService.save(consultation, request.user, data)
    except DiagnosisNotAllowed as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Diagnóstico guardado.")

    return redirect("consultations:professional_room", consultation_id=consultation.id)


# ---- Panel de administración (reemplaza a Django Admin, ver Tarea 2/3) -----


@staff_required
def panel_consultation_list(request):
    consultations = Consultation.objects.select_related("patient", "professional")
    return render(
        request,
        "consultations/panel_consultation_list.html",
        {"consultations": consultations},
    )


@staff_required
def panel_consultation_create(request):
    if request.method == "POST":
        form = ConsultationCreateForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.created_by = request.user
            consultation.save()
            messages.success(
                request,
                f"Teleconsulta #{consultation.id} creada. Comparte el acceso con "
                f"{consultation.patient} y {consultation.professional}.",
            )
            return redirect("consultations:panel_consultation_list")
    else:
        form = ConsultationCreateForm()

    return render(
        request,
        "consultations/panel_consultation_form.html",
        {"form": form},
    )
>>>>>>> Stashed changes

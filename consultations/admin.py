from django.contrib import messages
from django.utils.html import format_html

from django.contrib import admin

from .forms import ConsultationCreateForm
from .models import Consultation, IntakeForm


class IntakeFormInline(admin.StackedInline):
    model = IntakeForm
    extra = 0
    readonly_fields = ["updated_at"]
    can_delete = False


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    """
    El requisito "un admin crea teleconsultas mediante un formulario simple"
    se resuelve con el Django Admin: no se justifica construir un CRUD
    aparte para algo que Django ya resuelve muy bien.
    """

    form = ConsultationCreateForm
    list_display = ["id", "patient", "professional", "status_badge", "scheduled_at"]
    list_filter = ["status"]
    search_fields = ["patient__username", "professional__username"]
    inlines = [IntakeFormInline]
    readonly_fields = [
        "status",
        "patient_joined_at",
        "professional_joined_at",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]

    def status_badge(self, obj):
        return format_html("<b>{}</b>", obj.get_status_display())

    status_badge.short_description = "Estado"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            messages.info(
                request,
                f"Teleconsulta #{obj.id} creada. Comparte el acceso con "
                f"{obj.patient} y {obj.professional}.",
            )

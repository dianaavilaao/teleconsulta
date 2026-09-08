from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserProfile
from consultations.models import Consultation, IntakeForm


class Command(BaseCommand):
    help = "Crea usuarios y teleconsultas de demostración para probar el flujo completo."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@demo.local"},
        )
        if created:
            admin.set_password("demo1234")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Usuario admin creado (admin / demo1234)"))

        patient = self._get_or_create_user("paciente1", UserProfile.Role.PATIENT, "Paciente Uno")
        professional = self._get_or_create_user(
            "profesional1", UserProfile.Role.PROFESSIONAL, "Profesional Uno"
        )

        # No se usa get_or_create: un paciente puede legítimamente tener
        # varias consultas con el mismo profesional (uso real de la app),
        # así que (patient, professional) no es una clave única — solo
        # interesa que exista AL MENOS una para poder probar el flujo.
        c1 = Consultation.objects.filter(patient=patient, professional=professional).first()
        if c1 is None:
            c1 = Consultation.objects.create(
                patient=patient,
                professional=professional,
                created_by=admin,
                scheduled_at=timezone.now(),
            )
        IntakeForm.objects.get_or_create(consultation=c1)

        self.stdout.write(self.style.SUCCESS("Datos de demo listos."))
        self.stdout.write("Usuarios (contraseña 'demo1234' para todos):")
        self.stdout.write("  admin        -> /panel/ (crear y gestionar teleconsultas)")
        self.stdout.write(f"  paciente1    -> sala de espera consulta #{c1.id}")
        self.stdout.write("  profesional1 -> ve la consulta asignada")

    def _get_or_create_user(self, username, role, full_name):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": full_name},
        )
        if created:
            user.set_password("demo1234")
            user.save()
        UserProfile.objects.get_or_create(user=user, defaults={"role": role})
        return user

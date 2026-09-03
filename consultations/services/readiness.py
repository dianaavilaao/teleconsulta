"""
Servicio de dominio encargado de decidir si un intake permite (o no)
iniciar la teleconsulta.

Se mantiene deliberadamente separado del modelo y de las vistas:
- El modelo (`IntakeForm`) solo guarda datos.
- Las vistas solo orquestan HTTP/WebSocket.
- Este servicio concentra la regla de negocio "¿está listo el paciente?".

Esto permite testear las reglas de negocio sin tocar Django views ni DB,
y facilita agregar nuevas reglas (ej. edad mínima, medicamentos que
requieren revisión) sin tocar el resto del sistema.
"""

from dataclasses import dataclass, field


@dataclass
class ReadinessResult:
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def can_start(self) -> bool:
        """La consulta puede avanzar a 'ready' solo si no hay blockers."""
        return not self.blockers

    def to_dict(self) -> dict:
        return {
            "can_start": self.can_start,
            "blockers": self.blockers,
            "warnings": self.warnings,
        }


class ReadinessService:
    """Evalúa un IntakeForm y devuelve blockers/warnings."""

    MIN_REASON_LENGTH = 10

    def evaluate(self, intake) -> ReadinessResult:
        blockers: list[str] = []
        warnings: list[str] = []

        if not intake.consent_given:
            blockers.append("El paciente no ha otorgado el consentimiento informado.")

        if not intake.reason or len(intake.reason.strip()) < self.MIN_REASON_LENGTH:
            blockers.append("El motivo de consulta es obligatorio y debe ser descriptivo.")

        if not intake.birth_date:
            warnings.append("No se informó la fecha de nacimiento del paciente.")

        if not intake.current_medications.strip():
            warnings.append("No se informaron medicamentos actuales (o no aplica).")

        if not intake.allergies.strip():
            warnings.append("No se informaron alergias (o no aplica).")

        return ReadinessResult(blockers=blockers, warnings=warnings)

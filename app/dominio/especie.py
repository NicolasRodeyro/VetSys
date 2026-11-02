"""Especie y su esquema de vacunas obligatorias."""

from dataclasses import dataclass
from datetime import date

from app.dominio.fechas import meses_entre


@dataclass(frozen=True)
class VacunaObligatoria:
    """Una vacuna del esquema de una especie.

    edad_aplicacion_meses: edad a partir de la cual corresponde aplicarla.
    refuerzo_cada_meses: cada cuánto se repite; None si es de una sola dosis.
    """

    nombre: str
    edad_aplicacion_meses: int
    refuerzo_cada_meses: int | None = None

    def refuerzo_vencido(self, ultima_aplicacion: date, fecha: date) -> bool:
        # GRASP Experto: la vacuna conoce su período de refuerzo,
        # así que es ella quien decide si el refuerzo ya venció.
        if self.refuerzo_cada_meses is None:
            return False
        return meses_entre(ultima_aplicacion, fecha) >= self.refuerzo_cada_meses


class Especie:
    def __init__(self, nombre: str) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.nombre = nombre
        self._esquema_vacunas: list[VacunaObligatoria] = []

    @property
    def esquema_vacunas(self) -> tuple[VacunaObligatoria, ...]:
        return tuple(self._esquema_vacunas)

    def agregar_vacuna_obligatoria(self, vacuna: VacunaObligatoria) -> None:
        self._esquema_vacunas.append(vacuna)

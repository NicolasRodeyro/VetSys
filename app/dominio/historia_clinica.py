"""Historia clínica de una mascota: experta en su estado sanitario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from app.dominio.especie import VacunaObligatoria
from app.dominio.excepciones import ReglaNegocio

from app.dominio.fechas import sumar_meses


if TYPE_CHECKING:
    from app.dominio.consulta import Consulta
    from app.dominio.mascota import Mascota


@dataclass(frozen=True)
class VacunaAplicada:
    vacuna: VacunaObligatoria
    fecha: date


class HistoriaClinica:
    def __init__(self, mascota: Mascota, alergias: str = "", antecedentes: str = "") -> None:
        self._mascota = mascota
        self.alergias = alergias
        self.antecedentes = antecedentes
        self._vacunas_aplicadas: list[VacunaAplicada] = []
        self._consultas: list[Consulta] = []

    @property
    def mascota(self) -> Mascota:
        return self._mascota

    @property
    def vacunas_aplicadas(self) -> tuple[VacunaAplicada, ...]:
        return tuple(self._vacunas_aplicadas)

    @property
    def consultas(self) -> tuple[Consulta, ...]:
        return tuple(self._consultas)

    def registrar_vacuna(self, vacuna: VacunaObligatoria, fecha: date) -> None:
        self._vacunas_aplicadas.append(VacunaAplicada(vacuna, fecha))

    def registrar_consulta(self, consulta: Consulta) -> None:
        """Agrega la consulta a la historia.

        Si la mascota tiene vacunas pendientes a la fecha de la consulta, **no se
        bloquea la atención**: la consulta se registra igual y queda con una
        advertencia por cada vacuna pendiente (CLAUDE.md §4.5).
        """
        if consulta.mascota is not self._mascota:
            raise ReglaNegocio("La consulta es de otra mascota")
        if consulta in self._consultas:
            raise ReglaNegocio("La consulta ya está registrada en la historia")

        for vacuna in self.vacunas_pendientes(consulta.fecha_hora.date()):
            consulta.agregar_advertencia(f"Vacuna pendiente: {vacuna.nombre}")
        self._consultas.append(consulta)

    def vacunas_pendientes(self, fecha: date) -> list[VacunaObligatoria]:
        """Vacunas del esquema de la especie que le faltan a la mascota en `fecha`.

        Una vacuna está pendiente si por la edad ya le corresponde y:
        - nunca se aplicó, o
        - se aplicó pero el refuerzo ya venció.
        """
        edad = self._mascota.edad_en_meses(fecha)
        pendientes = []
        for vacuna in self._mascota.especie.esquema_vacunas:
            if edad < vacuna.edad_aplicacion_meses:
                continue  # todavía no le corresponde por edad
            ultima = self._ultima_aplicacion(vacuna, fecha)
            if ultima is None or vacuna.refuerzo_vencido(ultima, fecha):
                pendientes.append(vacuna)
        return pendientes

    def _ultima_aplicacion(self, vacuna: VacunaObligatoria, fecha: date) -> date | None:
        """Fecha de la última aplicación de `vacuna` hasta `fecha` inclusive."""
        fechas = [
            aplicada.fecha
            for aplicada in self._vacunas_aplicadas
            if aplicada.vacuna == vacuna and aplicada.fecha <= fecha
        ]
        return max(fechas) if fechas else None

    def vacunas_pendientes_con_vencimiento(self, fecha: date) -> list[tuple[VacunaObligatoria, date]]:
        """Las mismas vacunas que `vacunas_pendientes(fecha)`, cada una con la fecha en que venció.

        - Nunca aplicada: venció al cumplir la edad de aplicación (nacimiento + edad_aplicacion_meses).
        - Aplicada con refuerzo: venció a la última aplicación + refuerzo_cada_meses.
        Se parte de `vacunas_pendientes` para que la regla de qué está pendiente siga en un solo lugar.
        """
        return [(vacuna, self._vencimiento(vacuna, fecha)) for vacuna in self.vacunas_pendientes(fecha)]

    def _vencimiento(self, vacuna: VacunaObligatoria, fecha: date) -> date:
        ultima = self._ultima_aplicacion(vacuna, fecha)
        if ultima is None:
            return sumar_meses(self._mascota.fecha_nacimiento, vacuna.edad_aplicacion_meses)
        # Si está pendiente y ya se aplicó, es porque tiene refuerzo y venció.
        return sumar_meses(ultima, vacuna.refuerzo_cada_meses)
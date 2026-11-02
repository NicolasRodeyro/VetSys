"""Veterinario y su agenda de turnos."""

from app.dominio.clinica import Clinica
from app.dominio.enums import EstadoTurno
from app.dominio.excepciones import ReglaNegocio
from app.dominio.turno import Turno


class Veterinario:
    def __init__(self, matricula: str, nombre: str, apellido: str, clinica: Clinica) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.matricula = matricula
        self.nombre = nombre
        self.apellido = apellido
        self.clinica = clinica
        # La agenda es privada: la única forma de agregar un turno es
        # agregar_turno(), que valida que no se superponga.
        self._turnos: list[Turno] = []

    @property
    def turnos(self) -> tuple[Turno, ...]:
        return tuple(self._turnos)

    def agregar_turno(self, turno: Turno) -> None:
        # Regla de negocio: no puede haber turnos superpuestos en la agenda de
        # un veterinario. Los cancelados no cuentan: liberan el horario.
        for existente in self._turnos:
            if existente.estado is EstadoTurno.CANCELADO:
                continue
            if turno.se_superpone_con(existente):
                raise ReglaNegocio(
                    f"El turno se superpone con otro de {self.apellido} "
                    f"({existente.inicio:%d/%m/%Y %H:%M} a {existente.fin:%H:%M})"
                )
        self._turnos.append(turno)

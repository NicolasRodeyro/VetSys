"""Turno: un intervalo de tiempo reservado para atender a una mascota."""

from datetime import datetime, timedelta

from app.dominio.enums import EstadoTurno
from app.dominio.excepciones import ReglaNegocio
from app.dominio.mascota import Mascota


class Turno:
    def __init__(self, inicio: datetime, duracion_minutos: int, mascota: Mascota) -> None:
        if duracion_minutos <= 0:
            raise ReglaNegocio("La duración del turno debe ser mayor a cero")
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self._inicio = inicio
        self._duracion_minutos = duracion_minutos
        self._mascota = mascota
        self._estado = EstadoTurno.PROGRAMADO

    @property
    def inicio(self) -> datetime:
        return self._inicio

    @property
    def duracion_minutos(self) -> int:
        return self._duracion_minutos

    @property
    def fin(self) -> datetime:
        return self._inicio + timedelta(minutes=self._duracion_minutos)

    @property
    def mascota(self) -> Mascota:
        return self._mascota

    @property
    def estado(self) -> EstadoTurno:
        return self._estado

    def cancelar(self) -> None:
        self._estado = EstadoTurno.CANCELADO

    def se_superpone_con(self, otro: "Turno") -> bool:
        """Los turnos se tratan como intervalos [inicio, fin): si uno termina
        justo cuando empieza el otro, no se superponen."""
        return self._inicio < otro.fin and otro.inicio < self.fin

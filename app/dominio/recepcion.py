"""Recepción en el laboratorio: una constancia por conservadora recibida."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import TYPE_CHECKING

from app.dominio.enums import EstadoPrecinto, MotivoRechazo
from app.dominio.excepciones import ReglaNegocio
from app.dominio.laboratorio import Laboratorio

if TYPE_CHECKING:
    from app.dominio.conservadora import Conservadora


class DetalleRecepcion:
    """Lo que el laboratorio constató al recibir una conservadora.

    Es el experto en decidir si se acepta: compara el estado del precinto y la
    temperatura de llegada contra el rango de la conservadora. Pueden darse los
    dos motivos de rechazo a la vez.
    """

    def __init__(
        self,
        conservadora: Conservadora,
        estado_precinto: EstadoPrecinto,
        temperatura_llegada: float,
        observacion: str = "",
    ) -> None:
        self._conservadora = conservadora
        self._estado_precinto = estado_precinto
        self._temperatura_llegada = temperatura_llegada
        self.observacion = observacion

        motivos: list[MotivoRechazo] = []
        if estado_precinto is EstadoPrecinto.ROTO:
            motivos.append(MotivoRechazo.PRECINTO_ROTO)
        if not conservadora.admite_temperatura(temperatura_llegada):
            motivos.append(MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO)
        self._motivos = tuple(motivos)

    @property
    def conservadora(self) -> Conservadora:
        return self._conservadora

    @property
    def estado_precinto(self) -> EstadoPrecinto:
        return self._estado_precinto

    @property
    def temperatura_llegada(self) -> float:
        return self._temperatura_llegada

    @property
    def motivos(self) -> tuple[MotivoRechazo, ...]:
        return self._motivos

    @property
    def aceptada(self) -> bool:
        return not self._motivos


class Recepcion:
    def __init__(
        self,
        laboratorio: Laboratorio,
        responsable: str,
        fecha_hora: datetime,
        detalles: Iterable[DetalleRecepcion],
    ) -> None:
        self._detalles = tuple(detalles)
        if not self._detalles:
            raise ReglaNegocio("La recepción necesita al menos un detalle")
        self._laboratorio = laboratorio
        self.responsable = responsable
        self._fecha_hora = fecha_hora

    @property
    def laboratorio(self) -> Laboratorio:
        return self._laboratorio

    @property
    def fecha_hora(self) -> datetime:
        return self._fecha_hora

    @property
    def detalles(self) -> tuple[DetalleRecepcion, ...]:
        return self._detalles

    @property
    def todas_aceptadas(self) -> bool:
        return all(detalle.aceptada for detalle in self._detalles)

    @property
    def ninguna_aceptada(self) -> bool:
        return not any(detalle.aceptada for detalle in self._detalles)

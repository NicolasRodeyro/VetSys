"""Observadores de la muestra (patrón Observer).

La Muestra es el sujeto: cada vez que cambia de estado avisa a los
observadores suscriptos. Cada observador decide qué hacer con el aviso.
Los observadores no se persisten: los suscribe la capa de servicios al
cargar la muestra (CLAUDE.md §4.4).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.dominio.estados_muestra import Analizada, Rechazada

if TYPE_CHECKING:
    from app.dominio.cambio_estado import CambioEstado
    from app.dominio.cliente import Cliente
    from app.dominio.muestra import Muestra


class ObservadorMuestra(ABC):
    @abstractmethod
    def actualizar(self, muestra: Muestra, cambio: CambioEstado) -> None:
        """Recibe el aviso de que `muestra` cambió de estado.

        `cambio` trae el estado anterior y el nuevo, además de cuándo, quién,
        dónde y por qué.
        """


class RegistroTrazabilidad(ObservadorMuestra):
    """Guarda cada cambio en el historial de la muestra (obligatorio)."""

    def actualizar(self, muestra: Muestra, cambio: CambioEstado) -> None:
        muestra.agregar_al_historial(cambio)


class AlertaRechazo(ObservadorMuestra):
    """Cuando la muestra pasa a Rechazada, deja un aviso para la clínica
    para que coordine la re-extracción (obligatorio)."""

    def __init__(self) -> None:
        self._alertas: list[str] = []

    @property
    def alertas(self) -> tuple[str, ...]:
        return tuple(self._alertas)

    def actualizar(self, muestra: Muestra, cambio: CambioEstado) -> None:
        if cambio.nuevo != Rechazada.nombre:
            return
        # Texto legible para quien lo lea: PRECINTO_ROTO -> "precinto roto"
        motivos = ", ".join(motivo.value.replace("_", " ").lower() for motivo in cambio.motivos)
        self._alertas.append(
            f"Muestra rechazada ({motivos}): coordinar la re-extracción con la clínica"
        )


class NotificadorCliente(ObservadorMuestra):
    """Cuando la muestra pasa a Analizada, avisa al responsable de la mascota (opcional)."""

    def __init__(self, cliente: Cliente) -> None:
        self._cliente = cliente
        self._avisos: list[str] = []

    @property
    def avisos(self) -> tuple[str, ...]:
        return tuple(self._avisos)

    def actualizar(self, muestra: Muestra, cambio: CambioEstado) -> None:
        if cambio.nuevo != Analizada.nombre:
            return
        self._avisos.append(
            f"{self._cliente.nombre} {self._cliente.apellido}: "
            f"ya está el resultado de {muestra.tipo_analisis.nombre}"
        )

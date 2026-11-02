"""Estados de la muestra (patrón State).

Cada estado es un objeto que decide qué operaciones permite y a qué estado
pasa. Como en la guía de la cátedra, la muestra delega en su estado actual y
el estado le pide a la muestra que cambie con `muestra.cambiar_estado(...)`.

`EstadoMuestra` implementa TODAS las operaciones lanzando TransicionInvalida;
cada estado concreto sobrescribe solo las que permite. Así la clase Muestra
no necesita ningún `if estado == ...`.

Ciclo de vida (CLAUDE.md §4.2):

    Extraida -> Empaquetada -> EnTransito -> Recibida -> Analizada
                                   \\-> Rechazada
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING

from app.dominio.enums import MotivoRechazo
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida

if TYPE_CHECKING:
    from app.dominio.muestra import Muestra


# Las operaciones que la muestra delega en su estado.
OPERACIONES = ("empaquetar", "despachar", "recibir", "analizar")


class EstadoMuestra(ABC):
    @property
    @abstractmethod
    def nombre(self) -> str:
        """Texto con el que se guarda el estado en la base (ej. 'EN_TRANSITO')."""

    @property
    def es_final(self) -> bool:
        return False

    @property
    def activa(self) -> bool:
        """Una muestra está activa mientras no haya sido rechazada."""
        return True

    @property
    def motivos(self) -> tuple[MotivoRechazo, ...]:
        return ()

    @property
    def operaciones_permitidas(self) -> tuple[str, ...]:
        """Las operaciones que este estado permite: las que sobrescribe (la base rechaza todas)."""
        return tuple(
            operacion for operacion in OPERACIONES
            if getattr(type(self), operacion) is not getattr(EstadoMuestra, operacion)
        )

    # --- Operaciones: por defecto no están permitidas ---

    def empaquetar(
        self, muestra: Muestra, responsable: str, ubicacion: str, observacion: str
    ) -> None:
        self._no_permitida("empaquetar")

    def despachar(
        self, muestra: Muestra, responsable: str, ubicacion: str, observacion: str
    ) -> None:
        self._no_permitida("despachar")

    def recibir(
        self,
        muestra: Muestra,
        aceptada: bool,
        motivos: Iterable[MotivoRechazo],
        responsable: str,
        ubicacion: str,
        observacion: str,
    ) -> None:
        self._no_permitida("recibir")

    def analizar(
        self, muestra: Muestra, responsable: str, ubicacion: str, observacion: str
    ) -> None:
        self._no_permitida("analizar")

    def _no_permitida(self, operacion: str) -> None:
        raise TransicionInvalida(
            f"No se puede {operacion} una muestra en estado {self.nombre}"
        )


class Extraida(EstadoMuestra):
    nombre = "EXTRAIDA"

    def empaquetar(self, muestra, responsable, ubicacion, observacion) -> None:
        muestra.cambiar_estado(Empaquetada(), responsable, ubicacion, observacion)


class Empaquetada(EstadoMuestra):
    nombre = "EMPAQUETADA"

    def despachar(self, muestra, responsable, ubicacion, observacion) -> None:
        muestra.cambiar_estado(EnTransito(), responsable, ubicacion, observacion)


class EnTransito(EstadoMuestra):
    nombre = "EN_TRANSITO"

    def recibir(self, muestra, aceptada, motivos, responsable, ubicacion, observacion) -> None:
        # El rechazo solo ocurre acá: en la recepción del laboratorio.
        if aceptada:
            if tuple(motivos):
                raise ReglaNegocio("Una muestra aceptada no puede tener motivos de rechazo")
            nuevo: EstadoMuestra = Recibida()
        else:
            nuevo = Rechazada(motivos)
        muestra.cambiar_estado(nuevo, responsable, ubicacion, observacion)


class Recibida(EstadoMuestra):
    nombre = "RECIBIDA"

    def analizar(self, muestra, responsable, ubicacion, observacion) -> None:
        muestra.cambiar_estado(Analizada(), responsable, ubicacion, observacion)


class Analizada(EstadoMuestra):
    nombre = "ANALIZADA"

    @property
    def es_final(self) -> bool:
        return True


class Rechazada(EstadoMuestra):
    nombre = "RECHAZADA"

    def __init__(self, motivos: Iterable[MotivoRechazo]) -> None:
        self._motivos = tuple(motivos)
        if not self._motivos:
            raise ReglaNegocio("Una muestra rechazada necesita al menos un motivo")

    @property
    def es_final(self) -> bool:
        return True

    @property
    def activa(self) -> bool:
        return False

    @property
    def motivos(self) -> tuple[MotivoRechazo, ...]:
        return self._motivos

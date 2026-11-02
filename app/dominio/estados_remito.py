"""Estados del remito biológico (patrón State).

Igual que con la muestra: el remito delega en su estado actual, cada estado
sobrescribe solo las operaciones que permite y el resto lanza TransicionInvalida.

Ciclo de vida (CLAUDE.md §4.3):

    Abierto -> Cerrado -> EnTransito -+-> Recibido          (todas aceptadas)
                                      +-> RecibidoParcial   (algunas rechazadas)
                                      +-> Rechazado         (todas rechazadas)

Los dos State colaboran: el remito no cambia el estado de las muestras, les pide
`despachar()` o `recibir()` y el estado de cada muestra valida su propia transición.
(Los nombres Abierto, EnTransito, etc. no chocan con los de la muestra porque
viven en otro módulo.)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.dominio.excepciones import ReglaNegocio, TransicionInvalida

if TYPE_CHECKING:
    from app.dominio.conservadora import Conservadora
    from app.dominio.recepcion import Recepcion
    from app.dominio.remito_biologico import RemitoBiologico
    from app.dominio.tramo_envio import TramoEnvio


# Las operaciones que el remito delega en su estado, en el orden en que se muestran.
OPERACIONES = (
    "agregar_conservadora",
    "quitar_conservadora",
    "cerrar",
    "despachar",
    "registrar_tramo",
    "registrar_recepcion",
)


class EstadoRemito(ABC):
    @property
    @abstractmethod
    def nombre(self) -> str:
        """Texto con el que se guarda el estado en la base (ej. 'EN_TRANSITO')."""

    @property
    def es_final(self) -> bool:
        return False

    @property
    def operaciones_permitidas(self) -> tuple[str, ...]:
        """Las operaciones que este estado permite, para que la interfaz muestre solo esos botones.

        Una operación está permitida si el estado concreto la sobrescribe: la clase base
        las rechaza todas. Así no hay una segunda tabla que mantener en sincronía."""
        return tuple(
            operacion for operacion in OPERACIONES
            if getattr(type(self), operacion) is not getattr(EstadoRemito, operacion)
        )

    # --- Operaciones: por defecto no están permitidas ---

    def agregar_conservadora(self, remito: RemitoBiologico, conservadora: Conservadora) -> None:
        self._no_permitida("agregar una conservadora")

    def quitar_conservadora(self, remito: RemitoBiologico, conservadora: Conservadora) -> None:
        self._no_permitida("quitar una conservadora")

    def cerrar(self, remito: RemitoBiologico) -> None:
        self._no_permitida("cerrar el remito")

    def despachar(
        self, remito: RemitoBiologico, responsable: str, ubicacion: str, observacion: str
    ) -> None:
        self._no_permitida("despachar el remito")

    def registrar_tramo(self, remito: RemitoBiologico, tramo: TramoEnvio) -> None:
        self._no_permitida("registrar un tramo")

    def registrar_recepcion(self, remito: RemitoBiologico, recepcion: Recepcion) -> None:
        self._no_permitida("registrar la recepción")

    def _no_permitida(self, operacion: str) -> None:
        raise TransicionInvalida(
            f"No se puede {operacion}: el remito está en estado {self.nombre}"
        )


class Abierto(EstadoRemito):
    nombre = "ABIERTO"

    def agregar_conservadora(self, remito, conservadora) -> None:
        if conservadora in remito.conservadoras:
            raise ReglaNegocio(f"La conservadora {conservadora.codigo} ya está en el remito")
        remito.incorporar_conservadora(conservadora)

    def quitar_conservadora(self, remito, conservadora) -> None:
        # Quitarla del remito NO es desempaquetar: las muestras siguen en la conservadora.
        if conservadora not in remito.conservadoras:
            raise ReglaNegocio(f"La conservadora {conservadora.codigo} no está en el remito")
        remito.retirar_conservadora(conservadora)

    def cerrar(self, remito) -> None:
        if not remito.conservadoras:
            raise ReglaNegocio("El remito necesita al menos una conservadora para cerrarse")
        sin_precinto = [c.codigo for c in remito.conservadoras if c.precinto is None]
        if sin_precinto:
            raise ReglaNegocio(
                "Todas las conservadoras deben tener precinto para cerrar el remito; "
                f"faltan: {', '.join(sin_precinto)}"
            )
        remito.cambiar_estado(Cerrado())


class Cerrado(EstadoRemito):
    nombre = "CERRADO"

    def despachar(self, remito, responsable, ubicacion, observacion) -> None:
        # El remito le pide a cada muestra que se despache; el State de la muestra
        # valida que pueda hacerlo y la pasa a En tránsito.
        for conservadora in remito.conservadoras:
            for muestra in conservadora.muestras:
                muestra.despachar(
                    responsable, ubicacion, observacion or f"Remito {remito.numero}"
                )
        remito.cambiar_estado(EnTransito())


class EnTransito(EstadoRemito):
    nombre = "EN_TRANSITO"

    def registrar_tramo(self, remito, tramo) -> None:
        remito.incorporar_tramo(tramo)

    def registrar_recepcion(self, remito, recepcion) -> None:
        recibidas = [detalle.conservadora for detalle in recepcion.detalles]
        if len(recibidas) != len(remito.conservadoras) or set(recibidas) != set(remito.conservadoras):
            raise ReglaNegocio(
                "La recepción debe tener un detalle por cada conservadora del remito"
            )

        # Cada muestra recibe el resultado del detalle de su conservadora.
        for detalle in recepcion.detalles:
            for muestra in detalle.conservadora.muestras:
                muestra.recibir(
                    detalle.aceptada,
                    recepcion.responsable,
                    detalle.motivos,
                    recepcion.laboratorio.nombre,
                    detalle.observacion,
                )

        # El estado final del remito sale de los detalles.
        if recepcion.todas_aceptadas:
            nuevo: EstadoRemito = Recibido()
        elif recepcion.ninguna_aceptada:
            nuevo = Rechazado()
        else:
            nuevo = RecibidoParcial()
        remito.cambiar_estado(nuevo)


class Recibido(EstadoRemito):
    nombre = "RECIBIDO"

    @property
    def es_final(self) -> bool:
        return True


class RecibidoParcial(EstadoRemito):
    nombre = "RECIBIDO_PARCIAL"

    @property
    def es_final(self) -> bool:
        return True


class Rechazado(EstadoRemito):
    nombre = "RECHAZADO"

    @property
    def es_final(self) -> bool:
        return True

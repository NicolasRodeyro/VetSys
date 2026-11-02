"""Remito biológico: documento que acompaña a las conservadoras desde la clínica
hasta el laboratorio.

No decide nada según su estado: delega en el objeto de estado actual
(patrón State, ver estados_remito.py).
"""

from __future__ import annotations

from datetime import datetime

from app.dominio.clinica import Clinica
from app.dominio.conservadora import Conservadora
from app.dominio.estados_remito import Abierto, EstadoRemito
from app.dominio.laboratorio import Laboratorio
from app.dominio.recepcion import Recepcion
from app.dominio.tramo_envio import TramoEnvio


class RemitoBiologico:
    def __init__(self, numero: str, origen: Clinica, destino: Laboratorio) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.numero = numero
        self._origen = origen
        self._destino = destino
        self._estado: EstadoRemito = Abierto()
        self._conservadoras: list[Conservadora] = []
        self._tramos: list[TramoEnvio] = []
        self._recepcion: Recepcion | None = None

    @property
    def origen(self) -> Clinica:
        return self._origen

    @property
    def destino(self) -> Laboratorio:
        return self._destino

    @property
    def estado(self) -> EstadoRemito:
        return self._estado

    @property
    def conservadoras(self) -> tuple[Conservadora, ...]:
        return tuple(self._conservadoras)

    @property
    def tramos(self) -> tuple[TramoEnvio, ...]:
        return tuple(self._tramos)

    @property
    def recepcion(self) -> Recepcion | None:
        return self._recepcion

    # --- Operaciones: el remito delega en su estado ---

    def agregar_conservadora(self, conservadora: Conservadora) -> None:
        self._estado.agregar_conservadora(self, conservadora)

    def quitar_conservadora(self, conservadora: Conservadora) -> None:
        self._estado.quitar_conservadora(self, conservadora)

    def cerrar(self) -> None:
        self._estado.cerrar(self)

    def despachar(self, responsable: str, ubicacion: str = "", observacion: str = "") -> None:
        self._estado.despachar(self, responsable, ubicacion, observacion)

    def registrar_tramo(
        self,
        origen: str,
        destino: str,
        transportista: str,
        salida: datetime,
        llegada: datetime | None = None,
        temperatura: float | None = None,
    ) -> None:
        tramo = TramoEnvio(
            len(self._tramos) + 1, origen, destino, transportista, salida, llegada, temperatura
        )
        self._estado.registrar_tramo(self, tramo)

    def registrar_recepcion(self, recepcion: Recepcion) -> None:
        self._estado.registrar_recepcion(self, recepcion)
        self._recepcion = recepcion

    # --- Operaciones que usan los estados para modificar el remito ---
    # (Como cambiar_estado() de la muestra: no son para llamar desde afuera.)

    def cambiar_estado(self, nuevo_estado: EstadoRemito) -> None:
        self._estado = nuevo_estado

    def incorporar_conservadora(self, conservadora: Conservadora) -> None:
        self._conservadoras.append(conservadora)

    def retirar_conservadora(self, conservadora: Conservadora) -> None:
        self._conservadoras.remove(conservadora)

    def incorporar_tramo(self, tramo: TramoEnvio) -> None:
        self._tramos.append(tramo)

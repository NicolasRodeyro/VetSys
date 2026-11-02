"""Consulta médica: una atención de una mascota con un veterinario."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.dominio.comprobante import Comprobante, ItemComprobante
from app.dominio.enums import EstadoTurno, Prioridad, TipoConsulta
from app.dominio.excepciones import ReglaNegocio
from app.dominio.orden_derivacion import OrdenDerivacion

if TYPE_CHECKING:
    from app.dominio.mascota import Mascota
    from app.dominio.tipo_analisis import TipoAnalisis
    from app.dominio.turno import Turno
    from app.dominio.veterinario import Veterinario


class Consulta:
    def __init__(
        self,
        tipo: TipoConsulta,
        fecha_hora: datetime,
        mascota: Mascota,
        veterinario: Veterinario,
        turno: Turno | None = None,
        diagnostico: str = "",
        tratamiento: str = "",
    ) -> None:
        # El turno es opcional (las urgencias no tienen turno), pero si hay
        # uno tiene que ser de esta mascota y no estar cancelado.
        if turno is not None:
            if turno.mascota is not mascota:
                raise ReglaNegocio("El turno es de otra mascota")
            if turno.estado is EstadoTurno.CANCELADO:
                raise ReglaNegocio("No se puede atender un turno cancelado")

        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self._tipo = tipo
        self._fecha_hora = fecha_hora
        self._mascota = mascota
        self._veterinario = veterinario
        self._turno = turno
        self.diagnostico = diagnostico
        self.tratamiento = tratamiento
        self._advertencias: list[str] = []
        self._ordenes: list[OrdenDerivacion] = []
        self._comprobante: Comprobante | None = None

    @property
    def tipo(self) -> TipoConsulta:
        return self._tipo

    @property
    def fecha_hora(self) -> datetime:
        return self._fecha_hora

    @property
    def mascota(self) -> Mascota:
        return self._mascota

    @property
    def veterinario(self) -> Veterinario:
        return self._veterinario

    @property
    def turno(self) -> Turno | None:
        return self._turno

    @property
    def advertencias(self) -> tuple[str, ...]:
        return tuple(self._advertencias)

    def agregar_advertencia(self, texto: str) -> None:
        self._advertencias.append(texto)

    @property
    def ordenes(self) -> tuple[OrdenDerivacion, ...]:
        return tuple(self._ordenes)

    def emitir_orden(
        self, tipo_analisis: TipoAnalisis, prioridad: Prioridad = Prioridad.NORMAL
    ) -> OrdenDerivacion:
        """Emite una orden de derivación a laboratorio dentro de esta consulta."""
        if self._comprobante is not None:
            raise ReglaNegocio("La consulta ya está cerrada: no admite nuevas órdenes")
        orden = OrdenDerivacion(tipo_analisis, prioridad)
        self._ordenes.append(orden)
        return orden

    @property
    def comprobante(self) -> Comprobante | None:
        return self._comprobante

    @property
    def cerrada(self) -> bool:
        return self._comprobante is not None

    def cerrar(self, honorarios: Decimal, fecha_hora: datetime) -> Comprobante:
        """Cierra la consulta y emite su único comprobante.

        Tiene un ítem por la consulta (`honorarios`) y uno por cada orden de
        derivación, con el precio de su TipoAnalisis. Se cobra por orden y no por
        muestra: si una muestra se rechaza y se vuelve a extraer, no hay cargo nuevo.
        """
        if self._comprobante is not None:
            raise ReglaNegocio("La consulta ya está cerrada")
        if honorarios < 0:
            raise ReglaNegocio("Los honorarios no pueden ser negativos")

        items = [ItemComprobante(self._tipo.value.capitalize(), honorarios)]
        for orden in self._ordenes:
            analisis = orden.tipo_analisis
            items.append(ItemComprobante(analisis.nombre, analisis.precio, es_laboratorio=True))

        self._comprobante = Comprobante(self, fecha_hora, items)
        return self._comprobante

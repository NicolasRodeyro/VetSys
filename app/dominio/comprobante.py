"""Comprobante de atención: lo que paga el cliente al irse de la clínica."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.dominio.excepciones import ReglaNegocio

if TYPE_CHECKING:
    from app.dominio.cliente import Cliente
    from app.dominio.consulta import Consulta


@dataclass(frozen=True)
class ItemComprobante:
    """Un renglón del comprobante. Los montos son Decimal, nunca float.

    `es_laboratorio` distingue los servicios de laboratorio (las órdenes de
    derivación) de los de la clínica, para el reporte de facturación.
    """

    descripcion: str
    monto: Decimal
    es_laboratorio: bool = False


class Comprobante:
    def __init__(
        self, consulta: Consulta, fecha_hora: datetime, items: Iterable[ItemComprobante]
    ) -> None:
        self._items = tuple(items)
        if not self._items:
            raise ReglaNegocio("El comprobante necesita al menos un ítem")
        self._consulta = consulta
        self._fecha_hora = fecha_hora

    @property
    def consulta(self) -> Consulta:
        return self._consulta

    @property
    def cliente(self) -> Cliente:
        return self._consulta.mascota.responsable

    @property
    def fecha_hora(self) -> datetime:
        return self._fecha_hora

    @property
    def items(self) -> tuple[ItemComprobante, ...]:
        return self._items

    @property
    def total(self) -> Decimal:
        return sum((item.monto for item in self._items), Decimal("0"))

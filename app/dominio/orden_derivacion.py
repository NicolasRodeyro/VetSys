"""Orden de derivación: pide un análisis de laboratorio a partir de una consulta."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.dominio.enums import Prioridad
from app.dominio.excepciones import ReglaNegocio
from app.dominio.tipo_analisis import TipoAnalisis

if TYPE_CHECKING:
    from app.dominio.muestra import Muestra


class OrdenDerivacion:
    def __init__(self, tipo_analisis: TipoAnalisis, prioridad: Prioridad = Prioridad.NORMAL) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self._tipo_analisis = tipo_analisis
        self.prioridad = prioridad
        # Una orden puede tener varias muestras a lo largo del tiempo (si una se
        # rechaza se vuelve a extraer), pero solo una activa a la vez.
        self._muestras: list[Muestra] = []

    @property
    def tipo_analisis(self) -> TipoAnalisis:
        return self._tipo_analisis

    @property
    def muestras(self) -> tuple[Muestra, ...]:
        return tuple(self._muestras)

    def muestra_activa(self) -> Muestra | None:
        """La muestra no rechazada de la orden, o None si no hay."""
        for muestra in self._muestras:
            if muestra.esta_activa():
                return muestra
        return None

    def agregar_muestra(self, muestra: Muestra) -> None:
        # Regla de negocio: una sola muestra activa por orden. Una muestra
        # rechazada ya no cuenta, así que se puede re-extraer.
        if self.muestra_activa() is not None:
            raise ReglaNegocio("La orden ya tiene una muestra activa")
        self._muestras.append(muestra)

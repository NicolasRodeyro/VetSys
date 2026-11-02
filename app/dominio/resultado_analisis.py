"""Resultado de un análisis de laboratorio.

No tiene estados propios (CLAUDE.md §4.1): registrarlo es lo que pasa la
muestra a Analizada.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.dominio.excepciones import ReglaNegocio

if TYPE_CHECKING:
    from app.dominio.muestra import Muestra


@dataclass(frozen=True)
class ValorResultado:
    """Un parámetro medido, con el rango de referencia contra el que se interpreta.

    Cualquiera de los dos límites puede faltar (ej. un parámetro que solo tiene máximo).
    """

    parametro: str
    valor: float
    unidad: str
    ref_min: float | None = None
    ref_max: float | None = None

    def __post_init__(self) -> None:
        if self.ref_min is not None and self.ref_max is not None and self.ref_min > self.ref_max:
            raise ReglaNegocio("El mínimo de referencia no puede superar al máximo")

    def fuera_de_rango(self) -> bool:
        if self.ref_min is not None and self.valor < self.ref_min:
            return True
        if self.ref_max is not None and self.valor > self.ref_max:
            return True
        return False


class ResultadoAnalisis:
    def __init__(
        self,
        muestra: Muestra,
        responsable: str,
        fecha_hora: datetime,
        valores: Iterable[ValorResultado],
        observaciones: str = "",
        ubicacion: str = "",
    ) -> None:
        """Registra el resultado de una muestra y la pasa a Analizada.

        Si la muestra no está Recibida, su State lanza TransicionInvalida y el
        resultado no se crea. Como la muestra queda Analizada (estado final), no
        puede tener un segundo resultado.
        """
        self._valores = tuple(valores)
        if not self._valores:
            raise ReglaNegocio("El resultado necesita al menos un valor")

        muestra.analizar(responsable, ubicacion, observaciones or "Resultado registrado")

        self._muestra = muestra
        self.responsable = responsable
        self._fecha_hora = fecha_hora
        self.observaciones = observaciones

    @property
    def muestra(self) -> Muestra:
        return self._muestra

    @property
    def fecha_hora(self) -> datetime:
        return self._fecha_hora

    @property
    def valores(self) -> tuple[ValorResultado, ...]:
        return self._valores

    def valores_fuera_de_rango(self) -> tuple[ValorResultado, ...]:
        return tuple(valor for valor in self._valores if valor.fuera_de_rango())

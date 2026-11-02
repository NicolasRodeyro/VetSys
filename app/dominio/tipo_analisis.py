"""Tipo de análisis de laboratorio: un catálogo con precio y condiciones de la muestra."""

from dataclasses import dataclass
from decimal import Decimal

from app.dominio.excepciones import ReglaNegocio


@dataclass(frozen=True)
class TipoAnalisis:
    """Es una clase y no un enum porque tiene datos que usan las reglas de negocio
    (CLAUDE.md §4.6): el precio para el comprobante y el rango de temperatura
    para validar la conservadora y la recepción.
    """

    nombre: str
    precio: Decimal
    tipo_muestra: str
    temp_min: float
    temp_max: float
    horas_max_transito: int

    def __post_init__(self) -> None:
        if self.temp_min > self.temp_max:
            raise ReglaNegocio("La temperatura mínima no puede superar a la máxima")

    def admite_temperatura(self, temperatura: float) -> bool:
        return self.temp_min <= temperatura <= self.temp_max

    def admite_rango(self, desde: float, hasta: float) -> bool:
        """¿Un contenedor que se mantiene entre `desde` y `hasta` cuida esta muestra?
        Sí si todo su rango queda adentro del que necesita el análisis."""
        return self.temp_min <= desde and hasta <= self.temp_max

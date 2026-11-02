"""Tramo de envío: un trayecto de la cadena de transporte de un remito."""

from dataclasses import dataclass
from datetime import datetime

from app.dominio.excepciones import ReglaNegocio


@dataclass(frozen=True)
class TramoEnvio:
    """Un tramo une dos lugares (clínica, centro de distribución, laboratorio...)
    con un transportista. La temperatura es la medida durante ese tramo; la
    llegada y la temperatura pueden faltar mientras el tramo está en curso.
    """

    orden: int
    origen: str
    destino: str
    transportista: str
    salida: datetime
    llegada: datetime | None = None
    temperatura: float | None = None

    def __post_init__(self) -> None:
        if self.llegada is not None and self.llegada < self.salida:
            raise ReglaNegocio("La llegada del tramo no puede ser anterior a su salida")

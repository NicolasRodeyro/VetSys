"""Cambio de estado de una muestra: un renglón de su trazabilidad."""

from dataclasses import dataclass
from datetime import datetime

from app.dominio.enums import MotivoRechazo


@dataclass(frozen=True)
class CambioEstado:
    """Es inmutable (frozen=True): una vez registrado no se puede modificar,
    que es lo que pide la validación de trazabilidad inmutable.

    Los estados se guardan por su nombre (texto), igual que en la base.
    `anterior` es None en la extracción, que es el origen de la muestra.
    `motivos` solo se completa cuando la muestra pasa a Rechazada.
    """

    anterior: str | None
    nuevo: str
    fecha_hora: datetime
    responsable: str
    ubicacion: str = ""
    observacion: str = ""
    motivos: tuple[MotivoRechazo, ...] = ()

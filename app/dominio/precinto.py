"""Precinto sanitario: sella una conservadora para garantizar que no se abrió."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Precinto:
    """Es de la conservadora, no de la muestra (CLAUDE.md §4.1).

    No guarda un estado propio: al colocarlo está intacto, y lo que importa
    es en qué estado lo encuentra el laboratorio al recibir (ver DetalleRecepcion).
    """

    numero: str
    fecha_colocacion: datetime
    responsable: str

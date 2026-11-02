"""Conversión entre los tipos del dominio y lo que se guarda en SQLite.

Fechas como texto ISO 8601 y montos (Decimal) como texto (CLAUDE.md §5 y §6).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal


def a_texto(valor: date | datetime | Decimal | None) -> str | None:
    return None if valor is None else (str(valor) if isinstance(valor, Decimal) else valor.isoformat())


def a_datetime(texto: str | None) -> datetime | None:
    return None if texto is None else datetime.fromisoformat(texto)


def a_fecha(texto: str) -> date:
    return date.fromisoformat(texto)


def a_decimal(texto: str) -> Decimal:
    return Decimal(texto)

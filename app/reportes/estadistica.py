"""Cálculos que SQLite no tiene o que no conviene hacer en SQL."""

from __future__ import annotations

from decimal import Decimal


def variacion_porcentual(actual: Decimal, anterior: Decimal) -> Decimal | None:
    """(actual - anterior) / anterior x 100. None si el anterior es 0: no hay base para comparar."""
    if anterior == 0:
        return None
    return (actual - anterior) / anterior * 100

"""Cálculos que SQLite no tiene o que no conviene hacer en SQL."""

from __future__ import annotations

from decimal import Decimal


def variacion_porcentual(actual: Decimal, anterior: Decimal) -> Decimal | None:
    """(actual - anterior) / anterior x 100. None si el anterior es 0: no hay base para comparar."""
    if anterior == 0:
        return None
    return (actual - anterior) / anterior * 100


def percentil(valores: list[float], p: float) -> float | None:
    """El percentil `p` (entre 0 y 1) por interpolación lineal entre los dos valores más cercanos.

    Es la definición de PERCENTILE_CONT de otros motores (SQLite no la tiene). Con un solo dato,
    ese dato; sin datos, None. Ej.: de [6, 24, 28], el P90 es 24 + (28 - 24) x 0,8 = 27,2.
    """
    if not valores:
        return None
    ordenados = sorted(valores)
    posicion = (len(ordenados) - 1) * p
    abajo = int(posicion)
    arriba = min(abajo + 1, len(ordenados) - 1)
    return ordenados[abajo] + (ordenados[arriba] - ordenados[abajo]) * (posicion - abajo)


def mediana(valores: list[float]) -> float | None:
    return percentil(valores, 0.5)

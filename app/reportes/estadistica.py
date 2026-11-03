"""Cálculos que SQLite no tiene o que no conviene hacer en SQL."""

from __future__ import annotations

from decimal import Decimal


def variacion_porcentual(actual: Decimal, anterior: Decimal) -> Decimal | None:
    """(actual - anterior) / anterior x 100. None si el anterior es 0: no hay base para comparar."""
    if anterior == 0:
        return None
    return (actual - anterior) / anterior * 100


def mediana(valores: list[float]) -> float | None:
    """El valor del medio de `valores` (promedio de los dos del medio si son pares).

    None si la lista está vacía. Es el percentil 50, pero se expone aparte porque es el
    caso más pedido y así queda claro en los reportes.
    """
    return percentil(valores, 50)


def percentil(valores: list[float], p: float) -> float | None:
    """Percentil `p` (0 a 100) con interpolación lineal, como el PERCENTILE_CONT que SQLite no tiene.

    Se calcula en Python porque SQLite no trae percentiles. None si no hay valores.
    Ej.: el P90 de [1..10] cae entre el 9º y el 10º valor (posición 9,1 -> 9,1).
    """
    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0]
    # Posición (0-based) del percentil dentro de la lista ordenada.
    posicion = (len(ordenados) - 1) * (p / 100)
    bajo = int(posicion)
    resto = posicion - bajo
    if bajo + 1 >= len(ordenados):
        return ordenados[bajo]
    # Interpolación lineal entre el valor `bajo` y el siguiente.
    return ordenados[bajo] + (ordenados[bajo + 1] - ordenados[bajo]) * resto

"""Funciones de fecha que usan varias clases del dominio."""

from datetime import date


def meses_entre(desde: date, hasta: date) -> int:
    """Cantidad de meses completos entre dos fechas.

    Ej.: del 15/01 al 14/02 hay 0 meses; del 15/01 al 15/02 hay 1.
    """
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    if hasta.day < desde.day:
        meses -= 1  # el último mes todavía no se completó
    return meses

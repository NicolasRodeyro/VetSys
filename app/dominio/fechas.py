"""Funciones de fecha que usan varias clases del dominio."""

import calendar
from datetime import date, timedelta


def meses_entre(desde: date, hasta: date) -> int:
    """Cantidad de meses completos entre dos fechas.

    Ej.: del 15/01 al 14/02 hay 0 meses; del 15/01 al 15/02 hay 1.
    """
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    if hasta.day < desde.day:
        meses -= 1  # el último mes todavía no se completó
    return meses


def sumar_meses(fecha: date, meses: int) -> date:
    """Primer día en que se cumplen `meses` meses completos desde `fecha`.

    Es la inversa de `meses_entre`: meses_entre(fecha, sumar_meses(fecha, n)) == n, y el
    día anterior todavía da n - 1. Por eso, si el día no existe en el mes destino
    (31/01 + 1 mes), el mes recién se completa el día 1 del mes siguiente (01/03).
    """
    indice = fecha.month - 1 + meses
    anio, mes = fecha.year + indice // 12, indice % 12 + 1
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    if fecha.day <= ultimo_dia:
        return date(anio, mes, fecha.day)
    return date(anio, mes, ultimo_dia) + timedelta(days=1)

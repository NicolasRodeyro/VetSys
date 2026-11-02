"""Conversión de lo que el usuario escribe (texto) a fechas, antes de llamar a los servicios.

Los demás datos (números, importes) los sanitizan los propios servicios (`validaciones.py`).
Un texto que no se puede convertir lanza EntradaInvalida, que la pantalla muestra al usuario.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.servicios import tiempo
from app.servicios.excepciones import EntradaInvalida

_FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y")
_FORMATOS_FECHA_HORA = ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M")


def a_fecha(texto: str | None, campo: str) -> date:
    limpio = " ".join((texto or "").split())
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(limpio, formato).date()
        except ValueError:
            continue
    raise EntradaInvalida(f"{campo}: escribí la fecha como AAAA-MM-DD (por ejemplo 2026-03-25)")


def a_fecha_hora(texto: str | None, campo: str) -> datetime:
    limpio = " ".join((texto or "").split())
    for formato in _FORMATOS_FECHA_HORA:
        try:
            return datetime.strptime(limpio, formato)
        except ValueError:
            continue
    raise EntradaInvalida(f"{campo}: escribí fecha y hora como AAAA-MM-DD HH:MM (por ejemplo 2026-03-25 10:30)")


def hoy_texto() -> str:
    return tiempo.hoy().isoformat()


def ahora_texto() -> str:
    """La fecha y hora actuales, en el formato que se escribe en los campos."""
    return tiempo.ahora().strftime("%Y-%m-%d %H:%M")


def en_pesos(monto: Decimal) -> str:
    """$ 12.500,00 (miles con punto, decimales con coma)."""
    return "$ " + f"{monto:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def en_texto(valor: date | datetime | None) -> str:
    """Una fecha o fecha-hora para mostrar en pantalla: dd/mm/aaaa (y hh:mm si la tiene)."""
    if valor is None:
        return ""
    return f"{valor:%d/%m/%Y %H:%M}" if isinstance(valor, datetime) else f"{valor:%d/%m/%Y}"

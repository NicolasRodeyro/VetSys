"""Cómo se escriben en las tablas de los reportes los montos, porcentajes, horas y meses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

SIN_DATO = "—"


def pesos(monto: Decimal) -> str:
    """$ 12.500,00 (miles con punto, decimales con coma), igual que el resto de la aplicación."""
    return "$ " + f"{monto:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def porcentaje(valor: Decimal | None) -> str:
    """+12,5 % / -3,0 %; «—» si no se puede calcular. Lleva signo porque es una variación."""
    if valor is None:
        return SIN_DATO
    return f"{valor:+.1f} %".replace(".", ",")


def tasa(valor: Decimal | None) -> str:
    """12,5 % sin signo: para proporciones (tasa de rechazo), no variaciones."""
    if valor is None:
        return SIN_DATO
    return f"{valor:.1f} %".replace(".", ",")


def horas(valor: float | None) -> str:
    """12,5 h; «—» si no hay dato (una muestra que todavía no completó ese tramo)."""
    if valor is None:
        return SIN_DATO
    return f"{valor:.1f} h".replace(".", ",")


def dias(valor: int) -> str:
    return f"{valor} día" + ("" if valor == 1 else "s")


def mes(primer_dia: date) -> str:
    return f"{primer_dia:%m/%Y}"


def fecha(valor: date) -> str:
    return f"{valor:%d/%m/%Y}"

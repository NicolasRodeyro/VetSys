"""Cómo se escriben en las tablas de los reportes los montos, porcentajes y meses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

SIN_DATO = "—"


def pesos(monto: Decimal) -> str:
    """$ 12.500,00 (miles con punto, decimales con coma), igual que el resto de la aplicación."""
    return "$ " + f"{monto:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def porcentaje(valor: Decimal | None) -> str:
    """+12,5 % / -3,0 %; «—» si no se puede calcular."""
    if valor is None:
        return SIN_DATO
    return f"{valor:+.1f} %".replace(".", ",")


def mes(primer_dia: date) -> str:
    return f"{primer_dia:%m/%Y}"

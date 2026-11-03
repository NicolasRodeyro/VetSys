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


def horas(valor: float | None) -> str:
    """5,5 h; «—» si no hay dato."""
    return SIN_DATO if valor is None else f"{valor:.1f} h".replace(".", ",")


def tasa(parte: int, total: int) -> str:
    """33,3 % (de parte sobre total); «—» si el total es 0."""
    return SIN_DATO if total == 0 else f"{parte / total * 100:.1f} %".replace(".", ",")


# Los códigos de motivo de rechazo, para leer en pantalla (los mismos que usa la interfaz).
MOTIVOS = {
    "PRECINTO_ROTO": "Precinto roto",
    "TEMPERATURA_FUERA_DE_RANGO": "Temperatura fuera de rango",
}


def motivo(codigo: str) -> str:
    return MOTIVOS.get(codigo, codigo)

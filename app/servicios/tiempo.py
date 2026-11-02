"""El reloj del sistema, en un solo lugar para poder reemplazarlo en los tests."""

from datetime import date, datetime


def ahora() -> datetime:
    return datetime.now().replace(microsecond=0)


def hoy() -> date:
    return ahora().date()

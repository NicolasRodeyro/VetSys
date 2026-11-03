"""Quién transportó cada remito: lo comparten los reportes de tiempos y de rechazo.

Un remito puede tener varios tramos con distintos transportistas. Regla de los reportes: una
muestra cuenta **una vez por cada transportista que intervino** en su remito. Si el remito no
tiene tramos registrados, se agrupa bajo SIN_TRAMOS.
"""

from __future__ import annotations

import sqlite3

SIN_TRAMOS = "Sin tramos registrados"


def transportistas_por_remito(conexion: sqlite3.Connection) -> dict[int, list[str]]:
    """remito_id -> transportistas que intervinieron, sin repetir y en orden alfabético."""
    filas = conexion.execute("SELECT DISTINCT remito_id, transportista FROM tramos_envio ORDER BY transportista")
    resultado: dict[int, list[str]] = {}
    for fila in filas:
        resultado.setdefault(fila["remito_id"], []).append(fila["transportista"])
    return resultado


def de_un_remito(por_remito: dict[int, list[str]], remito_id: int) -> list[str]:
    return por_remito.get(remito_id) or [SIN_TRAMOS]

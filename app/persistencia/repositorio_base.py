"""Base de los repositorios: acceso a la conexión y al mapa de identidad."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

from app.persistencia.identidad import MapaIdentidad, ObjetoNoGuardado

if TYPE_CHECKING:
    from app.persistencia.contexto import Contexto


class Repositorio:
    """Un repositorio por agregado. El SQL va siempre parametrizado (`?`)."""

    def __init__(self, contexto: Contexto) -> None:
        self.ctx = contexto

    @property
    def cx(self) -> sqlite3.Connection:
        return self.ctx.conexion

    @property
    def mapa(self) -> MapaIdentidad:
        return self.ctx.mapa

    def _una(self, sql: str, parametros: tuple = ()) -> sqlite3.Row | None:
        return self.cx.execute(sql, parametros).fetchone()

    def _todas(self, sql: str, parametros: tuple = ()) -> list[sqlite3.Row]:
        return self.cx.execute(sql, parametros).fetchall()

    def _insertar(self, sql: str, parametros: tuple = ()) -> int:
        return self.cx.execute(sql, parametros).lastrowid

    def _contar(self, sql: str, parametros: tuple = ()) -> int:
        return self.cx.execute(sql, parametros).fetchone()[0]

    def _id(self, tipo: str, objeto: Any) -> int:
        """Id de un objeto que tiene que estar guardado, o error claro."""
        id_ = self.mapa.id_de(tipo, objeto)
        if id_ is None:
            raise ObjetoNoGuardado(
                f"Hay que guardar primero el objeto de tipo '{tipo}' antes de guardar lo que depende de él"
            )
        return id_

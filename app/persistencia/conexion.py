"""Conexión a SQLite.

La base es un único archivo. Por defecto es `vetsys.db` en la raíz del repo;
se puede cambiar con la variable DATABASE_PATH (archivo `.env`, opcional).
Una ruta relativa se interpreta desde la raíz del repo.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent.parent
RUTA_POR_DEFECTO = "vetsys.db"


def obtener_conexion(ruta: str | Path | None = None) -> sqlite3.Connection:
    load_dotenv()
    destino = Path(ruta or os.environ.get("DATABASE_PATH") or RUTA_POR_DEFECTO)
    if not destino.is_absolute():
        destino = RAIZ / destino
    conexion = sqlite3.connect(destino)
    # Permite leer las columnas por nombre: fila["nombre"].
    conexion.row_factory = sqlite3.Row
    # SQLite no controla las claves foráneas salvo que se lo pidamos en cada conexión.
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


@contextmanager
def transaccion(ruta: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Abre una conexión y la usa como una sola transacción.

    Si el bloque termina bien se hace commit; si lanza una excepción se hace
    rollback de todo y la excepción se vuelve a lanzar. Cada caso de uso de
    servicios/ corre dentro de un `with transaccion() as conexion:`.
    """
    conexion = obtener_conexion(ruta)
    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()

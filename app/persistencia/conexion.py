"""Conexión a PostgreSQL.

La cadena de conexión sale de la variable DATABASE_URL (archivo .env).
Cambiando solo esa variable se puede apuntar a Supabase o a un Postgres local.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv


def obtener_conexion() -> psycopg.Connection:
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL en el archivo .env")
    return psycopg.connect(url)


@contextmanager
def transaccion() -> Iterator[psycopg.Connection]:
    """Abre una conexión y la usa como una sola transacción.

    Si el bloque termina bien se hace commit; si lanza una excepción se hace
    rollback de todo y la excepción se vuelve a lanzar. Cada caso de uso de
    servicios/ corre dentro de un `with transaccion() as conexion:`.
    """
    conexion = obtener_conexion()
    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()

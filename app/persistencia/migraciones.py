"""Migraciones de la base: aplica en orden los archivos de db/migraciones/ que faltan.

Lo usan `scripts/migrar.py` y el arranque de la aplicación (así la base se crea sola
la primera vez). Si el archivo de la base no existe, SQLite lo crea. Las migraciones
aplicadas se anotan en la tabla `migraciones_aplicadas`. Cada archivo se aplica en su
propia transacción junto con su anotación: si un archivo falla, no queda aplicado a
medias ni anotado.
"""

import sqlite3
from pathlib import Path

from app.persistencia.conexion import RAIZ, transaccion

CARPETA_MIGRACIONES = RAIZ / "db" / "migraciones"


def crear_tabla_de_control() -> None:
    with transaccion() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS migraciones_aplicadas (
                nombre      TEXT PRIMARY KEY,
                aplicada_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def migraciones_ya_aplicadas() -> set[str]:
    with transaccion() as conexion:
        filas = conexion.execute("SELECT nombre FROM migraciones_aplicadas").fetchall()
    return {fila["nombre"] for fila in filas}


def dividir_sentencias(sql: str) -> list[str]:
    """Separa un script en sentencias. Respeta los triggers (BEGIN ... END;)."""
    sentencias: list[str] = []
    actual = ""
    for linea in sql.splitlines(keepends=True):
        actual += linea
        if sqlite3.complete_statement(actual):
            sentencias.append(actual.strip())
            actual = ""
    if actual.strip():
        sentencias.append(actual.strip())
    return sentencias


def aplicar(archivo: Path) -> None:
    sentencias = dividir_sentencias(archivo.read_text(encoding="utf-8"))
    with transaccion() as conexion:
        # SQLite solo abre la transacción sola antes de INSERT/UPDATE/DELETE;
        # como una migración tiene CREATE TABLE, la abrimos a mano.
        conexion.execute("BEGIN")
        for sentencia in sentencias:
            conexion.execute(sentencia)
        conexion.execute(
            "INSERT INTO migraciones_aplicadas (nombre) VALUES (?)", (archivo.name,)
        )


def migrar() -> list[str]:
    """Aplica las migraciones pendientes. Devuelve los nombres de las que aplicó
    (lista vacía si la base ya estaba al día). Se puede llamar las veces que haga falta."""
    crear_tabla_de_control()
    aplicadas = migraciones_ya_aplicadas()

    # El orden lo da el prefijo numérico del nombre: 001_..., 002_..., etc.
    pendientes = [
        archivo
        for archivo in sorted(CARPETA_MIGRACIONES.glob("*.sql"))
        if archivo.name not in aplicadas
    ]
    for archivo in pendientes:
        aplicar(archivo)
    return [archivo.name for archivo in pendientes]

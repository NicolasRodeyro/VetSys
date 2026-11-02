"""Carga de los datos de prueba (db/seed.sql): clínicas, veterinarios, catálogo de análisis,
clientes y mascotas. Lo usan `scripts/sembrar.py` y el botón de la aplicación."""

from app.persistencia.conexion import RAIZ, obtener_conexion

ARCHIVO_SEED = RAIZ / "db" / "seed.sql"


def base_vacia() -> bool:
    """True si todavía no hay ninguna clínica cargada (no se puede operar sin catálogos)."""
    conexion = obtener_conexion()
    try:
        return conexion.execute("SELECT COUNT(*) FROM clinicas").fetchone()[0] == 0
    finally:
        conexion.close()


def cargar() -> bool:
    """Carga los datos de prueba. Devuelve False (sin hacer nada) si la base ya tiene datos."""
    conexion = obtener_conexion()
    try:
        if conexion.execute("SELECT COUNT(*) FROM clinicas").fetchone()[0]:
            return False
        sql = ARCHIVO_SEED.read_text(encoding="utf-8")
        try:
            # Se carga todo o nada: si alguna sentencia falla, se deshace.
            conexion.executescript("BEGIN;\n" + sql + "\nCOMMIT;")
        except Exception:
            if conexion.in_transaction:
                conexion.rollback()
            raise
        return True
    finally:
        conexion.close()

"""Aplica en orden las migraciones de db/migraciones/ que todavía no se aplicaron.

Uso (desde la raíz del repo):  python scripts/migrar.py

Las migraciones aplicadas se anotan en la tabla `migraciones_aplicadas`.
Cada archivo se aplica en su propia transacción junto con su anotación:
si un archivo falla, no queda aplicado a medias ni anotado.
"""

import sys
from pathlib import Path

# Permite importar el paquete `app` al correr el script directamente.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.persistencia.conexion import transaccion  # noqa: E402

CARPETA_MIGRACIONES = RAIZ / "db" / "migraciones"


def crear_tabla_de_control() -> None:
    with transaccion() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS migraciones_aplicadas (
                nombre      TEXT PRIMARY KEY,
                aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def migraciones_ya_aplicadas() -> set[str]:
    with transaccion() as conexion:
        filas = conexion.execute("SELECT nombre FROM migraciones_aplicadas").fetchall()
    return {fila[0] for fila in filas}


def aplicar(archivo: Path) -> None:
    with transaccion() as conexion:
        conexion.execute(archivo.read_text(encoding="utf-8"))
        conexion.execute(
            "INSERT INTO migraciones_aplicadas (nombre) VALUES (%s)", (archivo.name,)
        )


def main() -> None:
    crear_tabla_de_control()
    aplicadas = migraciones_ya_aplicadas()

    # El orden lo da el prefijo numérico del nombre: 001_..., 002_..., etc.
    pendientes = [
        archivo
        for archivo in sorted(CARPETA_MIGRACIONES.glob("*.sql"))
        if archivo.name not in aplicadas
    ]

    if not pendientes:
        print("Conexión OK. No hay migraciones pendientes.")
        return

    for archivo in pendientes:
        print(f"Aplicando {archivo.name}...")
        aplicar(archivo)
    print(f"Listo: {len(pendientes)} migración(es) aplicada(s).")


if __name__ == "__main__":
    main()

"""Aplica en orden las migraciones de db/migraciones/ que todavía no se aplicaron.

Uso (desde la raíz del repo):  python scripts/migrar.py

La lógica está en app/persistencia/migraciones.py (la aplicación también la usa al arrancar).
"""

import sys
from pathlib import Path

# Permite importar el paquete `app` al correr el script directamente.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.persistencia.migraciones import migrar  # noqa: E402


def main() -> None:
    aplicadas = migrar()
    if not aplicadas:
        print("Base OK. No hay migraciones pendientes.")
        return
    for nombre in aplicadas:
        print(f"Aplicada {nombre}")
    print(f"Listo: {len(aplicadas)} migración(es) aplicada(s).")


if __name__ == "__main__":
    main()

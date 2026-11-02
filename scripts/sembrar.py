"""Carga los datos de prueba de db/seed.sql en la base.

Uso (desde la raíz del repo):  python scripts/sembrar.py

Hay que haber corrido antes `python scripts/migrar.py`. No es necesario para usar
el sistema: solo sirve para tener clínicas, clientes y mascotas con los que probar.
Si la base ya tiene datos no hace nada, para no duplicarlos.
"""

import sys
from pathlib import Path

# Permite importar el paquete `app` al correr el script directamente.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.persistencia.datos_de_prueba import cargar  # noqa: E402


def main() -> None:
    if cargar():
        print("Datos de prueba cargados.")
    else:
        print("La base ya tiene datos: no se carga el seed otra vez.")


if __name__ == "__main__":
    main()

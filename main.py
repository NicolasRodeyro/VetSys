"""Punto de entrada de VetSys:  python main.py

La primera vez crea la base de datos (vetsys.db). Si está vacía, la ventana ofrece
cargar datos de prueba (clínicas, veterinarios, análisis, clientes y mascotas).
"""

import flet as ft

from app.ui.aplicacion import main

if __name__ == "__main__":
    ft.run(main)

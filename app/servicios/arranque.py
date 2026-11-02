"""Preparación de la base al iniciar la aplicación (para que la interfaz no toque la persistencia)."""

from __future__ import annotations

from app.persistencia import datos_de_prueba, migraciones


def preparar_base() -> None:
    """Crea la base la primera vez y aplica las migraciones pendientes."""
    migraciones.migrar()


def base_vacia() -> bool:
    """True si faltan los catálogos (clínicas, veterinarios, análisis): no se puede operar."""
    return datos_de_prueba.base_vacia()


def cargar_datos_de_prueba() -> bool:
    """Carga clínicas, veterinarios, análisis, clientes y mascotas de ejemplo. False si ya había datos."""
    return datos_de_prueba.cargar()

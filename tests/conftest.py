"""Fixtures comunes a los tests de integración y de servicios: una base SQLite temporal
ya migrada (y, si se pide, con los datos de prueba)."""

import sqlite3
from datetime import datetime

import pytest

from app.persistencia import datos_de_prueba, migraciones
from app.persistencia.conexion import obtener_conexion
from app.servicios import tiempo


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Crea una base temporal y le aplica todas las migraciones reales de db/migraciones/.
    Nunca toca vetsys.db."""
    ruta = tmp_path / "prueba.db"
    monkeypatch.setenv("DATABASE_PATH", str(ruta))
    migraciones.migrar()
    return ruta


@pytest.fixture
def cx(base) -> sqlite3.Connection:
    """Conexión a la base migrada (con claves foráneas activas)."""
    conexion = obtener_conexion()
    yield conexion
    conexion.close()


@pytest.fixture
def sesion(base):
    """Fábrica de contextos de persistencia. Cada llamada abre una conexión y un mapa de
    identidad nuevos, como lo haría cada caso de uso: sirve para guardar en una sesión
    y volver a cargar en otra, y comprobar que lo guardado alcanza."""
    from app.persistencia.contexto import Contexto

    abiertas = []

    def _abrir() -> Contexto:
        conexion = obtener_conexion()
        abiertas.append(conexion)
        return Contexto(conexion)

    yield _abrir
    for conexion in abiertas:
        conexion.close()


@pytest.fixture
def con_seed(base):
    """La base migrada con los datos de prueba de db/seed.sql (clínicas, veterinarios,
    catálogo de análisis, 10 clientes con sus mascotas)."""
    datos_de_prueba.cargar()


AHORA = datetime(2026, 11, 2, 12, 0, 0)


@pytest.fixture
def ahora(monkeypatch) -> datetime:
    """Congela el reloj del sistema en el 02/11/2026 12:00."""
    monkeypatch.setattr(tiempo, "ahora", lambda: AHORA)
    return AHORA

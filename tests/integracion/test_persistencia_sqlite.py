"""Tests de la persistencia base: transacciones y migraciones sobre SQLite."""

import sqlite3
from pathlib import Path

import pytest

from app.persistencia import migraciones
from app.persistencia.conexion import transaccion


@pytest.fixture
def ruta_db(tmp_path, monkeypatch) -> Path:
    ruta = tmp_path / "prueba.db"
    monkeypatch.setenv("DATABASE_PATH", str(ruta))
    return ruta


@pytest.fixture
def migrar(ruta_db, tmp_path, monkeypatch):
    """El módulo de migraciones apuntando a una carpeta de migraciones temporal."""
    carpeta = tmp_path / "migraciones"
    carpeta.mkdir()
    monkeypatch.setattr(migraciones, "CARPETA_MIGRACIONES", carpeta)
    monkeypatch.setattr(migraciones, "carpeta", carpeta, raising=False)
    return migraciones


def tablas() -> set[str]:
    with transaccion() as conexion:
        filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {fila["name"] for fila in filas}


# --- transacciones ---

def test_transaccion_hace_commit_si_todo_sale_bien(ruta_db):
    with transaccion() as c:
        c.execute("CREATE TABLE t (x INTEGER)")
        c.execute("INSERT INTO t VALUES (?)", (1,))
    with transaccion() as c:
        assert c.execute("SELECT x FROM t").fetchone()["x"] == 1


def test_transaccion_hace_rollback_si_hay_error(ruta_db):
    with transaccion() as c:
        c.execute("CREATE TABLE t (x INTEGER)")
    with pytest.raises(RuntimeError):
        with transaccion() as c:
            c.execute("INSERT INTO t VALUES (?)", (1,))
            raise RuntimeError("falló el caso de uso")
    with transaccion() as c:
        assert c.execute("SELECT COUNT(*) AS n FROM t").fetchone()["n"] == 0


def test_claves_foraneas_estan_activadas(ruta_db):
    with transaccion() as c:
        c.execute("CREATE TABLE padre (id INTEGER PRIMARY KEY)")
        c.execute("CREATE TABLE hijo (padre_id INTEGER REFERENCES padre(id))")
    with pytest.raises(sqlite3.IntegrityError):
        with transaccion() as c:
            c.execute("INSERT INTO hijo VALUES (?)", (99,))


# --- migraciones ---

def test_migrar_aplica_y_registra_las_migraciones(migrar):
    (migrar.carpeta / "001_uno.sql").write_text("CREATE TABLE uno (id INTEGER);")
    (migrar.carpeta / "002_dos.sql").write_text("CREATE TABLE dos (id INTEGER);")
    migrar.migrar()
    assert {"uno", "dos", "migraciones_aplicadas"} <= tablas()
    assert migrar.migraciones_ya_aplicadas() == {"001_uno.sql", "002_dos.sql"}


def test_migrar_es_idempotente(migrar):
    (migrar.carpeta / "001_uno.sql").write_text("CREATE TABLE uno (id INTEGER);")
    migrar.migrar()
    migrar.migrar()  # si reaplicara, fallaría: la tabla ya existe
    assert migrar.migraciones_ya_aplicadas() == {"001_uno.sql"}


def test_migracion_que_falla_no_queda_a_medias_ni_anotada(migrar):
    (migrar.carpeta / "001_rota.sql").write_text(
        "CREATE TABLE buena (id INTEGER);\nINSERT INTO no_existe VALUES (1);"
    )
    with pytest.raises(sqlite3.OperationalError):
        migrar.migrar()
    assert "buena" not in tablas()
    assert migrar.migraciones_ya_aplicadas() == set()


def test_migrar_soporta_triggers(migrar):
    """El trigger de trazabilidad inmutable (Fase 6) tiene BEGIN...END con ';' adentro."""
    (migrar.carpeta / "001_trigger.sql").write_text(
        """
        CREATE TABLE cambios (id INTEGER PRIMARY KEY, dato TEXT);
        CREATE TRIGGER cambios_sin_update BEFORE UPDATE ON cambios
        BEGIN
            SELECT RAISE(ABORT, 'La trazabilidad es inmutable');
        END;
        """
    )
    migrar.migrar()
    with transaccion() as c:
        c.execute("INSERT INTO cambios (dato) VALUES (?)", ("a",))
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        with transaccion() as c:
            c.execute("UPDATE cambios SET dato = ?", ("b",))


def test_migrar_informa_cuales_aplico(migrar):
    (migrar.carpeta / "001_uno.sql").write_text("CREATE TABLE uno (id INTEGER);")
    (migrar.carpeta / "002_dos.sql").write_text("CREATE TABLE dos (id INTEGER);")
    assert migrar.migrar() == ["001_uno.sql", "002_dos.sql"]
    assert migrar.migrar() == []  # ya estaba al día

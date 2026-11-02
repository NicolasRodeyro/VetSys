"""002_trazabilidad_inmutable.sql: los cambios de estado no se modifican ni se borran."""

import sqlite3

import pytest


@pytest.fixture
def cambio(cx) -> int:
    """Una muestra con un cambio de estado rechazado (con motivo) ya registrado."""
    especie = cx.execute("INSERT INTO especies (nombre) VALUES ('Perro')").lastrowid
    cliente = cx.execute("INSERT INTO clientes (dni, nombre, apellido) VALUES ('1', 'Ana', 'Paz')").lastrowid
    mascota = cx.execute(
        "INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento) "
        "VALUES (?, ?, 'Toby', 'MACHO', '2026-01-10')", (cliente, especie)).lastrowid
    clinica = cx.execute("INSERT INTO clinicas (nombre) VALUES ('Centro')").lastrowid
    vet = cx.execute(
        "INSERT INTO veterinarios (matricula, nombre, apellido, clinica_id) VALUES ('M', 'L', 'G', ?)", (clinica,)).lastrowid
    consulta = cx.execute(
        "INSERT INTO consultas (tipo, fecha_hora, mascota_id, veterinario_id) "
        "VALUES ('CONSULTA', '2026-05-10T11:00:00', ?, ?)", (mascota, vet)).lastrowid
    tipo = cx.execute(
        "INSERT INTO tipos_analisis (nombre, precio, tipo_muestra, temp_min, temp_max, horas_max_transito) "
        "VALUES ('Hemograma', '1', 'Sangre', 2, 8, 24)").lastrowid
    orden = cx.execute(
        "INSERT INTO ordenes_derivacion (consulta_id, tipo_analisis_id, prioridad) VALUES (?, ?, 'NORMAL')",
        (consulta, tipo)).lastrowid
    muestra = cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'RECHAZADA')", (orden,)).lastrowid
    cambio = cx.execute(
        "INSERT INTO cambios_estado (muestra_id, anterior, nuevo, fecha_hora, responsable) "
        "VALUES (?, 'EN_TRANSITO', 'RECHAZADA', '2026-06-01T14:00:00', 'Bioq. Pérez')", (muestra,)).lastrowid
    cx.execute("INSERT INTO cambio_estado_motivos (cambio_id, motivo) VALUES (?, 'PRECINTO_ROTO')", (cambio,))
    cx.commit()
    return cambio


def test_se_pueden_agregar_cambios_de_estado(cx, cambio):
    muestra = cx.execute("SELECT muestra_id FROM cambios_estado").fetchone()[0]
    cx.execute(
        "INSERT INTO cambios_estado (muestra_id, anterior, nuevo, fecha_hora, responsable) "
        "VALUES (?, NULL, 'EXTRAIDA', '2026-06-01T09:00:00', 'Dr. Gómez')", (muestra,))
    assert cx.execute("SELECT COUNT(*) FROM cambios_estado").fetchone()[0] == 2


def test_el_trigger_bloquea_el_update_de_un_cambio_de_estado(cx, cambio):
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        cx.execute("UPDATE cambios_estado SET responsable = 'Otro' WHERE id = ?", (cambio,))


def test_el_trigger_bloquea_cambiar_el_estado_registrado(cx, cambio):
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        cx.execute("UPDATE cambios_estado SET nuevo = 'RECIBIDA' WHERE id = ?", (cambio,))


def test_el_trigger_bloquea_el_delete_de_un_cambio_de_estado(cx, cambio):
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        cx.execute("DELETE FROM cambios_estado WHERE id = ?", (cambio,))


def test_los_motivos_del_rechazo_tambien_son_inmutables(cx, cambio):
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        cx.execute("UPDATE cambio_estado_motivos SET motivo = 'TEMPERATURA_FUERA_DE_RANGO'")
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        cx.execute("DELETE FROM cambio_estado_motivos")


def test_despues_de_los_intentos_el_registro_sigue_intacto(cx, cambio):
    for sql in ("UPDATE cambios_estado SET responsable = 'X'", "DELETE FROM cambios_estado"):
        with pytest.raises(sqlite3.IntegrityError):
            cx.execute(sql)
    fila = cx.execute("SELECT responsable, nuevo FROM cambios_estado WHERE id = ?", (cambio,)).fetchone()
    assert (fila["responsable"], fila["nuevo"]) == ("Bioq. Pérez", "RECHAZADA")

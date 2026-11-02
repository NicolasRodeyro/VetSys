"""El esquema protege las reglas de negocio también desde la base de datos."""

import sqlite3

import pytest


def insertar(cx, sql, *params) -> int:
    return cx.execute(sql, params).lastrowid


@pytest.fixture
def datos(cx):
    """Filas mínimas para poder probar las tablas dependientes."""
    especie = insertar(cx, "INSERT INTO especies (nombre) VALUES ('Perro')")
    cliente = insertar(cx, "INSERT INTO clientes (dni, nombre, apellido) VALUES ('1', 'Ana', 'Paz')")
    mascota = insertar(
        cx,
        "INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento) "
        "VALUES (?, ?, 'Toby', 'MACHO', '2026-01-10')", cliente, especie,
    )
    clinica = insertar(cx, "INSERT INTO clinicas (nombre) VALUES ('Centro')")
    vet = insertar(
        cx, "INSERT INTO veterinarios (matricula, nombre, apellido, clinica_id) "
        "VALUES ('MP1', 'Laura', 'Gómez', ?)", clinica,
    )
    consulta = insertar(
        cx, "INSERT INTO consultas (tipo, fecha_hora, mascota_id, veterinario_id) "
        "VALUES ('CONSULTA', '2026-05-10T11:00:00', ?, ?)", mascota, vet,
    )
    tipo = insertar(
        cx, "INSERT INTO tipos_analisis (nombre, precio, tipo_muestra, temp_min, temp_max, "
        "horas_max_transito) VALUES ('Hemograma', '12500', 'Sangre', 2, 8, 24)",
    )
    orden = insertar(
        cx, "INSERT INTO ordenes_derivacion (consulta_id, tipo_analisis_id, prioridad) "
        "VALUES (?, ?, 'NORMAL')", consulta, tipo,
    )
    cx.commit()
    return dict(especie=especie, cliente=cliente, mascota=mascota, orden=orden, clinica=clinica)


# --- Claves foráneas y campos obligatorios ---

def test_toda_mascota_necesita_un_responsable_que_exista(cx, datos):
    with pytest.raises(sqlite3.IntegrityError):  # cliente inexistente
        cx.execute(
            "INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento) "
            "VALUES (999, ?, 'Rex', 'MACHO', '2026-01-01')", (datos["especie"],),
        )


def test_mascota_sin_responsable_es_rechazada_por_la_base(cx, datos):
    with pytest.raises(sqlite3.IntegrityError, match="NOT NULL"):
        cx.execute(
            "INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento) "
            "VALUES (NULL, ?, 'Rex', 'MACHO', '2026-01-01')", (datos["especie"],),
        )


def test_dni_de_cliente_es_unico(cx, datos):
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        cx.execute("INSERT INTO clientes (dni, nombre, apellido) VALUES ('1', 'Otro', 'Cliente')")


# --- CHECK de valores válidos ---

@pytest.mark.parametrize("sexo", ["macho", "OTRO", ""])
def test_sexo_invalido_es_rechazado(cx, datos, sexo):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        cx.execute(
            "INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento) "
            "VALUES (?, ?, 'Rex', ?, '2026-01-01')", (datos["cliente"], datos["especie"], sexo),
        )


def test_estado_de_muestra_invalido_es_rechazado(cx, datos):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'PERDIDA')", (datos["orden"],))


def test_estado_de_remito_invalido_es_rechazado(cx, datos):
    lab = insertar(cx, "INSERT INTO laboratorios (nombre) VALUES ('Central')")
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        cx.execute(
            "INSERT INTO remitos (numero, clinica_id, laboratorio_id, estado) "
            "VALUES ('R-1', ?, ?, 'ANULADO')", (datos["clinica"], lab),  # el remito no tiene Anulado
        )


def test_rango_de_temperatura_invertido_es_rechazado(cx):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        cx.execute("INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) VALUES ('C', 5, 8, 2)")


def test_capacidad_debe_ser_positiva(cx):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        cx.execute("INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) VALUES ('C', 0, 2, 8)")


def test_el_precinto_esta_completo_o_no_esta(cx):
    cx.execute("INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) VALUES ('A', 5, 2, 8)")
    cx.execute(
        "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max, precinto_numero, "
        "precinto_fecha, precinto_responsable) VALUES ('B', 5, 2, 8, 'P1', '2026-06-01T10:00:00', 'Ruiz')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):  # precinto a medias
        cx.execute(
            "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max, precinto_numero) "
            "VALUES ('C', 5, 2, 8, 'P2')"
        )


# --- Una muestra activa por orden (también en la base) ---

def test_la_base_no_permite_dos_muestras_activas_en_la_misma_orden(cx, datos):
    cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'EXTRAIDA')", (datos["orden"],))
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'EMPAQUETADA')", (datos["orden"],))


def test_la_base_permite_re_extraer_si_la_anterior_fue_rechazada(cx, datos):
    cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'RECHAZADA')", (datos["orden"],))
    cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'RECHAZADA')", (datos["orden"],))
    cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, 'EXTRAIDA')", (datos["orden"],))
    assert cx.execute("SELECT COUNT(*) FROM muestras").fetchone()[0] == 3


# --- Una muestra / una conservadora / un resultado / un comprobante ---

def test_una_muestra_no_puede_estar_en_dos_conservadoras(cx, datos):
    muestra = insertar(cx, "INSERT INTO muestras (orden_id, estado) VALUES (?, 'EXTRAIDA')", datos["orden"])
    a = insertar(cx, "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) VALUES ('A', 5, 2, 8)")
    b = insertar(cx, "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) VALUES ('B', 5, 2, 8)")
    cx.execute("INSERT INTO conservadora_muestras (conservadora_id, muestra_id) VALUES (?, ?)", (a, muestra))
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        cx.execute("INSERT INTO conservadora_muestras (conservadora_id, muestra_id) VALUES (?, ?)", (b, muestra))


def test_una_consulta_tiene_un_solo_comprobante(cx, datos):
    consulta = cx.execute("SELECT id FROM consultas").fetchone()[0]
    cx.execute("INSERT INTO comprobantes (consulta_id, fecha_hora) VALUES (?, '2026-05-10T12:00:00')", (consulta,))
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        cx.execute("INSERT INTO comprobantes (consulta_id, fecha_hora) VALUES (?, '2026-05-10T12:30:00')", (consulta,))

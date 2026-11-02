-- Esquema inicial de VetSys (SQLite).
--
-- Convenciones:
--  * Las fechas se guardan como texto ISO 8601 (hora local, sin zona).
--  * Los montos (Decimal) se guardan como TEXT para no perder exactitud.
--  * Los estados y tipos se guardan como texto, con un CHECK de los valores válidos.
--  * Los valores booleanos son INTEGER 0/1.

-- ============================================================
-- Clientes, mascotas e historias clínicas
-- ============================================================

CREATE TABLE especies (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE vacunas_obligatorias (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    especie_id            INTEGER NOT NULL REFERENCES especies(id),
    nombre                TEXT NOT NULL,
    edad_aplicacion_meses INTEGER NOT NULL CHECK (edad_aplicacion_meses >= 0),
    refuerzo_cada_meses   INTEGER CHECK (refuerzo_cada_meses IS NULL OR refuerzo_cada_meses > 0),
    UNIQUE (especie_id, nombre)
);
CREATE INDEX idx_vacunas_obligatorias_especie ON vacunas_obligatorias(especie_id);

CREATE TABLE clientes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    dni       TEXT NOT NULL UNIQUE,
    nombre    TEXT NOT NULL,
    apellido  TEXT NOT NULL,
    telefono  TEXT NOT NULL DEFAULT '',
    email     TEXT NOT NULL DEFAULT '',
    direccion TEXT NOT NULL DEFAULT ''
);

-- Toda mascota tiene un responsable: cliente_id es obligatorio.
CREATE TABLE mascotas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id       INTEGER NOT NULL REFERENCES clientes(id),
    especie_id       INTEGER NOT NULL REFERENCES especies(id),
    nombre           TEXT NOT NULL,
    sexo             TEXT NOT NULL CHECK (sexo IN ('MACHO', 'HEMBRA')),
    fecha_nacimiento TEXT NOT NULL
);
CREATE INDEX idx_mascotas_cliente ON mascotas(cliente_id);
CREATE INDEX idx_mascotas_especie ON mascotas(especie_id);

-- La historia clínica es una por mascota (composición).
CREATE TABLE historias_clinicas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    mascota_id   INTEGER NOT NULL UNIQUE REFERENCES mascotas(id),
    alergias     TEXT NOT NULL DEFAULT '',
    antecedentes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE vacunas_aplicadas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    historia_id INTEGER NOT NULL REFERENCES historias_clinicas(id),
    vacuna_id   INTEGER NOT NULL REFERENCES vacunas_obligatorias(id),
    fecha       TEXT NOT NULL
);
CREATE INDEX idx_vacunas_aplicadas_historia ON vacunas_aplicadas(historia_id);
CREATE INDEX idx_vacunas_aplicadas_fecha ON vacunas_aplicadas(fecha);

-- ============================================================
-- Atención clínica
-- ============================================================

CREATE TABLE clinicas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    direccion TEXT NOT NULL DEFAULT ''
);

CREATE TABLE laboratorios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    direccion TEXT NOT NULL DEFAULT ''
);

CREATE TABLE veterinarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula  TEXT NOT NULL UNIQUE,
    nombre     TEXT NOT NULL,
    apellido   TEXT NOT NULL,
    clinica_id INTEGER NOT NULL REFERENCES clinicas(id)
);
CREATE INDEX idx_veterinarios_clinica ON veterinarios(clinica_id);

CREATE TABLE turnos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    veterinario_id   INTEGER NOT NULL REFERENCES veterinarios(id),
    mascota_id       INTEGER NOT NULL REFERENCES mascotas(id),
    inicio           TEXT NOT NULL,
    duracion_minutos INTEGER NOT NULL CHECK (duracion_minutos > 0),
    estado           TEXT NOT NULL CHECK (estado IN ('PROGRAMADO', 'CANCELADO'))
);
CREATE INDEX idx_turnos_veterinario ON turnos(veterinario_id);
CREATE INDEX idx_turnos_mascota ON turnos(mascota_id);
CREATE INDEX idx_turnos_inicio ON turnos(inicio);

CREATE TABLE tipos_analisis (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre             TEXT NOT NULL UNIQUE,
    precio             TEXT NOT NULL,
    tipo_muestra       TEXT NOT NULL,
    temp_min           REAL NOT NULL,
    temp_max           REAL NOT NULL,
    horas_max_transito INTEGER NOT NULL CHECK (horas_max_transito > 0),
    CHECK (temp_min <= temp_max)
);

CREATE TABLE consultas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo           TEXT NOT NULL CHECK (tipo IN ('CONTROL', 'CONSULTA', 'URGENCIA')),
    fecha_hora     TEXT NOT NULL,
    mascota_id     INTEGER NOT NULL REFERENCES mascotas(id),
    veterinario_id INTEGER NOT NULL REFERENCES veterinarios(id),
    turno_id       INTEGER REFERENCES turnos(id),   -- opcional: las urgencias no tienen turno
    diagnostico    TEXT NOT NULL DEFAULT '',
    tratamiento    TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_consultas_mascota ON consultas(mascota_id);
CREATE INDEX idx_consultas_veterinario ON consultas(veterinario_id);
CREATE INDEX idx_consultas_fecha ON consultas(fecha_hora);

CREATE TABLE consulta_advertencias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id INTEGER NOT NULL REFERENCES consultas(id),
    texto       TEXT NOT NULL
);
CREATE INDEX idx_consulta_advertencias_consulta ON consulta_advertencias(consulta_id);

CREATE TABLE ordenes_derivacion (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id      INTEGER NOT NULL REFERENCES consultas(id),
    tipo_analisis_id INTEGER NOT NULL REFERENCES tipos_analisis(id),
    prioridad        TEXT NOT NULL CHECK (prioridad IN ('NORMAL', 'URGENTE'))
);
CREATE INDEX idx_ordenes_consulta ON ordenes_derivacion(consulta_id);
CREATE INDEX idx_ordenes_tipo_analisis ON ordenes_derivacion(tipo_analisis_id);

-- ============================================================
-- Muestras y su trazabilidad
-- ============================================================

CREATE TABLE muestras (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id INTEGER NOT NULL REFERENCES ordenes_derivacion(id),
    estado   TEXT NOT NULL CHECK (estado IN
        ('EXTRAIDA', 'EMPAQUETADA', 'EN_TRANSITO', 'RECIBIDA', 'ANALIZADA', 'RECHAZADA'))
);
CREATE INDEX idx_muestras_orden ON muestras(orden_id);
CREATE INDEX idx_muestras_estado ON muestras(estado);

-- Regla de negocio también en la base: una sola muestra activa (no rechazada) por orden.
CREATE UNIQUE INDEX uq_una_muestra_activa_por_orden
    ON muestras(orden_id) WHERE estado <> 'RECHAZADA';

-- Un renglón por cada cambio de estado. Es inmutable (ver 002_trazabilidad_inmutable.sql).
CREATE TABLE cambios_estado (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    muestra_id  INTEGER NOT NULL REFERENCES muestras(id),
    anterior    TEXT CHECK (anterior IS NULL OR anterior IN
        ('EXTRAIDA', 'EMPAQUETADA', 'EN_TRANSITO', 'RECIBIDA', 'ANALIZADA', 'RECHAZADA')),
    nuevo       TEXT NOT NULL CHECK (nuevo IN
        ('EXTRAIDA', 'EMPAQUETADA', 'EN_TRANSITO', 'RECIBIDA', 'ANALIZADA', 'RECHAZADA')),
    fecha_hora  TEXT NOT NULL,
    responsable TEXT NOT NULL,
    ubicacion   TEXT NOT NULL DEFAULT '',
    observacion TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_cambios_estado_muestra ON cambios_estado(muestra_id);
CREATE INDEX idx_cambios_estado_fecha ON cambios_estado(fecha_hora);

-- Motivos de un rechazo (puede haber más de uno por cambio).
CREATE TABLE cambio_estado_motivos (
    cambio_id INTEGER NOT NULL REFERENCES cambios_estado(id),
    motivo    TEXT NOT NULL CHECK (motivo IN ('PRECINTO_ROTO', 'TEMPERATURA_FUERA_DE_RANGO')),
    PRIMARY KEY (cambio_id, motivo)
);

-- ============================================================
-- Empaquetado y envío
-- ============================================================

-- El precinto es de la conservadora: o están sus tres datos o ninguno.
CREATE TABLE conservadoras (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo              TEXT NOT NULL UNIQUE,
    capacidad           INTEGER NOT NULL CHECK (capacidad > 0),
    temp_min            REAL NOT NULL,
    temp_max            REAL NOT NULL,
    precinto_numero      TEXT,
    precinto_fecha       TEXT,
    precinto_responsable TEXT,
    CHECK (temp_min <= temp_max),
    CHECK ((precinto_numero IS NULL AND precinto_fecha IS NULL AND precinto_responsable IS NULL)
        OR (precinto_numero IS NOT NULL AND precinto_fecha IS NOT NULL AND precinto_responsable IS NOT NULL))
);

-- Una muestra está como máximo en una conservadora. El id da el orden de empaquetado.
CREATE TABLE conservadora_muestras (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    conservadora_id INTEGER NOT NULL REFERENCES conservadoras(id),
    muestra_id      INTEGER NOT NULL UNIQUE REFERENCES muestras(id)
);
CREATE INDEX idx_conservadora_muestras_conservadora ON conservadora_muestras(conservadora_id);

CREATE TABLE remitos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    numero         TEXT NOT NULL UNIQUE,
    clinica_id     INTEGER NOT NULL REFERENCES clinicas(id),
    laboratorio_id INTEGER NOT NULL REFERENCES laboratorios(id),
    estado         TEXT NOT NULL CHECK (estado IN
        ('ABIERTO', 'CERRADO', 'EN_TRANSITO', 'RECIBIDO', 'RECIBIDO_PARCIAL', 'RECHAZADO'))
);
CREATE INDEX idx_remitos_clinica ON remitos(clinica_id);
CREATE INDEX idx_remitos_laboratorio ON remitos(laboratorio_id);
CREATE INDEX idx_remitos_estado ON remitos(estado);

-- Una conservadora viaja en un solo remito.
CREATE TABLE remito_conservadoras (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    remito_id       INTEGER NOT NULL REFERENCES remitos(id),
    conservadora_id INTEGER NOT NULL UNIQUE REFERENCES conservadoras(id)
);
CREATE INDEX idx_remito_conservadoras_remito ON remito_conservadoras(remito_id);

CREATE TABLE tramos_envio (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    remito_id     INTEGER NOT NULL REFERENCES remitos(id),
    orden         INTEGER NOT NULL CHECK (orden > 0),
    origen        TEXT NOT NULL,
    destino       TEXT NOT NULL,
    transportista TEXT NOT NULL,
    salida        TEXT NOT NULL,
    llegada       TEXT,
    temperatura   REAL,
    UNIQUE (remito_id, orden)
);
CREATE INDEX idx_tramos_envio_salida ON tramos_envio(salida);

CREATE TABLE recepciones (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    remito_id      INTEGER NOT NULL UNIQUE REFERENCES remitos(id),
    laboratorio_id INTEGER NOT NULL REFERENCES laboratorios(id),
    responsable    TEXT NOT NULL,
    fecha_hora     TEXT NOT NULL
);
CREATE INDEX idx_recepciones_laboratorio ON recepciones(laboratorio_id);
CREATE INDEX idx_recepciones_fecha ON recepciones(fecha_hora);

-- Un detalle por conservadora recibida.
CREATE TABLE detalles_recepcion (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    recepcion_id        INTEGER NOT NULL REFERENCES recepciones(id),
    conservadora_id     INTEGER NOT NULL REFERENCES conservadoras(id),
    estado_precinto     TEXT NOT NULL CHECK (estado_precinto IN ('INTACTO', 'ROTO')),
    temperatura_llegada REAL NOT NULL,
    observacion         TEXT NOT NULL DEFAULT '',
    aceptada            INTEGER NOT NULL CHECK (aceptada IN (0, 1)),
    UNIQUE (recepcion_id, conservadora_id)
);
CREATE INDEX idx_detalles_recepcion_conservadora ON detalles_recepcion(conservadora_id);

-- ============================================================
-- Resultados y cobro
-- ============================================================

-- Una muestra tiene como máximo un resultado.
CREATE TABLE resultados_analisis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    muestra_id    INTEGER NOT NULL UNIQUE REFERENCES muestras(id),
    responsable   TEXT NOT NULL,
    fecha_hora    TEXT NOT NULL,
    observaciones TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_resultados_fecha ON resultados_analisis(fecha_hora);

CREATE TABLE valores_resultado (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    resultado_id INTEGER NOT NULL REFERENCES resultados_analisis(id),
    parametro    TEXT NOT NULL,
    valor        REAL NOT NULL,
    unidad       TEXT NOT NULL,
    ref_min      REAL,
    ref_max      REAL
);
CREATE INDEX idx_valores_resultado_resultado ON valores_resultado(resultado_id);

-- Comprobante único por consulta, emitido al cerrarla.
CREATE TABLE comprobantes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id INTEGER NOT NULL UNIQUE REFERENCES consultas(id),
    fecha_hora  TEXT NOT NULL
);
CREATE INDEX idx_comprobantes_fecha ON comprobantes(fecha_hora);

CREATE TABLE items_comprobante (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    comprobante_id INTEGER NOT NULL REFERENCES comprobantes(id),
    descripcion    TEXT NOT NULL,
    monto          TEXT NOT NULL,
    es_laboratorio INTEGER NOT NULL CHECK (es_laboratorio IN (0, 1))
);
CREATE INDEX idx_items_comprobante_comprobante ON items_comprobante(comprobante_id);

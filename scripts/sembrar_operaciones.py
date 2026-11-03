"""Carga datos de prueba OPERATIVOS para que los reportes muestren información.

El seed normal (db/seed.sql) trae solo catálogos, clientes y mascotas. Sin operaciones, los
reportes de facturación, tiempos y rechazo salen vacíos. Este script agrega un historial de
unos meses: consultas con comprobantes, muestras que viajan y se procesan, y algunas rechazadas.

Es SOLO para demostración. Inserta las filas directamente (INSERT, nunca UPDATE/DELETE, así no
choca con el trigger de trazabilidad inmutable) con fechas elegidas a mano, porque los tiempos de
la trazabilidad los pone el reloj del sistema y no se pueden fijar desde los servicios.

Uso (desde la raíz del repo, después de migrar y sembrar el seed normal):
    python scripts/migrar.py
    python scripts/sembrar.py
    python scripts/sembrar_operaciones.py

Si ya hay muestras cargadas no hace nada, para no duplicar.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.persistencia.conexion import obtener_conexion  # noqa: E402

TRANSPORTISTAS = ["LogiFrío", "TransVet", "CadenaFría SA"]


def _uno(cx, sql, params=()):
    return cx.execute(sql, params).fetchone()[0]


def _operacion(cx, n, *, clinica, matricula, mascota, analisis, honorarios, precio,
               tipo_consulta, fechas, transportista, rechazo=None):
    """Inserta una consulta con su comprobante y una muestra con todo su circuito.

    `fechas` tiene las claves consulta, extraida, empaquetada, transito y, según el final,
    recibida+analizada (camino feliz) o rechazada. `rechazo`, si viene, es la lista de motivos.
    """
    vet = _uno(cx, "SELECT id FROM veterinarios WHERE matricula = ?", (matricula,))
    mascota_id = _uno(cx, "SELECT id FROM mascotas WHERE nombre = ?", (mascota,))
    tipo = _uno(cx, "SELECT id FROM tipos_analisis WHERE nombre = ?", (analisis,))
    clinica_id = _uno(cx, "SELECT clinica_id FROM veterinarios WHERE id = ?", (vet,))
    laboratorio = _uno(cx, "SELECT id FROM laboratorios LIMIT 1")

    consulta = _uno(cx, "INSERT INTO consultas (tipo, fecha_hora, mascota_id, veterinario_id, diagnostico) "
                        "VALUES (?, ?, ?, ?, 'Control de rutina') RETURNING id",
                    (tipo_consulta, fechas["consulta"], mascota_id, vet))
    orden = _uno(cx, "INSERT INTO ordenes_derivacion (consulta_id, tipo_analisis_id, prioridad) "
                     "VALUES (?, ?, 'NORMAL') RETURNING id", (consulta, tipo))
    # Comprobante: un ítem por la consulta y uno por el análisis derivado.
    comprobante = _uno(cx, "INSERT INTO comprobantes (consulta_id, fecha_hora) VALUES (?, ?) RETURNING id",
                       (consulta, fechas["consulta"]))
    cx.execute("INSERT INTO items_comprobante (comprobante_id, descripcion, monto, es_laboratorio) VALUES (?, ?, ?, 0)",
               (comprobante, tipo_consulta.capitalize(), honorarios))
    cx.execute("INSERT INTO items_comprobante (comprobante_id, descripcion, monto, es_laboratorio) VALUES (?, ?, ?, 1)",
               (comprobante, analisis, precio))

    estado_final = "RECHAZADA" if rechazo else "ANALIZADA"
    muestra = _uno(cx, "INSERT INTO muestras (orden_id, estado) VALUES (?, ?) RETURNING id", (orden, estado_final))

    pasos = [("EXTRAIDA", fechas["extraida"], None, "EXTRAIDA"),
             ("EMPAQUETADA", fechas["empaquetada"], "EXTRAIDA", "EMPAQUETADA"),
             ("EN_TRANSITO", fechas["transito"], "EMPAQUETADA", "EN_TRANSITO")]
    if rechazo:
        pasos.append(("RECHAZADA", fechas["rechazada"], "EN_TRANSITO", "RECHAZADA"))
    else:
        pasos.append(("RECIBIDA", fechas["recibida"], "EN_TRANSITO", "RECIBIDA"))
        pasos.append(("ANALIZADA", fechas["analizada"], "RECIBIDA", "ANALIZADA"))

    for _, cuando, anterior, nuevo in pasos:
        cambio = _uno(cx, "INSERT INTO cambios_estado (muestra_id, anterior, nuevo, fecha_hora, responsable, ubicacion) "
                          "VALUES (?, ?, ?, ?, 'Operador demo', ?) RETURNING id",
                      (muestra, anterior, nuevo, cuando, clinica))
        if nuevo == "RECHAZADA":
            for motivo in rechazo:
                cx.execute("INSERT INTO cambio_estado_motivos (cambio_id, motivo) VALUES (?, ?)", (cambio, motivo))

    # Conservadora precintada + remito con un tramo (el transportista) + recepción.
    temp_min, temp_max = (2, 8) if analisis != "Biopsia" else (15, 25)
    conservadora = _uno(cx, "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max, "
                            "precinto_numero, precinto_fecha, precinto_responsable) "
                            "VALUES (?, 5, ?, ?, ?, ?, 'Operador demo') RETURNING id",
                        (f"C-{n:03d}", temp_min, temp_max, f"P-{n:03d}", fechas["empaquetada"]))
    cx.execute("INSERT INTO conservadora_muestras (conservadora_id, muestra_id) VALUES (?, ?)",
               (conservadora, muestra))
    remito = _uno(cx, "INSERT INTO remitos (numero, clinica_id, laboratorio_id, estado) VALUES (?, ?, ?, ?) RETURNING id",
                  (f"R-{n:05d}", clinica_id, laboratorio, "RECHAZADO" if rechazo else "RECIBIDO"))
    cx.execute("INSERT INTO remito_conservadoras (remito_id, conservadora_id) VALUES (?, ?)", (remito, conservadora))
    cx.execute("INSERT INTO tramos_envio (remito_id, orden, origen, destino, transportista, salida, llegada) "
               "VALUES (?, 1, ?, 'Laboratorio Central VetSys', ?, ?, ?)",
               (remito, clinica, transportista, fechas["transito"],
                fechas.get("rechazada") or fechas.get("recibida")))
    recepcion = _uno(cx, "INSERT INTO recepciones (remito_id, laboratorio_id, responsable, fecha_hora) "
                         "VALUES (?, ?, 'Bioq. demo', ?) RETURNING id",
                     (remito, laboratorio, fechas.get("rechazada") or fechas.get("recibida")))
    precinto = "ROTO" if (rechazo and "PRECINTO_ROTO" in rechazo) else "INTACTO"
    temp_llegada = 30 if (rechazo and "TEMPERATURA_FUERA_DE_RANGO" in rechazo) else (temp_min + temp_max) / 2
    cx.execute("INSERT INTO detalles_recepcion (recepcion_id, conservadora_id, estado_precinto, "
               "temperatura_llegada, aceptada) VALUES (?, ?, ?, ?, ?)",
               (recepcion, conservadora, precinto, temp_llegada, 0 if rechazo else 1))

    if not rechazo:
        resultado = _uno(cx, "INSERT INTO resultados_analisis (muestra_id, responsable, fecha_hora, observaciones) "
                             "VALUES (?, 'Bioq. demo', ?, 'Dentro de parámetros') RETURNING id",
                         (muestra, fechas["analizada"]))
        cx.execute("INSERT INTO valores_resultado (resultado_id, parametro, valor, unidad, ref_min, ref_max) "
                   "VALUES (?, 'Glóbulos blancos', 8.5, 'mil/uL', 6, 17)", (resultado,))


# Cada tupla es una operación. Las fechas arman tránsitos y procesamientos variados y dos rechazos.
_OPERACIONES = [
    dict(clinica="Clínica Centro", matricula="MP-1001", mascota="Toby", analisis="Hemograma",
         tipo_consulta="CONSULTA", honorarios="3000.00", precio="12500.00", transportista="LogiFrío",
         fechas=dict(consulta="2026-08-05T09:00:00", extraida="2026-08-05T09:30:00", empaquetada="2026-08-05T10:00:00",
                     transito="2026-08-05T12:00:00", recibida="2026-08-06T10:00:00", analizada="2026-08-06T16:00:00")),
    dict(clinica="Clínica Centro", matricula="MP-1002", mascota="Mimi", analisis="Perfil bioquimico",
         tipo_consulta="CONTROL", honorarios="2500.00", precio="18900.00", transportista="TransVet",
         fechas=dict(consulta="2026-08-20T11:00:00", extraida="2026-08-20T11:30:00", empaquetada="2026-08-20T12:00:00",
                     transito="2026-08-20T14:00:00", recibida="2026-08-22T09:00:00", analizada="2026-08-22T15:00:00")),
    dict(clinica="Clínica Norte", matricula="MP-2001", mascota="Rex", analisis="Hemograma",
         tipo_consulta="URGENCIA", honorarios="8000.00", precio="12500.00", transportista="CadenaFría SA",
         rechazo=["PRECINTO_ROTO"],
         fechas=dict(consulta="2026-08-28T16:00:00", extraida="2026-08-28T16:30:00", empaquetada="2026-08-28T17:00:00",
                     transito="2026-08-28T18:00:00", rechazada="2026-08-29T10:00:00")),
    dict(clinica="Clínica Centro", matricula="MP-1001", mascota="Toby", analisis="Hemograma",
         tipo_consulta="CONSULTA", honorarios="3500.00", precio="12500.00", transportista="LogiFrío",
         fechas=dict(consulta="2026-09-03T09:00:00", extraida="2026-09-03T09:30:00", empaquetada="2026-09-03T10:00:00",
                     transito="2026-09-03T12:00:00", recibida="2026-09-04T18:00:00", analizada="2026-09-05T09:00:00")),
    dict(clinica="Clínica Norte", matricula="MP-2001", mascota="Nala", analisis="Biopsia",
         tipo_consulta="CONSULTA", honorarios="5000.00", precio="35000.00", transportista="TransVet",
         fechas=dict(consulta="2026-09-10T10:00:00", extraida="2026-09-10T10:30:00", empaquetada="2026-09-10T11:00:00",
                     transito="2026-09-10T13:00:00", recibida="2026-09-13T20:00:00", analizada="2026-09-14T11:00:00")),
    dict(clinica="Clínica Norte", matricula="MP-2002", mascota="Michi", analisis="Urocultivo",
         tipo_consulta="CONTROL", honorarios="2500.00", precio="9800.50", transportista="CadenaFría SA",
         rechazo=["TEMPERATURA_FUERA_DE_RANGO"],
         fechas=dict(consulta="2026-09-22T15:00:00", extraida="2026-09-22T15:30:00", empaquetada="2026-09-22T16:00:00",
                     transito="2026-09-22T17:00:00", rechazada="2026-09-23T12:00:00")),
    dict(clinica="Clínica Centro", matricula="MP-1001", mascota="Toby", analisis="Perfil bioquimico",
         tipo_consulta="CONSULTA", honorarios="4000.00", precio="18900.00", transportista="LogiFrío",
         fechas=dict(consulta="2026-10-02T09:00:00", extraida="2026-10-02T09:30:00", empaquetada="2026-10-02T10:00:00",
                     transito="2026-10-02T12:00:00", recibida="2026-10-03T08:00:00", analizada="2026-10-03T14:00:00")),
    dict(clinica="Clínica Centro", matricula="MP-1002", mascota="Simba", analisis="Hemograma",
         tipo_consulta="CONTROL", honorarios="3000.00", precio="12500.00", transportista="TransVet",
         fechas=dict(consulta="2026-10-15T11:00:00", extraida="2026-10-15T11:30:00", empaquetada="2026-10-15T12:00:00",
                     transito="2026-10-15T14:00:00", recibida="2026-10-16T12:00:00", analizada="2026-10-16T18:00:00")),
]


def cargar() -> bool:
    """Inserta las operaciones de demostración. Devuelve False si ya había muestras cargadas."""
    conexion = obtener_conexion()
    try:
        if conexion.execute("SELECT COUNT(*) FROM muestras").fetchone()[0]:
            return False
        try:
            conexion.execute("BEGIN")
            for n, op in enumerate(_OPERACIONES, start=1):
                _operacion(conexion, n, **op)
            conexion.commit()
        except Exception:
            if conexion.in_transaction:
                conexion.rollback()
            raise
        return True
    finally:
        conexion.close()


def main() -> None:
    if cargar():
        print(f"Operaciones de demostración cargadas ({len(_OPERACIONES)} muestras con su circuito).")
    else:
        print("Ya hay muestras cargadas: no se cargan operaciones de demostración otra vez.")


if __name__ == "__main__":
    main()

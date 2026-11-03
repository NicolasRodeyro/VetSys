"""Datos de prueba para los reportes que dependen del historial de las muestras.

Los servicios sellan cada cambio con la hora real, y estos reportes miran diferencias entre fechas:
para tener tiempos exactos, el historial se inserta con SQL y fechas fijas (INSERT sí está permitido;
lo que el trigger prohíbe es modificar o borrar). Solo se carga lo que los reportes leen.

La consulta y la orden de derivación sí se crean con los servicios: cada muestra necesita su propia
orden, porque una orden admite una sola muestra activa.
"""

from __future__ import annotations

from datetime import datetime

from app.persistencia.conexion import transaccion
from app.servicios import consultas
from tests.servicios.conftest import mascota, veterinario


def iso(cuando: str) -> str:
    """'2026-09-10 08:00' -> '2026-09-10T08:00:00', como se guardan las fechas."""
    return datetime.strptime(cuando, "%Y-%m-%d %H:%M").isoformat()


def nueva_orden(analisis: str = "Hemograma", dni: str = "30111222", nombre: str = "Toby", matricula: str = "MP-1001") -> int:
    consulta = consultas.registrar_consulta(mascota(dni, nombre).id, veterinario(matricula).id, "CONSULTA")
    return consultas.emitir_orden(consulta.id, analisis).id


def muestra(orden_id: int, *cambios: tuple) -> int:
    """Inserta una muestra con su historial. Cada cambio es (estado, 'AAAA-MM-DD HH:MM'[, motivos]).
    El estado de la muestra es el del último cambio. Una RECHAZADA necesita al menos un motivo (como en el dominio:
    si no, al cargar al cliente la muestra no se puede reconstruir)."""
    ultimo = cambios[-1]
    if ultimo[0] == "RECHAZADA" and not (len(ultimo) > 2 and ultimo[2]):
        raise ValueError("Una muestra RECHAZADA necesita al menos un motivo en su último cambio")
    with transaccion() as cx:
        muestra_id = cx.execute("INSERT INTO muestras (orden_id, estado) VALUES (?, ?)", (orden_id, cambios[-1][0])).lastrowid
        anterior = None
        for cambio in cambios:
            nuevo, cuando, motivos = (*cambio, ())[:3]
            cambio_id = cx.execute(
                "INSERT INTO cambios_estado (muestra_id, anterior, nuevo, fecha_hora, responsable) VALUES (?, ?, ?, ?, 'Prueba')",
                (muestra_id, anterior, nuevo, iso(cuando))).lastrowid
            for motivo in motivos:
                cx.execute("INSERT INTO cambio_estado_motivos (cambio_id, motivo) VALUES (?, ?)", (cambio_id, motivo))
            anterior = nuevo
    return muestra_id


def remito(numero: str, clinica: str, muestra_id: int, transportistas: tuple[str, ...] = (), estado: str = "EN_TRANSITO",
           recepcion: tuple | None = None) -> int:
    """Un remito de `clinica` que lleva una conservadora con la muestra. `transportistas` genera un tramo
    por cada uno (vacío = sin tramos). `recepcion` es (fecha, estado_del_precinto, temperatura_de_llegada, aceptada)."""
    with transaccion() as cx:
        clinica_id = cx.execute("SELECT id FROM clinicas WHERE nombre = ?", (clinica,)).fetchone()["id"]
        laboratorio_id = cx.execute("SELECT id FROM laboratorios").fetchone()["id"]
        conservadora_id = cx.execute(
            "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) VALUES (?, 5, 4, 6)", (f"C-{numero}",)).lastrowid
        cx.execute("INSERT INTO conservadora_muestras (conservadora_id, muestra_id) VALUES (?, ?)", (conservadora_id, muestra_id))
        remito_id = cx.execute(
            "INSERT INTO remitos (numero, clinica_id, laboratorio_id, estado) VALUES (?, ?, ?, ?)",
            (numero, clinica_id, laboratorio_id, estado)).lastrowid
        cx.execute("INSERT INTO remito_conservadoras (remito_id, conservadora_id) VALUES (?, ?)", (remito_id, conservadora_id))
        for orden, transportista in enumerate(transportistas, start=1):
            cx.execute(
                "INSERT INTO tramos_envio (remito_id, orden, origen, destino, transportista, salida) VALUES (?, ?, 'A', 'B', ?, ?)",
                (remito_id, orden, transportista, iso("2026-01-01 00:00")))
        if recepcion:
            cuando, precinto, temperatura, aceptada = recepcion
            recepcion_id = cx.execute(
                "INSERT INTO recepciones (remito_id, laboratorio_id, responsable, fecha_hora) VALUES (?, ?, 'Prueba', ?)",
                (remito_id, laboratorio_id, iso(cuando))).lastrowid
            cx.execute(
                "INSERT INTO detalles_recepcion (recepcion_id, conservadora_id, estado_precinto, temperatura_llegada, aceptada) "
                "VALUES (?, ?, ?, ?, ?)", (recepcion_id, conservadora_id, precinto, temperatura, int(aceptada)))
    return remito_id

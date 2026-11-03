"""Ayuda para los tests de reportes que leen de la base.

Los tiempos de la trazabilidad (`cambios_estado.fecha_hora`) los pone el reloj de la muestra
al cambiar de estado, y no se pueden fijar desde los servicios. Para poder probar con fechas
elegidas (tránsito de X horas, un despacho en tal mes), estos tests insertan las muestras y sus
cambios directamente por SQL sobre la base ya sembrada. Solo se usan INSERT, así que el trigger
de trazabilidad inmutable no se viola.
"""

from __future__ import annotations

import pytest

VETERINARIO = {"Clínica Centro": "MP-1001", "Clínica Norte": "MP-2001"}


class InsertorCircuito:
    """Inserta muestras con su cadena de estados en una base ya migrada y sembrada."""

    def __init__(self, cx):
        self.cx = cx
        self._n = 0

    def _id(self, sql, params=()):
        return self.cx.execute(sql, params).fetchone()[0]

    def insertar_muestra(self, *, clinica, analisis, cambios, transportista=None, motivos=()):
        """Crea consulta -> orden -> muestra y le carga `cambios` (lista de (estado, 'YYYY-MM-DD HH:MM')).

        Si se pasa `transportista`, arma conservadora + remito + tramo para que la muestra quede
        asociada a ese transportista. `motivos` se atan al cambio a RECHAZADA.
        """
        self._n += 1
        n = self._n
        vet = self._id("SELECT id FROM veterinarios WHERE matricula = ?", (VETERINARIO[clinica],))
        mascota = self._id("SELECT id FROM mascotas LIMIT 1")
        tipo = self._id("SELECT id FROM tipos_analisis WHERE nombre = ?", (analisis,))
        estado_final = cambios[-1][0]

        consulta = self._id(
            "INSERT INTO consultas (tipo, fecha_hora, mascota_id, veterinario_id) "
            "VALUES ('CONSULTA', '2026-01-01T09:00:00', ?, ?) RETURNING id", (mascota, vet))
        orden = self._id(
            "INSERT INTO ordenes_derivacion (consulta_id, tipo_analisis_id, prioridad) "
            "VALUES (?, ?, 'NORMAL') RETURNING id", (consulta, tipo))
        muestra = self._id(
            "INSERT INTO muestras (orden_id, estado) VALUES (?, ?) RETURNING id", (orden, estado_final))

        for estado, cuando in cambios:
            cambio = self._id(
                "INSERT INTO cambios_estado (muestra_id, anterior, nuevo, fecha_hora, responsable) "
                "VALUES (?, NULL, ?, ?, 'test') RETURNING id",
                (muestra, estado, cuando.replace(" ", "T")))
            if estado == "RECHAZADA":
                for motivo in motivos:
                    self.cx.execute(
                        "INSERT INTO cambio_estado_motivos (cambio_id, motivo) VALUES (?, ?)",
                        (cambio, motivo))

        if transportista is not None:
            conservadora = self._id(
                "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max) "
                "VALUES (?, 5, 2, 8) RETURNING id", (f"C-{n}",))
            self.cx.execute(
                "INSERT INTO conservadora_muestras (conservadora_id, muestra_id) VALUES (?, ?)",
                (conservadora, muestra))
            remito = self._id(
                "INSERT INTO remitos (numero, clinica_id, laboratorio_id, estado) "
                "VALUES (?, (SELECT clinica_id FROM veterinarios WHERE id = ?), "
                "(SELECT id FROM laboratorios LIMIT 1), 'EN_TRANSITO') RETURNING id",
                (f"R-{n:05d}", vet))
            self.cx.execute(
                "INSERT INTO remito_conservadoras (remito_id, conservadora_id) VALUES (?, ?)",
                (remito, conservadora))
            self.cx.execute(
                "INSERT INTO tramos_envio (remito_id, orden, origen, destino, transportista, salida) "
                "VALUES (?, 1, 'Clínica', 'Laboratorio', ?, '2026-01-01T10:00:00')",
                (remito, transportista))
        self.cx.commit()
        return muestra


@pytest.fixture
def circuito(con_seed, cx) -> InsertorCircuito:
    return InsertorCircuito(cx)

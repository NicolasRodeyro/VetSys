"""Reporte: tasa de rechazo de muestras por clínica y por motivo.

Qué calcula (no está guardado): sobre las muestras despachadas en el período, qué proporción
terminó rechazada en la recepción del laboratorio, abierta por clínica de origen y por motivo
del rechazo (precinto roto o temperatura fuera de rango; una misma muestra puede tener los dos).

- Despachada: la muestra pasó a EN_TRANSITO (salió hacia el laboratorio).
- Rechazada: en la recepción pasó a RECHAZADA (CLAUDE.md §4.2: el rechazo solo ocurre ahí).
- Tasa de rechazo = rechazadas / despachadas.

El rango de fechas se aplica a la fecha de despacho; la clínica, a la de origen de la muestra.
Los motivos salen de `cambio_estado_motivos`, parte de la trazabilidad inmutable.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.dominio.enums import MotivoRechazo
from app.persistencia.conexion import transaccion
from app.reportes import formato
from app.reportes.filtros import FiltroReporte
from app.reportes.resultado import Grafico, ResultadoReporte

TITULO = "Tasa de rechazo de muestras"
DESCRIPCION = ("Sobre las muestras despachadas en el período (por fecha de despacho), qué porcentaje "
               "terminó rechazada, abierto por clínica y por motivo. Una muestra puede tener más de un motivo.")

_SQL_DESPACHADAS = """
SELECT m.id          AS muestra_id,
       cl.nombre     AS clinica,
       ce.fecha_hora AS despacho
FROM muestras m
JOIN ordenes_derivacion o ON o.id = m.orden_id
JOIN consultas c          ON c.id = o.consulta_id
JOIN veterinarios v       ON v.id = c.veterinario_id
JOIN clinicas cl          ON cl.id = v.clinica_id
JOIN cambios_estado ce    ON ce.muestra_id = m.id AND ce.nuevo = 'EN_TRANSITO'
WHERE (? IS NULL OR cl.id = ?)
"""

_SQL_MOTIVOS = """
SELECT ce.muestra_id AS muestra_id,
       cem.motivo    AS motivo
FROM cambios_estado ce
JOIN cambio_estado_motivos cem ON cem.cambio_id = ce.id
WHERE ce.nuevo = 'RECHAZADA'
"""


@dataclass(frozen=True)
class RechazoMuestra:
    muestra_id: int
    clinica: str
    rechazada: bool
    precinto_roto: bool
    temperatura_fuera: bool


@dataclass(frozen=True)
class RenglonRechazo:
    clinica: str
    despachadas: int
    rechazadas: int
    precinto_roto: int
    temperatura_fuera: int

    @property
    def tasa(self) -> Decimal | None:
        """Porcentaje de rechazo. None si no hubo despachos (no hay sobre qué calcularla)."""
        if self.despachadas == 0:
            return None
        return Decimal(self.rechazadas) / Decimal(self.despachadas) * 100


# ---------------------------------------------------------------- lectura (SQL)

def _leer(conexion: sqlite3.Connection, filtro: FiltroReporte) -> list[RechazoMuestra]:
    motivos: dict[int, set[str]] = {}
    for f in conexion.execute(_SQL_MOTIVOS):
        motivos.setdefault(f["muestra_id"], set()).add(f["motivo"])

    muestras: list[RechazoMuestra] = []
    for f in conexion.execute(_SQL_DESPACHADAS, (filtro.clinica_id, filtro.clinica_id)):
        if not (filtro.desde <= datetime.fromisoformat(f["despacho"]).date() <= filtro.hasta):
            continue
        suyos = motivos.get(f["muestra_id"], set())
        muestras.append(RechazoMuestra(
            f["muestra_id"], f["clinica"], bool(suyos),
            MotivoRechazo.PRECINTO_ROTO.value in suyos,
            MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO.value in suyos))
    return muestras


# ---------------------------------------------------------------- cálculo (Python puro)

def _resumir(clinica: str, muestras: list[RechazoMuestra]) -> RenglonRechazo:
    return RenglonRechazo(
        clinica,
        len(muestras),
        sum(1 for m in muestras if m.rechazada),
        sum(1 for m in muestras if m.precinto_roto),
        sum(1 for m in muestras if m.temperatura_fuera))


def calcular(muestras: list[RechazoMuestra]) -> tuple[list[RenglonRechazo], RenglonRechazo]:
    clinicas = sorted({m.clinica for m in muestras})
    renglones = [_resumir(clinica, [m for m in muestras if m.clinica == clinica]) for clinica in clinicas]
    total = _resumir("TOTAL", muestras)
    return renglones, total


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Clínica", "Despachadas", "Rechazadas", "Tasa de rechazo", "Precinto roto", "Temp. fuera de rango"]


def _fila(r: RenglonRechazo) -> list[str]:
    return [r.clinica, str(r.despachadas), str(r.rechazadas), formato.tasa(r.tasa),
            str(r.precinto_roto), str(r.temperatura_fuera)]


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    with transaccion() as conexion:
        muestras = _leer(conexion, filtro)
    renglones, total = calcular(muestras)

    filas = [_fila(r) for r in renglones]
    if muestras:
        filas.append(_fila(total))

    rechazadas = total.rechazadas
    notas = [f"{total.despachadas} muestra(s) despachada(s), {rechazadas} rechazada(s) "
             f"({formato.tasa(total.tasa)})."]
    if not muestras:
        notas = ["No hay muestras despachadas en el período elegido."]

    grafico = None
    if renglones:
        grafico = Grafico(
            "Tasa de rechazo por clínica (%)",
            [r.clinica for r in renglones],
            {"Tasa de rechazo": [float(r.tasa or 0) for r in renglones]},
            "Porcentaje")
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico)

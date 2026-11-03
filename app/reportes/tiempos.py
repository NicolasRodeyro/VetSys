"""Reporte: tiempos de tránsito y procesamiento de las muestras.

Qué calcula (no está guardado en ninguna tabla): a partir del historial de cada muestra
(su trazabilidad), cuánto tardó en viajar y cuánto en procesarse, y lo resume por clínica
de origen y por transportista.

- Tránsito: horas entre el despacho (paso a EN_TRANSITO) y la llegada al laboratorio
  (paso a RECIBIDA o RECHAZADA). Es el tiempo que la muestra estuvo en viaje.
- Procesamiento: horas entre la recepción (RECIBIDA) y el resultado (ANALIZADA).
- Fuera de tiempo: muestras cuyo tránsito superó las `horas_max_transito` que pide su análisis.
  (El exceso de tiempo NO rechaza la muestra —decisión de diseño, CLAUDE.md §4.5—, pero acá se
  mide para saber qué tan seguido pasa.)

La mediana y el P90 se calculan en Python porque SQLite no tiene PERCENTILE_CONT (ver
`estadistica.py`). El rango de fechas del filtro se aplica a la fecha de despacho; la clínica,
a la de origen de la muestra. A cada muestra se le atribuye el transportista del último tramo
de su remito (el que la entregó al laboratorio).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from app.persistencia.conexion import transaccion
from app.reportes import estadistica, formato
from app.reportes.filtros import FiltroReporte
from app.reportes.resultado import Grafico, ResultadoReporte

TITULO = "Tiempos de tránsito y procesamiento"
DESCRIPCION = ("Mediana y P90 (en horas) calculados desde el historial de cada muestra. "
               "El rango de fechas se aplica a la fecha de despacho. «Fuera de tiempo» cuenta las "
               "muestras cuyo tránsito superó el máximo que pide su análisis.")

# Un cambio de estado relevante para medir tiempos: el nombre del estado nuevo y cuándo pasó.
_SQL_CAMBIOS = """
SELECT m.id                 AS muestra_id,
       cl.nombre            AS clinica,
       ta.horas_max_transito AS horas_max,
       ce.nuevo             AS estado,
       ce.fecha_hora        AS fecha_hora
FROM muestras m
JOIN ordenes_derivacion o ON o.id = m.orden_id
JOIN consultas c          ON c.id = o.consulta_id
JOIN veterinarios v       ON v.id = c.veterinario_id
JOIN clinicas cl          ON cl.id = v.clinica_id
JOIN tipos_analisis ta    ON ta.id = o.tipo_analisis_id
JOIN cambios_estado ce    ON ce.muestra_id = m.id
WHERE (? IS NULL OR cl.id = ?)
ORDER BY m.id, ce.id
"""

# Transportista del último tramo (el que entregó la muestra en el laboratorio).
_SQL_TRANSPORTISTA = """
SELECT cm.muestra_id   AS muestra_id,
       te.transportista AS transportista
FROM conservadora_muestras cm
JOIN remito_conservadoras rc ON rc.conservadora_id = cm.conservadora_id
JOIN tramos_envio te         ON te.remito_id = rc.remito_id
WHERE te.orden = (SELECT MAX(orden) FROM tramos_envio WHERE remito_id = rc.remito_id)
"""


@dataclass(frozen=True)
class TiempoMuestra:
    """Lo medido de una muestra: sus tiempos ya calculados en horas (None si no llegó a ese paso)."""

    muestra_id: int
    clinica: str
    transportista: str | None
    horas_max: int
    transito: float | None
    proceso: float | None

    @property
    def fuera_de_tiempo(self) -> bool:
        return self.transito is not None and self.transito > self.horas_max


@dataclass(frozen=True)
class RenglonTiempos:
    ambito: str          # "Clínica" o "Transportista"
    nombre: str
    muestras: int        # cuántas completaron el tránsito (las que se pudieron medir)
    transito_mediana: float | None
    transito_p90: float | None
    proceso_mediana: float | None
    proceso_p90: float | None
    fuera_de_tiempo: int


@dataclass(frozen=True)
class ResumenTiempos:
    por_clinica: list[RenglonTiempos]
    por_transportista: list[RenglonTiempos]
    total: RenglonTiempos


# ---------------------------------------------------------------- lectura (SQL)

def _horas(desde: datetime, hasta: datetime) -> float:
    return (hasta - desde).total_seconds() / 3600


def _leer(conexion: sqlite3.Connection, filtro: FiltroReporte) -> list[TiempoMuestra]:
    transportistas = {f["muestra_id"]: f["transportista"]
                      for f in conexion.execute(_SQL_TRANSPORTISTA)}

    # Se juntan los cambios de cada muestra para reconstruir sus tiempos.
    cambios: dict[int, dict] = {}
    for f in conexion.execute(_SQL_CAMBIOS, (filtro.clinica_id, filtro.clinica_id)):
        datos = cambios.setdefault(f["muestra_id"],
                                   {"clinica": f["clinica"], "horas_max": f["horas_max"], "pasos": {}})
        # Si un estado se repitiera, vale el primero (no debería pasar en un flujo normal).
        datos["pasos"].setdefault(f["estado"], datetime.fromisoformat(f["fecha_hora"]))

    medidas: list[TiempoMuestra] = []
    for muestra_id, datos in cambios.items():
        pasos = datos["pasos"]
        despacho = pasos.get("EN_TRANSITO")
        if despacho is None or not (filtro.desde <= despacho.date() <= filtro.hasta):
            continue  # solo las despachadas dentro del rango de fechas

        llegada = pasos.get("RECIBIDA") or pasos.get("RECHAZADA")
        transito = _horas(despacho, llegada) if llegada is not None else None
        recibida, analizada = pasos.get("RECIBIDA"), pasos.get("ANALIZADA")
        proceso = _horas(recibida, analizada) if recibida and analizada else None

        medidas.append(TiempoMuestra(muestra_id, datos["clinica"], transportistas.get(muestra_id),
                                     datos["horas_max"], transito, proceso))
    return medidas


# ---------------------------------------------------------------- cálculo (Python puro)

def _resumir(ambito: str, nombre: str, muestras: list[TiempoMuestra]) -> RenglonTiempos:
    transitos = [m.transito for m in muestras if m.transito is not None]
    procesos = [m.proceso for m in muestras if m.proceso is not None]
    return RenglonTiempos(
        ambito, nombre, len(transitos),
        estadistica.mediana(transitos), estadistica.percentil(transitos, 90),
        estadistica.mediana(procesos), estadistica.percentil(procesos, 90),
        sum(1 for m in muestras if m.fuera_de_tiempo))


def _agrupar(muestras: list[TiempoMuestra], ambito: str, clave) -> list[RenglonTiempos]:
    nombres = sorted({clave(m) for m in muestras if clave(m) is not None})
    return [_resumir(ambito, nombre, [m for m in muestras if clave(m) == nombre]) for nombre in nombres]


def calcular(muestras: list[TiempoMuestra]) -> ResumenTiempos:
    return ResumenTiempos(
        _agrupar(muestras, "Clínica", lambda m: m.clinica),
        _agrupar(muestras, "Transportista", lambda m: m.transportista),
        _resumir("", "TOTAL", muestras))


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Ámbito", "Nombre", "Muestras", "Tránsito mediana", "Tránsito P90",
            "Proceso mediana", "Proceso P90", "Fuera de tiempo"]


def _fila(r: RenglonTiempos, proceso: bool = True) -> list[str]:
    return [r.ambito, r.nombre, str(r.muestras),
            formato.horas(r.transito_mediana), formato.horas(r.transito_p90),
            formato.horas(r.proceso_mediana) if proceso else formato.SIN_DATO,
            formato.horas(r.proceso_p90) if proceso else formato.SIN_DATO,
            str(r.fuera_de_tiempo)]


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    with transaccion() as conexion:
        muestras = _leer(conexion, filtro)
    resumen = calcular(muestras)

    filas = [_fila(r) for r in resumen.por_clinica]
    # El procesamiento ocurre en el laboratorio: no corresponde a un transportista.
    filas += [_fila(r, proceso=False) for r in resumen.por_transportista]
    if muestras:
        filas.append(_fila(resumen.total))

    medidas = resumen.total.muestras
    notas = [f"{len(muestras)} muestra(s) despachada(s) en el período; {medidas} completaron el tránsito."]
    if not muestras:
        notas = ["No hay muestras despachadas en el período elegido."]

    grafico = None
    if resumen.por_clinica:
        etiquetas = [r.nombre for r in resumen.por_clinica]
        grafico = Grafico(
            "Tránsito por clínica (horas)",
            etiquetas,
            {"Mediana": [r.transito_mediana or 0.0 for r in resumen.por_clinica],
             "P90": [r.transito_p90 or 0.0 for r in resumen.por_clinica]},
            "Horas")
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico)

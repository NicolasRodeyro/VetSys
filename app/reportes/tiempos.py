"""Reporte: tiempos de tránsito y de procesamiento de las muestras.

Qué calcula (no está guardado en ninguna tabla; sale del historial de estados de cada muestra):
- Tránsito: desde que se despacha (En tránsito) hasta que el laboratorio la recibe o la rechaza.
- Procesamiento: desde que se recibe hasta que se analiza (solo las que se aceptaron).
- Por clínica de origen y por transportista: cantidad, mediana y P90 de cada tiempo.
- Cuántas muestras superaron `horas_max_transito` de su tipo de análisis («fuera de plazo»).

El rango de fechas se aplica a la fecha de despacho. La clínica es la de origen del remito.
SQLite no tiene PERCENTILE_CONT: se traen las fechas y la mediana y el P90 se calculan en Python
(`estadistica.percentil`, interpolación lineal).

Ojo con el plazo: superarlo NO rechaza la muestra (decisión de diseño, ver CLAUDE.md); acá solo se informa.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.persistencia.conexion import transaccion
from app.reportes import formato
from app.reportes.estadistica import mediana, percentil
from app.reportes.filtros import FiltroReporte
from app.reportes.resultado import Grafico, ResultadoReporte
from app.reportes.transporte import de_un_remito, transportistas_por_remito

TITULO = "Tiempos de tránsito y procesamiento"
DESCRIPCION = ("Muestras despachadas en el rango (por fecha de despacho). Mediana y P90 en horas, por clínica de origen "
               "y por transportista. «Fuera de plazo»: el tránsito superó el máximo de su tipo de análisis.")

_SQL = """
SELECT m.id             AS muestra_id,
       cl.nombre        AS clinica,
       r.id             AS remito_id,
       ta.horas_max_transito AS horas_max,
       h.despacho, h.llegada, h.recibida, h.analizada
FROM (
    SELECT muestra_id,
           MIN(CASE WHEN nuevo = 'EN_TRANSITO' THEN fecha_hora END)               AS despacho,
           MIN(CASE WHEN nuevo IN ('RECIBIDA', 'RECHAZADA') THEN fecha_hora END)  AS llegada,
           MIN(CASE WHEN nuevo = 'RECIBIDA' THEN fecha_hora END)                  AS recibida,
           MIN(CASE WHEN nuevo = 'ANALIZADA' THEN fecha_hora END)                 AS analizada
    FROM cambios_estado
    GROUP BY muestra_id
) h
JOIN muestras m                 ON m.id = h.muestra_id
JOIN ordenes_derivacion o       ON o.id = m.orden_id
JOIN tipos_analisis ta          ON ta.id = o.tipo_analisis_id
JOIN conservadora_muestras cm   ON cm.muestra_id = m.id
JOIN remito_conservadoras rc    ON rc.conservadora_id = cm.conservadora_id
JOIN remitos r                  ON r.id = rc.remito_id
JOIN clinicas cl                ON cl.id = r.clinica_id
WHERE h.despacho >= ? AND h.despacho < ?
  AND (? IS NULL OR cl.id = ?)
ORDER BY h.despacho, m.id
"""


def _horas_entre(inicio: datetime | None, fin: datetime | None) -> float | None:
    return None if inicio is None or fin is None else (fin - inicio).total_seconds() / 3600


@dataclass(frozen=True)
class Envio:
    """El recorrido de una muestra, tal como sale del historial."""

    muestra_id: int
    clinica: str
    remito_id: int
    horas_max: int
    despacho: datetime
    llegada: datetime | None  # cuando el laboratorio la recibió o la rechazó
    recibida: datetime | None  # solo si la aceptó
    analizada: datetime | None

    @property
    def transito(self) -> float | None:
        """Horas en tránsito; None si todavía no llegó."""
        return _horas_entre(self.despacho, self.llegada)

    @property
    def procesamiento(self) -> float | None:
        """Horas entre la recepción y el análisis; None si no se aceptó o todavía no se analizó."""
        return _horas_entre(self.recibida, self.analizada)

    @property
    def fuera_de_plazo(self) -> bool:
        """El tránsito superó el máximo. Un tránsito justo igual al máximo está dentro del plazo."""
        return self.transito is not None and self.transito > self.horas_max


@dataclass(frozen=True)
class Resumen:
    muestras: int
    con_transito: int  # las que ya llegaron: sobre ellas se calculan las estadísticas de tránsito
    transito_mediana: float | None
    transito_p90: float | None
    fuera_de_plazo: int
    procesamiento_mediana: float | None
    procesamiento_p90: float | None
    en_transito: int  # todavía no llegaron


@dataclass(frozen=True)
class Grupo:
    agrupacion: str  # «Clínica», «Transportista» o «Total»
    nombre: str
    envios: list[Envio] = field(default_factory=list)


# ---------------------------------------------------------------- lectura (SQL)

def _leer(conexion: sqlite3.Connection, desde: date, hasta_exclusivo: date, clinica_id: int | None) -> list[Envio]:
    filas = conexion.execute(_SQL, (desde.isoformat(), hasta_exclusivo.isoformat(), clinica_id, clinica_id))

    def fecha(texto: str | None) -> datetime | None:
        return None if texto is None else datetime.fromisoformat(texto)

    return [Envio(f["muestra_id"], f["clinica"], f["remito_id"], f["horas_max"], datetime.fromisoformat(f["despacho"]),
                  fecha(f["llegada"]), fecha(f["recibida"]), fecha(f["analizada"])) for f in filas]


# ---------------------------------------------------------------- cálculo (Python puro)

def resumir(envios: list[Envio]) -> Resumen:
    transitos = [e.transito for e in envios if e.transito is not None]
    procesamientos = [e.procesamiento for e in envios if e.procesamiento is not None]
    return Resumen(
        len(envios), len(transitos), mediana(transitos), percentil(transitos, 0.9),
        sum(1 for e in envios if e.fuera_de_plazo),
        mediana(procesamientos), percentil(procesamientos, 0.9),
        len(envios) - len(transitos))


def agrupar(envios: list[Envio], transportistas: dict[int, list[str]]) -> list[Grupo]:
    """Por clínica, por transportista (una muestra cuenta una vez por cada uno que intervino) y el total."""
    por_clinica: dict[str, list[Envio]] = {}
    por_transportista: dict[str, list[Envio]] = {}
    for envio in envios:
        por_clinica.setdefault(envio.clinica, []).append(envio)
        for nombre in de_un_remito(transportistas, envio.remito_id):
            por_transportista.setdefault(nombre, []).append(envio)
    return ([Grupo("Clínica", nombre, por_clinica[nombre]) for nombre in sorted(por_clinica)]
            + [Grupo("Transportista", nombre, por_transportista[nombre]) for nombre in sorted(por_transportista)]
            + ([Grupo("Total", "Todas las muestras", envios)] if envios else []))


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Agrupación", "Grupo", "Muestras", "Tránsito (med. / P90)", "Fuera de plazo",
            "Procesam. (med. / P90)", "En tránsito"]


def _par(mediana: float | None, p90: float | None) -> str:
    """«24,0 h / 27,2 h»; «—» si no hay datos."""
    return formato.SIN_DATO if mediana is None else f"{formato.horas(mediana)} / {formato.horas(p90)}"


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    with transaccion() as conexion:
        envios = _leer(conexion, filtro.desde, filtro.hasta + timedelta(days=1), filtro.clinica_id)
        transportistas = transportistas_por_remito(conexion)
    grupos = agrupar(envios, transportistas)
    resumenes = [(g, resumir(g.envios)) for g in grupos]

    filas = [[g.agrupacion, g.nombre, str(r.muestras), _par(r.transito_mediana, r.transito_p90),
              f"{r.fuera_de_plazo} de {r.con_transito} ({formato.tasa(r.fuera_de_plazo, r.con_transito)})"
              if r.con_transito else formato.SIN_DATO,
              _par(r.procesamiento_mediana, r.procesamiento_p90), str(r.en_transito)]
             for g, r in resumenes]

    notas = [f"Despachos del {filtro.desde:%d/%m/%Y} al {filtro.hasta:%d/%m/%Y}: {len(envios)} muestra(s)."
             if envios else "No hay muestras despachadas en el período elegido.",
             "Una muestra cuenta una vez por cada transportista que intervino en su remito. "
             "P90 por interpolación lineal. Superar el plazo no rechaza la muestra: solo se informa."]
    con_dato = [(g, r) for g, r in resumenes if g.agrupacion != "Total" and r.transito_mediana is not None]
    grafico = Grafico(
        "Tiempo de tránsito (horas)", [g.nombre for g, _ in con_dato],
        {"Mediana": [r.transito_mediana for _, r in con_dato], "P90": [r.transito_p90 for _, r in con_dato]}, "Horas",
    ) if con_dato else None
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico)

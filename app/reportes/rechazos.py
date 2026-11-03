"""Reporte: tasa de rechazo de muestras en el laboratorio.

Qué calcula (no está guardado en ninguna tabla):
- Llegaron: muestras que el laboratorio recibió o rechazó en el rango (por fecha de la recepción).
- Tasa de rechazo = rechazadas / llegaron, por clínica de origen, por transportista y por motivo.
- El detalle de cada muestra rechazada: precinto, temperatura de llegada, remito y transportistas.

Reglas de lectura:
- Una muestra cuenta una vez por cada transportista que intervino en su remito.
- Una muestra rechazada por dos motivos cuenta en los dos: la suma por motivo puede superar a las
  rechazadas. En «Motivo», la tasa es sobre el total de las que llegaron.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.persistencia.conexion import transaccion
from app.reportes import formato
from app.reportes.filtros import FiltroReporte
from app.reportes.resultado import Grafico, ResultadoReporte
from app.reportes.transporte import de_un_remito, transportistas_por_remito

TITULO = "Tasa de rechazo de muestras"
DESCRIPCION = ("Muestras recibidas o rechazadas por el laboratorio en el rango (por fecha de recepción). Tasa de rechazo "
               "por clínica de origen, por transportista y por motivo, y el detalle de cada muestra rechazada.")

_SQL = """
SELECT ce.id AS cambio_id, ce.muestra_id, ce.nuevo AS resultado, ce.fecha_hora,
       cl.nombre AS clinica, r.id AS remito_id, r.numero AS remito,
       ta.nombre AS analisis, mas.nombre AS mascota,
       d.estado_precinto, d.temperatura_llegada
FROM cambios_estado ce
JOIN muestras m               ON m.id = ce.muestra_id
JOIN ordenes_derivacion o     ON o.id = m.orden_id
JOIN tipos_analisis ta        ON ta.id = o.tipo_analisis_id
JOIN consultas co             ON co.id = o.consulta_id
JOIN mascotas mas             ON mas.id = co.mascota_id
JOIN conservadora_muestras cm ON cm.muestra_id = m.id
JOIN remito_conservadoras rc  ON rc.conservadora_id = cm.conservadora_id
JOIN remitos r                ON r.id = rc.remito_id
JOIN clinicas cl              ON cl.id = r.clinica_id
LEFT JOIN recepciones rec     ON rec.remito_id = r.id
LEFT JOIN detalles_recepcion d ON d.recepcion_id = rec.id AND d.conservadora_id = cm.conservadora_id
WHERE ce.nuevo IN ('RECIBIDA', 'RECHAZADA')
  AND ce.fecha_hora >= ? AND ce.fecha_hora < ?
  AND (? IS NULL OR cl.id = ?)
ORDER BY ce.fecha_hora, ce.muestra_id
"""

_SQL_MOTIVOS = """
SELECT cem.cambio_id, cem.motivo
FROM cambio_estado_motivos cem
JOIN cambios_estado ce ON ce.id = cem.cambio_id
WHERE ce.fecha_hora >= ? AND ce.fecha_hora < ?
ORDER BY cem.rowid
"""


@dataclass(frozen=True)
class Llegada:
    """Una muestra en el momento en que el laboratorio la recibió o la rechazó."""

    muestra_id: int
    cuando: datetime
    rechazada: bool
    clinica: str
    remito_id: int
    remito: str
    analisis: str
    mascota: str
    precinto: str | None  # INTACTO / ROTO, tal como lo constató el laboratorio
    temperatura: float | None
    motivos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tasa:
    agrupacion: str  # «Clínica», «Transportista», «Motivo» o «Total»
    grupo: str
    llegaron: int
    rechazadas: int


# ---------------------------------------------------------------- lectura (SQL)

def _leer(conexion: sqlite3.Connection, desde: date, hasta_exclusivo: date, clinica_id: int | None) -> list[Llegada]:
    rango = (desde.isoformat(), hasta_exclusivo.isoformat())
    motivos: dict[int, list[str]] = {}
    for fila in conexion.execute(_SQL_MOTIVOS, rango):
        motivos.setdefault(fila["cambio_id"], []).append(fila["motivo"])
    filas = conexion.execute(_SQL, (*rango, clinica_id, clinica_id))
    return [Llegada(f["muestra_id"], datetime.fromisoformat(f["fecha_hora"]), f["resultado"] == "RECHAZADA", f["clinica"],
                    f["remito_id"], f["remito"], f["analisis"], f["mascota"], f["estado_precinto"], f["temperatura_llegada"],
                    tuple(motivos.get(f["cambio_id"], ()))) for f in filas]


# ---------------------------------------------------------------- cálculo (Python puro)

def calcular(llegadas: list[Llegada], transportistas: dict[int, list[str]]) -> list[Tasa]:
    """Las tasas por clínica, por transportista, por motivo y el total, en ese orden."""
    por_clinica: dict[str, list[Llegada]] = {}
    por_transportista: dict[str, list[Llegada]] = {}
    for llegada in llegadas:
        por_clinica.setdefault(llegada.clinica, []).append(llegada)
        for nombre in de_un_remito(transportistas, llegada.remito_id):
            por_transportista.setdefault(nombre, []).append(llegada)

    def tasa(agrupacion: str, grupo: str, lista: list[Llegada]) -> Tasa:
        return Tasa(agrupacion, grupo, len(lista), sum(1 for x in lista if x.rechazada))

    por_motivo: dict[str, int] = {}
    for llegada in llegadas:
        for codigo in llegada.motivos:
            por_motivo[codigo] = por_motivo.get(codigo, 0) + 1

    return ([tasa("Clínica", nombre, por_clinica[nombre]) for nombre in sorted(por_clinica)]
            + [tasa("Transportista", nombre, por_transportista[nombre]) for nombre in sorted(por_transportista)]
            + [Tasa("Motivo", formato.motivo(codigo), len(llegadas), cantidad)
               for codigo, cantidad in sorted(por_motivo.items(), key=lambda par: formato.motivo(par[0]))]
            + ([tasa("Total", "Todas las muestras", llegadas)] if llegadas else []))


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Agrupación", "Grupo", "Llegaron", "Rechazadas", "Tasa de rechazo"]
COLUMNAS_DETALLE = ["Fecha", "Muestra", "Análisis", "Mascota", "Clínica", "Remito", "Transportista(s)", "Motivo(s)",
                    "Precinto", "Temp. de llegada"]


def _detalle(llegadas: list[Llegada], transportistas: dict[int, list[str]]) -> list[list[str]]:
    return [[f"{x.cuando:%d/%m/%Y %H:%M}", f"#{x.muestra_id}", x.analisis, x.mascota, x.clinica, x.remito,
             ", ".join(de_un_remito(transportistas, x.remito_id)), ", ".join(formato.motivo(m) for m in x.motivos),
             formato.SIN_DATO if x.precinto is None else x.precinto.capitalize(),
             formato.SIN_DATO if x.temperatura is None else f"{x.temperatura:g} °C".replace(".", ",")]
            for x in llegadas if x.rechazada]


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    with transaccion() as conexion:
        llegadas = _leer(conexion, filtro.desde, filtro.hasta + timedelta(days=1), filtro.clinica_id)
        transportistas = transportistas_por_remito(conexion)
    tasas = calcular(llegadas, transportistas)

    filas = [[t.agrupacion, t.grupo, str(t.llegaron), str(t.rechazadas), formato.tasa(t.rechazadas, t.llegaron)] for t in tasas]
    detalle = _detalle(llegadas, transportistas)
    rechazadas = len(detalle)

    notas = [f"Del {filtro.desde:%d/%m/%Y} al {filtro.hasta:%d/%m/%Y}: llegaron {len(llegadas)} muestra(s) y se rechazaron {rechazadas}."
             if llegadas else "No llegaron muestras al laboratorio en el período elegido.",
             "Una muestra cuenta una vez por cada transportista de su remito. Una rechazada por dos motivos cuenta en ambos "
             "(en «Motivo» la tasa es sobre el total de las que llegaron)."]
    barras = [t for t in tasas if t.agrupacion in ("Clínica", "Transportista")]
    grafico = Grafico("Tasa de rechazo (%)", [t.grupo for t in barras],
                      {"Tasa de rechazo (%)": [t.rechazadas / t.llegaron * 100 for t in barras]}, "% de las que llegaron") if barras else None
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico,
                            "Muestras rechazadas" if detalle else "", COLUMNAS_DETALLE if detalle else [], detalle)

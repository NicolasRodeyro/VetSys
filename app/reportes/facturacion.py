"""Reporte: facturación por clínica y servicio, mes contra mes.

Qué calcula (no está guardado en ninguna tabla):
- Lo facturado por cada clínica y servicio en cada mes, y la variación % contra el mes anterior.
- El total de cada mes y su variación.

La clínica es la del veterinario que atendió la consulta del comprobante. El rango de fechas se
aplica a la fecha del comprobante y se toman **meses completos** (del 15/08 al 02/10 -> agosto,
septiembre y octubre). Para que el primer mes también tenga variación, se lee el mes anterior.

Los montos se guardan como TEXT (Decimal): no se usa SUM() de SQL, que los convertiría a float.
Se traen los ítems y se suman con Decimal en Python.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.dominio.fechas import sumar_meses
from app.persistencia.conexion import transaccion
from app.reportes import formato
from app.reportes.estadistica import variacion_porcentual
from app.reportes.filtros import FiltroReporte, meses_del_rango, primer_dia_del_mes
from app.reportes.resultado import Grafico, ResultadoReporte

TITULO = "Facturación por clínica y servicio"
DESCRIPCION = ("Meses completos según la fecha del comprobante. La variación compara cada mes con el anterior; "
               "«—» si el mes anterior no tuvo facturación.")

_SQL = """
SELECT strftime('%Y-%m', c.fecha_hora) AS mes,
       cl.nombre                      AS clinica,
       i.descripcion                  AS servicio,
       i.es_laboratorio               AS es_laboratorio,
       i.monto                        AS monto
FROM comprobantes c
JOIN consultas co        ON co.id = c.consulta_id
JOIN veterinarios v      ON v.id = co.veterinario_id
JOIN clinicas cl         ON cl.id = v.clinica_id
JOIN items_comprobante i ON i.comprobante_id = c.id
WHERE c.fecha_hora >= ? AND c.fecha_hora < ?
  AND (? IS NULL OR cl.id = ?)
ORDER BY c.fecha_hora, i.id
"""


@dataclass(frozen=True)
class ItemFacturado:
    """Un ítem de comprobante, tal como sale de la base."""

    mes: date  # primer día del mes del comprobante
    clinica: str
    servicio: str
    es_laboratorio: bool
    monto: Decimal


@dataclass(frozen=True)
class RenglonFacturacion:
    mes: date
    clinica: str
    servicio: str
    es_laboratorio: bool
    cantidad: int
    facturado: Decimal
    mes_anterior: Decimal

    @property
    def variacion(self) -> Decimal | None:
        return variacion_porcentual(self.facturado, self.mes_anterior)


@dataclass(frozen=True)
class TotalMes:
    mes: date
    cantidad: int
    facturado: Decimal
    mes_anterior: Decimal

    @property
    def variacion(self) -> Decimal | None:
        return variacion_porcentual(self.facturado, self.mes_anterior)


Clave = tuple[str, bool, str]  # (clínica, es_laboratorio, servicio): los servicios de la clínica van primero


# ---------------------------------------------------------------- lectura (SQL)

def _leer(conexion: sqlite3.Connection, desde: date, hasta_exclusivo: date, clinica_id: int | None) -> list[ItemFacturado]:
    filas = conexion.execute(_SQL, (desde.isoformat(), hasta_exclusivo.isoformat(), clinica_id, clinica_id))
    return [ItemFacturado(date.fromisoformat(f["mes"] + "-01"), f["clinica"], f["servicio"],
                          bool(f["es_laboratorio"]), Decimal(f["monto"])) for f in filas]


# ---------------------------------------------------------------- cálculo (Python puro)

def calcular(items: list[ItemFacturado], meses: list[date]) -> tuple[list[RenglonFacturacion], list[TotalMes]]:
    """Agrupa los ítems por mes, clínica y servicio y compara cada mes de `meses` con el anterior.

    Un renglón aparece si el servicio facturó en ese mes o en el anterior (así una caída a cero
    también se ve, como -100 %). Los totales salen para todos los meses, aunque sean cero.
    """
    sumas: dict[tuple[date, Clave], tuple[int, Decimal]] = {}
    for item in items:
        clave = (item.mes, (item.clinica, item.es_laboratorio, item.servicio))
        cantidad, monto = sumas.get(clave, (0, Decimal("0")))
        sumas[clave] = (cantidad + 1, monto + item.monto)

    def sumado(mes: date, clave: Clave) -> tuple[int, Decimal]:
        return sumas.get((mes, clave), (0, Decimal("0")))

    renglones: list[RenglonFacturacion] = []
    totales: list[TotalMes] = []
    for mes in meses:
        anterior = sumar_meses(mes, -1)
        claves = sorted({clave for (m, clave) in sumas if m in (mes, anterior)})
        for clave in claves:
            cantidad, facturado = sumado(mes, clave)
            clinica, es_laboratorio, servicio = clave
            renglones.append(RenglonFacturacion(mes, clinica, servicio, es_laboratorio, cantidad, facturado,
                                                sumado(anterior, clave)[1]))
        totales.append(TotalMes(
            mes,
            sum(c for (m, _), (c, _) in sumas.items() if m == mes),
            sum((monto for (m, _), (_, monto) in sumas.items() if m == mes), Decimal("0")),
            sum((monto for (m, _), (_, monto) in sumas.items() if m == anterior), Decimal("0")),
        ))
    return renglones, totales


def por_clinica(items: list[ItemFacturado], meses: list[date]) -> dict[str, list[Decimal]]:
    """Lo facturado por cada clínica en cada mes (para el gráfico)."""
    clinicas = sorted({item.clinica for item in items if item.mes in meses})
    return {clinica: [sum((i.monto for i in items if i.clinica == clinica and i.mes == mes), Decimal("0"))
                      for mes in meses]
            for clinica in clinicas}


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Mes", "Clínica", "Servicio", "Tipo", "Cant.", "Facturado", "Mes anterior", "Variación"]


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    meses = meses_del_rango(filtro.desde, filtro.hasta)
    desde = sumar_meses(meses[0], -1)  # el mes anterior al primero, para su variación
    hasta_exclusivo = sumar_meses(primer_dia_del_mes(filtro.hasta), 1)
    with transaccion() as conexion:
        items = _leer(conexion, desde, hasta_exclusivo, filtro.clinica_id)
    renglones, totales = calcular(items, meses)

    filas: list[list[str]] = []
    for total in totales:
        filas += [[formato.mes(r.mes), r.clinica, r.servicio, "Laboratorio" if r.es_laboratorio else "Clínica",
                   str(r.cantidad), formato.pesos(r.facturado), formato.pesos(r.mes_anterior),
                   formato.porcentaje(r.variacion)]
                  for r in renglones if r.mes == total.mes]
        filas.append([formato.mes(total.mes), "", "TOTAL DEL MES", "", str(total.cantidad),
                      formato.pesos(total.facturado), formato.pesos(total.mes_anterior),
                      formato.porcentaje(total.variacion)])

    notas = [f"Meses completos del {formato.mes(meses[0])} al {formato.mes(meses[-1])}. "
             f"Total del período: {formato.pesos(sum((t.facturado for t in totales), Decimal('0')))}."]
    if not renglones:
        notas.append("No hay comprobantes en el período elegido.")
    grafico = Grafico(
        "Facturado por mes y clínica",
        [formato.mes(mes) for mes in meses],
        {clinica: [float(m) for m in montos] for clinica, montos in por_clinica(items, meses).items()},
        "Pesos",
    )
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico if renglones else None)

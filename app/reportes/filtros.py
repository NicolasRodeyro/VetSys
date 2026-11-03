"""Filtros comunes a todos los reportes: rango de fechas y clínica."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.dominio.fechas import sumar_meses
from app.servicios.excepciones import EntradaInvalida


@dataclass(frozen=True)
class FiltroReporte:
    """`desde` y `hasta` incluyen el día completo. `clinica_id` None significa todas las clínicas.

    Cada reporte decide sobre qué fecha aplica el rango (la del comprobante, la del despacho...)
    y lo dice en su descripción.
    """

    desde: date
    hasta: date
    clinica_id: int | None = None

    def __post_init__(self) -> None:
        # EntradaInvalida hereda de ReglaNegocio: la pantalla la muestra sin código extra.
        if self.desde > self.hasta:
            raise EntradaInvalida("La fecha «desde» no puede ser posterior a «hasta».")


def primer_dia_del_mes(fecha: date) -> date:
    return fecha.replace(day=1)


def meses_del_rango(desde: date, hasta: date) -> list[date]:
    """El primer día de cada mes que toca el rango, en orden: 15/08 a 02/10 -> [01/08, 01/09, 01/10]."""
    meses, mes = [], primer_dia_del_mes(desde)
    while mes <= hasta:
        meses.append(mes)
        mes = sumar_meses(mes, 1)
    return meses


def rango_por_defecto(hoy: date) -> tuple[date, date]:
    """Los dos meses anteriores más el mes en curso: lo que la pantalla propone al abrirse."""
    return sumar_meses(primer_dia_del_mes(hoy), -2), hoy

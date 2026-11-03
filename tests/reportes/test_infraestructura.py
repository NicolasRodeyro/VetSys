"""Piezas comunes de los reportes: filtros, formato, variación y gráfico."""

from datetime import date
from decimal import Decimal

import pytest

from app.reportes import formato, graficos
from app.reportes.estadistica import variacion_porcentual
from app.reportes.filtros import FiltroReporte, meses_del_rango, rango_por_defecto
from app.reportes.resultado import Grafico
from app.servicios.excepciones import EntradaInvalida


def test_el_filtro_rechaza_desde_posterior_a_hasta():
    with pytest.raises(EntradaInvalida, match="posterior"):
        FiltroReporte(date(2026, 10, 2), date(2026, 10, 1))


def test_el_filtro_acepta_un_solo_dia():
    assert FiltroReporte(date(2026, 10, 1), date(2026, 10, 1)).clinica_id is None


def test_meses_del_rango_incluye_los_meses_de_los_extremos_y_cruza_el_anio():
    assert meses_del_rango(date(2025, 11, 15), date(2026, 2, 2)) == [
        date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)]
    assert meses_del_rango(date(2026, 10, 31), date(2026, 10, 31)) == [date(2026, 10, 1)]


def test_rango_por_defecto_son_los_dos_meses_anteriores_y_el_actual():
    assert rango_por_defecto(date(2026, 1, 20)) == (date(2025, 11, 1), date(2026, 1, 20))


@pytest.mark.parametrize("actual, anterior, esperada", [
    ("110", "100", Decimal("10")),
    ("50", "200", Decimal("-75")),
    ("0", "80", Decimal("-100")),
    ("100", "100", Decimal("0")),
])
def test_variacion_porcentual(actual, anterior, esperada):
    assert variacion_porcentual(Decimal(actual), Decimal(anterior)) == esperada


def test_sin_mes_anterior_no_hay_variacion():
    assert variacion_porcentual(Decimal("500"), Decimal("0")) is None


def test_formato_de_montos_porcentajes_y_meses():
    assert formato.pesos(Decimal("25300.75")) == "$ 25.300,75"
    assert formato.porcentaje(Decimal("66.68333")) == "+66,7 %"
    assert formato.porcentaje(Decimal("-100")) == "-100,0 %"
    assert formato.porcentaje(None) == "—"
    assert formato.mes(date(2026, 9, 1)) == "09/2026"


@pytest.mark.parametrize("series", [
    {"Clínica Centro": [1000.0, 2500.5, 0.0], "Clínica Norte": [0.0, 800.0, 1200.0]},
    {"Una sola": [3.0, 1.0, 2.0]},
])
def test_el_grafico_es_un_png(series):
    png = graficos.a_png(Grafico("Prueba", ["08/2026", "09/2026", "10/2026"], series, "Pesos"))
    assert png.startswith(b"\x89PNG")

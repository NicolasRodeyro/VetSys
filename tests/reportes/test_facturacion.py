"""Reporte de facturación: el cálculo se prueba sin base; la lectura, con comprobantes reales."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.reportes import facturacion
from app.reportes.facturacion import ItemFacturado, RenglonFacturacion, TotalMes, calcular
from app.reportes.filtros import FiltroReporte
from app.servicios import catalogos, consultas, tiempo
from tests.servicios.conftest import mascota, veterinario

AGO, SEP, OCT = date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)
D = Decimal


def item(mes, servicio, monto, clinica="Centro", laboratorio=False):
    return ItemFacturado(mes, clinica, servicio, laboratorio, D(monto))


# Agosto es solo la base de comparación de septiembre.
ITEMS = [
    item(AGO, "Consulta", "3000"),
    item(AGO, "Hemograma", "12500", laboratorio=True),
    item(SEP, "Consulta", "3000"),
    item(SEP, "Consulta", "2000.50"),
    item(SEP, "Hemograma", "12500", laboratorio=True),
    item(SEP, "Urgencia", "8000", clinica="Norte"),
    item(OCT, "Consulta", "4000"),
]


# ---------------------------------------------------------------- cálculo (sin base)

def test_agrupa_por_mes_clinica_y_servicio_y_compara_con_el_mes_anterior():
    renglones, _ = calcular(ITEMS, [SEP, OCT])

    assert renglones == [
        # septiembre: la consulta subió de 3000 a 5000,50; el hemograma quedó igual; Norte no tenía base
        RenglonFacturacion(SEP, "Centro", "Consulta", False, 2, D("5000.50"), D("3000")),
        RenglonFacturacion(SEP, "Centro", "Hemograma", True, 1, D("12500"), D("12500")),
        RenglonFacturacion(SEP, "Norte", "Urgencia", False, 1, D("8000"), D("0")),
        # octubre: los servicios que facturaron en septiembre y no en octubre aparecen en cero
        RenglonFacturacion(OCT, "Centro", "Consulta", False, 1, D("4000"), D("5000.50")),
        RenglonFacturacion(OCT, "Centro", "Hemograma", True, 0, D("0"), D("12500")),
        RenglonFacturacion(OCT, "Norte", "Urgencia", False, 0, D("0"), D("8000")),
    ]


def test_variaciones_calculadas_a_mano():
    renglones, totales = calcular(ITEMS, [SEP, OCT])
    variaciones = [r.variacion for r in renglones]

    assert round(variaciones[0], 4) == D("66.6833")  # (5000,50 - 3000) / 3000 x 100
    assert variaciones[1] == 0
    assert variaciones[2] is None  # sin base: no hay variación
    assert round(variaciones[3], 4) == D("-20.0080")  # (4000 - 5000,50) / 5000,50 x 100
    assert variaciones[4] == variaciones[5] == -100
    assert round(totales[0].variacion, 4) == D("64.5194")  # (25500,50 - 15500) / 15500 x 100


def test_totales_por_mes_incluyen_los_meses_sin_facturacion():
    _, totales = calcular(ITEMS, [SEP, OCT, date(2026, 11, 1)])

    assert totales == [
        TotalMes(SEP, 4, D("25500.50"), D("15500")),
        TotalMes(OCT, 1, D("4000"), D("25500.50")),
        TotalMes(date(2026, 11, 1), 0, D("0"), D("4000")),
    ]


def test_los_montos_se_suman_con_decimal_sin_errores_de_redondeo():
    items = [item(SEP, "Consulta", "0.10"), item(SEP, "Consulta", "0.20")]
    _, totales = calcular(items, [SEP])
    assert totales[0].facturado == D("0.30")  # con float daría 0.30000000000000004


def test_sin_items_no_hay_renglones_pero_si_totales_en_cero():
    renglones, totales = calcular([], [SEP])
    assert renglones == [] and totales == [TotalMes(SEP, 0, D("0"), D("0"))]


# ---------------------------------------------------------------- con la base (comprobantes reales)

def cerrar_consulta_el(monkeypatch, cuando, dni, nombre, matricula, tipo, honorarios, *analisis):
    """Registra y cierra una consulta con el reloj del sistema en `cuando` (fecha del comprobante)."""
    consulta = consultas.registrar_consulta(mascota(dni, nombre).id, veterinario(matricula).id, tipo, fecha_hora=cuando)
    for nombre_analisis in analisis:
        consultas.emitir_orden(consulta.id, nombre_analisis)
    with monkeypatch.context() as m:
        m.setattr(tiempo, "ahora", lambda: cuando)
        consultas.cerrar_consulta(consulta.id, honorarios)


@pytest.fixture
def comprobantes(con_seed, monkeypatch):
    # Clínica Centro (MP-1001, Toby) y Clínica Norte (MP-2001, Rex)
    cerrar_consulta_el(monkeypatch, datetime(2026, 8, 31, 23, 59), "30111222", "Toby", "MP-1001", "CONSULTA", "3000", "Hemograma")
    cerrar_consulta_el(monkeypatch, datetime(2026, 9, 1, 0, 0), "30111222", "Toby", "MP-1001", "CONSULTA", "3000")
    cerrar_consulta_el(monkeypatch, datetime(2026, 9, 20, 10, 0), "30111222", "Toby", "MP-1001", "CONSULTA", "2000.50", "Hemograma")
    cerrar_consulta_el(monkeypatch, datetime(2026, 9, 21, 11, 0), "28444555", "Rex", "MP-2001", "URGENCIA", "8000")
    cerrar_consulta_el(monkeypatch, datetime(2026, 10, 31, 23, 59), "30111222", "Toby", "MP-1001", "CONTROL", "4000")
    cerrar_consulta_el(monkeypatch, datetime(2026, 11, 1, 0, 0), "28444555", "Rex", "MP-2001", "URGENCIA", "999")  # fuera


def clinica(nombre):
    return next(x.id for x in catalogos.listar_clinicas() if x.nombre == nombre)


def test_lee_los_comprobantes_por_mes_y_clinica_del_veterinario(comprobantes):
    resultado = facturacion.generar(FiltroReporte(date(2026, 9, 15), date(2026, 10, 2)))

    assert resultado.columnas[:3] == ["Mes", "Clínica", "Servicio"]
    assert resultado.filas == [
        ["09/2026", "Clínica Centro", "Consulta", "Clínica", "2", "$ 5.000,50", "$ 3.000,00", "+66,7 %"],
        ["09/2026", "Clínica Centro", "Hemograma", "Laboratorio", "1", "$ 12.500,00", "$ 12.500,00", "+0,0 %"],
        ["09/2026", "Clínica Norte", "Urgencia", "Clínica", "1", "$ 8.000,00", "$ 0,00", "—"],
        ["09/2026", "", "TOTAL DEL MES", "", "4", "$ 25.500,50", "$ 15.500,00", "+64,5 %"],
        ["10/2026", "Clínica Centro", "Consulta", "Clínica", "0", "$ 0,00", "$ 5.000,50", "-100,0 %"],
        ["10/2026", "Clínica Centro", "Control", "Clínica", "1", "$ 4.000,00", "$ 0,00", "—"],
        ["10/2026", "Clínica Centro", "Hemograma", "Laboratorio", "0", "$ 0,00", "$ 12.500,00", "-100,0 %"],
        ["10/2026", "Clínica Norte", "Urgencia", "Clínica", "0", "$ 0,00", "$ 8.000,00", "-100,0 %"],
        ["10/2026", "", "TOTAL DEL MES", "", "1", "$ 4.000,00", "$ 25.500,50", "-84,3 %"],
    ]
    assert "Total del período: $ 29.500,50" in resultado.notas[0]
    assert resultado.grafico.etiquetas == ["09/2026", "10/2026"]
    assert resultado.grafico.series == {"Clínica Centro": [17500.5, 4000.0], "Clínica Norte": [8000.0, 0.0]}


def test_filtra_por_clinica(comprobantes):
    resultado = facturacion.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30), clinica("Clínica Norte")))

    assert resultado.filas == [
        ["09/2026", "Clínica Norte", "Urgencia", "Clínica", "1", "$ 8.000,00", "$ 0,00", "—"],
        ["09/2026", "", "TOTAL DEL MES", "", "1", "$ 8.000,00", "$ 0,00", "—"],
    ]
    assert list(resultado.grafico.series) == ["Clínica Norte"]


def test_un_periodo_sin_comprobantes_lo_avisa_y_no_tiene_grafico(comprobantes):
    resultado = facturacion.generar(FiltroReporte(date(2026, 6, 1), date(2026, 6, 30)))

    assert resultado.filas == [["06/2026", "", "TOTAL DEL MES", "", "0", "$ 0,00", "$ 0,00", "—"]]
    assert "No hay comprobantes en el período elegido." in resultado.notas
    assert resultado.grafico is None

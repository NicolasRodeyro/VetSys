"""Reporte de tiempos de tránsito y procesamiento: el cálculo se prueba sin base; la lectura, con historiales reales."""

from datetime import date, datetime, timedelta

import pytest

from app.reportes import tiempos
from app.reportes.filtros import FiltroReporte
from app.reportes.tiempos import Envio, Grupo, resumir
from app.reportes.transporte import SIN_TRAMOS
from tests.reportes import datos

pytestmark = pytest.mark.usefixtures("con_seed")


def envio(muestra_id=1, clinica="Centro", remito_id=1, horas_max=24, transito=None, procesamiento=None):
    """Un Envio cuyo tránsito y procesamiento duran exactamente las horas indicadas."""
    despacho = datetime(2026, 9, 10, 8, 0)
    llegada = None if transito is None else despacho + timedelta(hours=transito)
    analizada = None if procesamiento is None or llegada is None else llegada + timedelta(hours=procesamiento)
    return Envio(muestra_id, clinica, remito_id, horas_max, despacho, llegada, llegada, analizada)


# ---------------------------------------------------------------- cálculo (sin base)

def test_un_envio_mide_su_transito_y_su_procesamiento():
    e = envio(transito=6, procesamiento=12)
    assert (e.transito, e.procesamiento) == (6, 12)


def test_un_envio_que_no_llego_no_tiene_tiempos():
    e = envio()
    assert e.transito is None and e.procesamiento is None and not e.fuera_de_plazo


def test_el_plazo_se_supera_solo_con_mas_horas_que_el_maximo():
    assert not envio(transito=24, horas_max=24).fuera_de_plazo  # justo en el máximo: dentro del plazo
    assert envio(transito=24.5, horas_max=24).fuera_de_plazo
    assert not envio(transito=30, horas_max=72).fuera_de_plazo  # el máximo depende del tipo de análisis


def test_resumen_de_mediana_y_p90_calculados_a_mano():
    r = resumir([envio(1, transito=6, procesamiento=12), envio(2, transito=28, procesamiento=24),
                 envio(3, transito=24, procesamiento=6), envio(4)])  # la 4 sigue en tránsito
    assert r.muestras == 4 and r.con_transito == 3 and r.en_transito == 1
    assert r.transito_mediana == 24 and round(r.transito_p90, 6) == 27.2  # [6, 24, 28]: 24 + (28 - 24) x 0,8
    assert r.procesamiento_mediana == 12 and round(r.procesamiento_p90, 6) == 21.6  # [6, 12, 24]
    assert r.fuera_de_plazo == 1


def test_resumen_sin_datos():
    r = resumir([])
    assert (r.muestras, r.transito_mediana, r.procesamiento_p90, r.en_transito) == (0, None, None, 0)


def test_agrupa_por_clinica_y_por_transportista_y_cuenta_una_vez_por_cada_transportista():
    envios = [envio(1, "Norte", remito_id=10), envio(2, "Centro", remito_id=20), envio(3, "Centro", remito_id=30)]
    grupos = tiempos.agrupar(envios, {10: ["Sur"], 20: ["Sur", "Veloz"]})  # el remito 30 no tiene tramos

    assert [(g.agrupacion, g.nombre, [e.muestra_id for e in g.envios]) for g in grupos] == [
        ("Clínica", "Centro", [2, 3]), ("Clínica", "Norte", [1]),
        ("Transportista", SIN_TRAMOS, [3]), ("Transportista", "Sur", [1, 2]), ("Transportista", "Veloz", [2]),
        ("Total", "Todas las muestras", [1, 2, 3])]


def test_sin_envios_no_hay_grupos():
    assert tiempos.agrupar([], {}) == []
    assert Grupo("Total", "x").envios == []


# ---------------------------------------------------------------- con la base (historiales reales)

@pytest.fixture
def historiales():
    """Seis muestras despachadas en septiembre (más una de agosto). Los tiempos esperados están en cada línea."""
    def caso(numero, clinica, transportistas, analisis, *cambios, estado_remito="EN_TRANSITO"):
        m = datos.muestra(datos.nueva_orden(analisis), *cambios)
        datos.remito(numero, clinica, m, transportistas, estado_remito)

    centro, norte = "Clínica Centro", "Clínica Norte"
    caso("R1", centro, ("Transportes Sur",), "Hemograma", ("EN_TRANSITO", "2026-09-10 08:00"), ("RECIBIDA", "2026-09-10 14:00"),
         ("ANALIZADA", "2026-09-11 02:00"))  # tránsito 6 h, procesamiento 12 h
    caso("R2", centro, ("Logística Norte",), "Hemograma", ("EN_TRANSITO", "2026-09-10 08:00"), ("RECIBIDA", "2026-09-11 12:00"),
         ("ANALIZADA", "2026-09-12 12:00"))  # 28 h (fuera de plazo: máximo 24), 24 h
    caso("R3", norte, ("Logística Norte",), "Hemograma", ("EN_TRANSITO", "2026-09-12 09:00"),
         ("RECHAZADA", "2026-09-12 19:00", ("PRECINTO_ROTO",)))  # 10 h
    caso("R4", centro, ("Transportes Sur", "Logística Norte"), "Hemograma", ("EN_TRANSITO", "2026-09-15 08:00"),
         ("RECIBIDA", "2026-09-16 08:00"), ("ANALIZADA", "2026-09-16 14:00"))  # justo 24 h (dentro del plazo), 6 h
    caso("R5", centro, ("Transportes Sur",), "Hemograma", ("EN_TRANSITO", "2026-09-20 10:00"))  # todavía en tránsito
    caso("R6", centro, ("Transportes Sur",), "Hemograma", ("EN_TRANSITO", "2026-08-31 22:00"), ("RECIBIDA", "2026-09-01 02:00"))  # agosto
    caso("R7", centro, ("Transportes Sur",), "Biopsia", ("EN_TRANSITO", "2026-09-17 08:00"), ("RECIBIDA", "2026-09-18 14:00"))  # 30 h de 72


def clinica(nombre):
    from app.servicios import catalogos
    return next(x.id for x in catalogos.listar_clinicas() if x.nombre == nombre)


def test_calcula_los_tiempos_por_clinica_transportista_y_total(historiales):
    r = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30)))

    assert r.columnas[:2] == ["Agrupación", "Grupo"]
    assert r.filas == [
        # Centro: tránsitos [6, 24, 28, 30] -> mediana 26, P90 29,4; solo la de 28 h superó su máximo de 24 h
        ["Clínica", "Clínica Centro", "5", "26,0 h", "29,4 h", "1 de 4 (25,0 %)", "12,0 h", "21,6 h", "1"],
        ["Clínica", "Clínica Norte", "1", "10,0 h", "10,0 h", "0 de 1 (0,0 %)", "—", "—", "0"],
        ["Transportista", "Logística Norte", "3", "24,0 h", "27,2 h", "1 de 3 (33,3 %)", "15,0 h", "22,2 h", "0"],
        ["Transportista", "Transportes Sur", "4", "24,0 h", "28,8 h", "0 de 3 (0,0 %)", "9,0 h", "11,4 h", "1"],
        ["Total", "Todas las muestras", "6", "24,0 h", "29,2 h", "1 de 5 (20,0 %)", "12,0 h", "21,6 h", "1"],
    ]


def test_la_muestra_de_agosto_no_entra_y_la_que_sigue_en_transito_se_informa(historiales):
    r = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30)))
    total = r.filas[-1]
    assert total[2] == "6" and total[8] == "1"  # R6 (despachada el 31/08) queda afuera; R5 sigue en tránsito


def test_el_rango_se_aplica_a_la_fecha_de_despacho_incluyendo_el_ultimo_dia(historiales):
    solo_agosto = tiempos.generar(FiltroReporte(date(2026, 8, 31), date(2026, 8, 31)))
    assert solo_agosto.filas == [
        ["Clínica", "Clínica Centro", "1", "4,0 h", "4,0 h", "0 de 1 (0,0 %)", "—", "—", "0"],
        ["Transportista", "Transportes Sur", "1", "4,0 h", "4,0 h", "0 de 1 (0,0 %)", "—", "—", "0"],
        ["Total", "Todas las muestras", "1", "4,0 h", "4,0 h", "0 de 1 (0,0 %)", "—", "—", "0"]]

    hasta_el_10 = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 10)))
    assert hasta_el_10.filas[-1][2] == "2"  # R1 y R2, despachadas el 10/09 a las 08:00


def test_filtra_por_la_clinica_de_origen_del_remito(historiales):
    r = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30), clinica("Clínica Norte")))
    assert r.filas == [
        ["Clínica", "Clínica Norte", "1", "10,0 h", "10,0 h", "0 de 1 (0,0 %)", "—", "—", "0"],
        ["Transportista", "Logística Norte", "1", "10,0 h", "10,0 h", "0 de 1 (0,0 %)", "—", "—", "0"],
        ["Total", "Todas las muestras", "1", "10,0 h", "10,0 h", "0 de 1 (0,0 %)", "—", "—", "0"]]


def test_el_grafico_compara_mediana_y_p90_de_cada_grupo(historiales):
    g = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30))).grafico
    assert g.etiquetas == ["Clínica Centro", "Clínica Norte", "Logística Norte", "Transportes Sur"]
    assert g.series["Mediana"] == [26.0, 10.0, 24.0, 24.0]
    assert [round(x, 1) for x in g.series["P90"]] == [29.4, 10.0, 27.2, 28.8]


def test_un_periodo_sin_despachos_lo_avisa_y_no_tiene_grafico(historiales):
    r = tiempos.generar(FiltroReporte(date(2026, 6, 1), date(2026, 6, 30)))
    assert r.filas == [] and r.grafico is None
    assert "No hay muestras despachadas en el período elegido." in r.notas


def test_un_remito_sin_tramos_se_agrupa_aparte(con_seed):
    m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-09-10 08:00"), ("RECIBIDA", "2026-09-10 11:00"))
    datos.remito("R1", "Clínica Centro", m)  # sin transportistas
    r = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30)))
    assert ["Transportista", SIN_TRAMOS, "1", "3,0 h", "3,0 h", "0 de 1 (0,0 %)", "—", "—", "0"] in r.filas


def test_con_solo_las_muestras_en_transito_no_hay_grafico_pero_si_filas(con_seed):
    m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-09-10 08:00"))
    datos.remito("R1", "Clínica Centro", m, ("Transportes Sur",))
    r = tiempos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30)))
    assert r.filas[0] == ["Clínica", "Clínica Centro", "1", "—", "—", "—", "—", "—", "1"]
    assert r.grafico is None

"""Reporte de tasa de rechazo: el cálculo se prueba sin base; la lectura, con recepciones reales."""

from datetime import date, datetime

import pytest

from app.reportes import rechazos
from app.reportes.filtros import FiltroReporte
from app.reportes.rechazos import Llegada, Tasa, calcular
from app.reportes.transporte import SIN_TRAMOS
from app.servicios import catalogos
from tests.reportes import datos

pytestmark = pytest.mark.usefixtures("con_seed")

SEP = FiltroReporte(date(2026, 9, 1), date(2026, 9, 30))


def llegada(muestra_id, clinica, remito_id, rechazada=False, motivos=()):
    return Llegada(muestra_id, datetime(2026, 9, 10, 10, 0), rechazada, clinica, remito_id, f"R{remito_id}", "Hemograma",
                   "Toby", None, None, motivos)


# ---------------------------------------------------------------- cálculo (sin base)

def test_la_tasa_se_calcula_por_clinica_transportista_motivo_y_total():
    llegadas = [llegada(1, "Centro", 1), llegada(2, "Centro", 2, True, ("PRECINTO_ROTO",)),
                llegada(3, "Norte", 3, True, ("PRECINTO_ROTO", "TEMPERATURA_FUERA_DE_RANGO"))]
    tasas = calcular(llegadas, {1: ["Sur"], 2: ["Veloz"], 3: ["Veloz"]})

    assert tasas == [
        Tasa("Clínica", "Centro", 2, 1), Tasa("Clínica", "Norte", 1, 1),
        Tasa("Transportista", "Sur", 1, 0), Tasa("Transportista", "Veloz", 2, 2),
        # por motivo: el denominador es el total de las que llegaron (3), y la de dos motivos cuenta en los dos
        Tasa("Motivo", "Precinto roto", 3, 2), Tasa("Motivo", "Temperatura fuera de rango", 3, 1),
        Tasa("Total", "Todas las muestras", 3, 2)]


def test_sin_llegadas_no_hay_tasas():
    assert calcular([], {}) == []


def test_un_remito_sin_tramos_se_agrupa_aparte():
    assert Tasa("Transportista", SIN_TRAMOS, 1, 0) in calcular([llegada(1, "Centro", 9)], {})


# ---------------------------------------------------------------- con la base (recepciones reales)

@pytest.fixture
def recepciones():
    """Cinco muestras llegaron en septiembre (dos se rechazaron); una sigue en tránsito y una se rechazó en agosto."""
    ids = {}

    def caso(nombre, numero, clinica, transportistas, *cambios, recepcion=None, estado="RECIBIDO", mascota=("Toby", "30111222", "MP-1001")):
        analisis = "Hemograma"
        orden = datos.nueva_orden(analisis, mascota[1], mascota[0], mascota[2])
        ids[nombre] = datos.muestra(orden, *cambios)
        datos.remito(numero, clinica, ids[nombre], transportistas, estado, recepcion)

    centro, norte = "Clínica Centro", "Clínica Norte"
    sur, veloz = "Transportes Sur", "Logística Norte"
    caso("M1", "R1", centro, (sur,), ("EN_TRANSITO", "2026-09-09 08:00"), ("RECIBIDA", "2026-09-10 10:00"),
         recepcion=("2026-09-10 10:00", "INTACTO", 5.0, True))
    caso("M2", "R2", centro, (veloz,), ("EN_TRANSITO", "2026-09-10 08:00"), ("RECHAZADA", "2026-09-11 09:00", ("PRECINTO_ROTO",)),
         recepcion=("2026-09-11 09:00", "ROTO", 5.0, False), estado="RECHAZADO")
    caso("M3", "R3", norte, (veloz,), ("EN_TRANSITO", "2026-09-11 08:00"),
         ("RECHAZADA", "2026-09-12 10:30", ("PRECINTO_ROTO", "TEMPERATURA_FUERA_DE_RANGO")),
         recepcion=("2026-09-12 10:30", "ROTO", 15.5, False), estado="RECHAZADO", mascota=("Rex", "28444555", "MP-2001"))
    caso("M4", "R4", centro, (sur, veloz), ("EN_TRANSITO", "2026-09-12 08:00"), ("RECIBIDA", "2026-09-13 11:00"),
         recepcion=("2026-09-13 11:00", "INTACTO", 4.5, True))
    caso("M5", "R5", norte, (sur,), ("EN_TRANSITO", "2026-09-13 08:00"), ("RECIBIDA", "2026-09-14 08:00"),
         recepcion=("2026-09-14 08:00", "INTACTO", 5.0, True))
    caso("M6", "R6", centro, (sur,), ("EN_TRANSITO", "2026-09-20 08:00"))  # todavía en tránsito: no llegó
    caso("M7", "R7", centro, (sur,), ("EN_TRANSITO", "2026-08-29 08:00"), ("RECHAZADA", "2026-08-30 09:00", ("PRECINTO_ROTO",)),
         recepcion=("2026-08-30 09:00", "ROTO", 5.0, False), estado="RECHAZADO")  # agosto: fuera del rango
    return ids


def clinica(nombre):
    return next(x.id for x in catalogos.listar_clinicas() if x.nombre == nombre)


def test_calcula_la_tasa_de_rechazo_por_clinica_transportista_y_motivo(recepciones):
    r = rechazos.generar(SEP)

    assert r.columnas == ["Agrupación", "Grupo", "Llegaron", "Rechazadas", "Tasa de rechazo"]
    assert r.filas == [
        ["Clínica", "Clínica Centro", "3", "1", "33,3 %"],
        ["Clínica", "Clínica Norte", "2", "1", "50,0 %"],
        ["Transportista", "Logística Norte", "3", "2", "66,7 %"],  # M2, M3 y M4
        ["Transportista", "Transportes Sur", "3", "0", "0,0 %"],  # M1, M4 y M5
        ["Motivo", "Precinto roto", "5", "2", "40,0 %"],
        ["Motivo", "Temperatura fuera de rango", "5", "1", "20,0 %"],
        ["Total", "Todas las muestras", "5", "2", "40,0 %"],
    ]


def test_la_muestra_en_transito_y_la_de_agosto_no_entran(recepciones):
    total = rechazos.generar(SEP).filas[-1]
    assert total[2:] == ["5", "2", "40,0 %"]  # M6 no llegó; M7 se rechazó el 30/08


def test_el_detalle_lista_cada_muestra_rechazada_con_precinto_y_temperatura(recepciones):
    r = rechazos.generar(SEP)

    assert r.detalle_titulo == "Muestras rechazadas"
    assert r.detalle_columnas[:3] == ["Fecha", "Muestra", "Análisis"]
    assert r.detalle_filas == [
        ["11/09/2026 09:00", f"#{recepciones['M2']}", "Hemograma", "Toby", "Clínica Centro", "R2", "Logística Norte",
         "Precinto roto", "Roto", "5 °C"],
        ["12/09/2026 10:30", f"#{recepciones['M3']}", "Hemograma", "Rex", "Clínica Norte", "R3", "Logística Norte",
         "Precinto roto, Temperatura fuera de rango", "Roto", "15,5 °C"],
    ]


def test_el_rango_se_aplica_a_la_fecha_de_la_recepcion_y_agosto_aparece_si_se_pide(recepciones):
    agosto = rechazos.generar(FiltroReporte(date(2026, 8, 1), date(2026, 8, 31)))
    assert agosto.filas[-1][2:] == ["1", "1", "100,0 %"]
    assert agosto.detalle_filas[0][1] == f"#{recepciones['M7']}"


def test_el_ultimo_minuto_del_rango_entra_y_la_medianoche_siguiente_no(con_seed):
    def recibida(numero, cuando):
        m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-09-29 08:00"), ("RECIBIDA", cuando))
        datos.remito(numero, "Clínica Centro", m, ("Transportes Sur",), recepcion=(cuando, "INTACTO", 5.0, True))

    recibida("R1", "2026-09-30 23:59")
    recibida("R2", "2026-10-01 00:00")
    assert rechazos.generar(SEP).filas[-1][2] == "1"


def test_filtra_por_la_clinica_de_origen(recepciones):
    r = rechazos.generar(FiltroReporte(date(2026, 9, 1), date(2026, 9, 30), clinica("Clínica Norte")))
    assert r.filas == [
        ["Clínica", "Clínica Norte", "2", "1", "50,0 %"],
        ["Transportista", "Logística Norte", "1", "1", "100,0 %"],
        ["Transportista", "Transportes Sur", "1", "0", "0,0 %"],
        ["Motivo", "Precinto roto", "2", "1", "50,0 %"],
        ["Motivo", "Temperatura fuera de rango", "2", "1", "50,0 %"],
        ["Total", "Todas las muestras", "2", "1", "50,0 %"],
    ]
    assert len(r.detalle_filas) == 1


def test_el_grafico_muestra_la_tasa_de_cada_clinica_y_transportista(recepciones):
    g = rechazos.generar(SEP).grafico
    assert g.etiquetas == ["Clínica Centro", "Clínica Norte", "Logística Norte", "Transportes Sur"]
    assert [round(x, 1) for x in g.series["Tasa de rechazo (%)"]] == [33.3, 50.0, 66.7, 0.0]


def test_un_periodo_sin_llegadas_lo_avisa_y_no_tiene_grafico_ni_detalle(recepciones):
    r = rechazos.generar(FiltroReporte(date(2026, 6, 1), date(2026, 6, 30)))
    assert r.filas == [] and r.grafico is None and r.detalle_filas == [] and r.detalle_titulo == ""
    assert "No llegaron muestras al laboratorio en el período elegido." in r.notas


def test_sin_rechazos_la_tasa_es_cero_y_no_hay_detalle(con_seed):
    m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-09-09 08:00"), ("RECIBIDA", "2026-09-10 10:00"))
    datos.remito("R1", "Clínica Centro", m, ("Transportes Sur",), recepcion=("2026-09-10 10:00", "INTACTO", 5.0, True))
    r = rechazos.generar(SEP)
    assert r.filas[-1] == ["Total", "Todas las muestras", "1", "0", "0,0 %"]
    assert not any(f[0] == "Motivo" for f in r.filas) and r.detalle_filas == []


def test_una_rechazada_sin_detalle_de_recepcion_muestra_guiones(con_seed):
    m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-09-09 08:00"), ("RECHAZADA", "2026-09-10 10:00", ("PRECINTO_ROTO",)))
    datos.remito("R1", "Clínica Centro", m, ("Transportes Sur",), estado="RECHAZADO")  # sin recepción registrada
    fila = rechazos.generar(SEP).detalle_filas[0]
    assert fila[-2:] == ["—", "—"]

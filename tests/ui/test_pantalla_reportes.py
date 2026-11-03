from datetime import datetime

import pytest

from app.reportes import REPORTES
from app.ui.pantallas.reportes import TODAS, PantallaReportes
from tests.reportes import datos
from tests.reportes.test_facturacion import cerrar_consulta_el
from tests.ui.conftest import elegir, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaReportes:
    pantalla = PantallaReportes(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


def elegir_reporte(pantalla, clave):
    pantalla.reporte.value = clave
    pantalla.elegir_reporte()


@pytest.fixture
def un_comprobante(monkeypatch):
    cerrar_consulta_el(monkeypatch, datetime(2026, 10, 5, 10, 0), "30111222", "Toby", "MP-1001", "CONSULTA", "3000", "Hemograma")


def test_los_botones_no_reciben_el_evento(pantalla):
    assert sin_parametros(pantalla.generar) and sin_parametros(pantalla.elegir_reporte)


def test_al_abrir_propone_los_dos_meses_anteriores_y_todas_las_clinicas(pantalla):
    # El reloj de los tests está en el 02/11/2026.
    assert (pantalla.desde.value, pantalla.hasta.value) == ("2026-09-01", "2026-11-02")
    assert pantalla.clinica.value == TODAS
    assert [o.text for o in pantalla.clinica.options] == ["Todas", "Clínica Centro", "Clínica Norte"]
    assert [o.key for o in pantalla.reporte.options] == list(REPORTES)
    assert pantalla.descripcion.value == REPORTES[pantalla.reporte.value].DESCRIPCION


def test_generar_muestra_la_tabla_las_notas_y_el_grafico(pantalla, un_comprobante, mensajes):
    elegir_reporte(pantalla, "facturacion")
    pantalla.generar()

    assert mensajes.errores == []
    assert pantalla.resultado.visible
    assert pantalla.titulo_resultado.value == "Facturación por clínica y servicio"
    assert ["10/2026", "Clínica Centro", "Hemograma", "Laboratorio", "1", "$ 12.500,00", "$ 0,00", "—"] \
        in pantalla.tabla.textos()
    assert pantalla.notas.controls
    assert pantalla.lugar_grafico.content.src.startswith(b"\x89PNG")


def test_filtrar_por_otra_clinica_deja_la_tabla_sin_ventas(pantalla, un_comprobante):
    elegir_reporte(pantalla, "facturacion")
    elegir(pantalla.clinica, "Clínica Norte")
    pantalla.generar()

    assert all(fila[2] == "TOTAL DEL MES" for fila in pantalla.tabla.textos())
    assert pantalla.lugar_grafico.content is None


@pytest.mark.parametrize("desde, hasta, error", [
    ("2026-11-01", "2026-10-01", "posterior"),
    ("ayer", "2026-10-01", "Desde"),
    ("2026-10-01", "", "Hasta"),
])
def test_filtros_invalidos_se_explican_al_usuario(pantalla, mensajes, desde, hasta, error):
    pantalla.desde.value, pantalla.hasta.value = desde, hasta
    pantalla.generar()

    assert error in mensajes.errores[-1]
    assert not pantalla.resultado.visible


def test_cambiar_de_reporte_oculta_el_resultado_anterior(pantalla, un_comprobante):
    pantalla.generar()
    pantalla.elegir_reporte()
    assert not pantalla.resultado.visible


# ---------------------------------------------------------------- los otros tres reportes

def test_los_cuatro_reportes_estan_en_la_pantalla_en_este_orden(pantalla):
    assert [o.key for o in pantalla.reporte.options] == ["tiempos", "rechazos", "vacunas", "facturacion"]


@pytest.mark.parametrize("clave", ["tiempos", "rechazos", "vacunas", "facturacion"])
def test_cada_reporte_se_genera_sin_errores_aunque_no_haya_movimientos(pantalla, mensajes, clave):
    elegir_reporte(pantalla, clave)
    pantalla.generar()

    assert mensajes.errores == [] and pantalla.resultado.visible
    assert pantalla.titulo_resultado.value == REPORTES[clave].TITULO


def test_el_reporte_de_vacunas_usa_el_hasta_como_fecha_de_corte(pantalla, mensajes):
    elegir_reporte(pantalla, "vacunas")
    pantalla.hasta.value = "2026-11-02"
    pantalla.generar()

    assert mensajes.errores == []
    assert "Fecha de corte: 02/11/2026. 9 mascota(s) con 21 vacuna(s) pendiente(s)." in pantalla.notas.controls[0].value
    assert len(pantalla.tabla.textos()) == 21
    assert pantalla.lugar_grafico.content.src.startswith(b"\x89PNG") and pantalla.detalle is None


@pytest.fixture
def una_muestra_rechazada():
    m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-10-05 08:00"),
                      ("RECHAZADA", "2026-10-06 09:00", ("PRECINTO_ROTO",)))
    datos.remito("R1", "Clínica Centro", m, ("Transportes Sur",), "RECHAZADO", ("2026-10-06 09:00", "ROTO", 5.0, False))


def test_el_reporte_de_rechazos_muestra_la_tabla_y_el_detalle_de_lo_rechazado(pantalla, una_muestra_rechazada, mensajes):
    elegir_reporte(pantalla, "rechazos")
    pantalla.generar()

    assert mensajes.errores == []
    assert ["Total", "Todas las muestras", "1", "1", "100,0 %"] in pantalla.tabla.textos()
    assert pantalla.detalle is not None and pantalla.lugar_detalle.content is not None
    assert pantalla.detalle.textos()[0][5:] == ["R1", "Transportes Sur", "Precinto roto", "Roto", "5 °C"]


def test_cambiar_a_un_reporte_sin_detalle_oculta_la_segunda_tabla(pantalla, una_muestra_rechazada):
    elegir_reporte(pantalla, "rechazos")
    pantalla.generar()
    assert pantalla.detalle is not None

    elegir_reporte(pantalla, "tiempos")
    pantalla.generar()
    assert pantalla.detalle is None and pantalla.lugar_detalle.content is None


def test_el_reporte_de_tiempos_muestra_el_grafico_de_mediana_y_p90(pantalla):
    m = datos.muestra(datos.nueva_orden(), ("EN_TRANSITO", "2026-10-05 08:00"), ("RECIBIDA", "2026-10-05 14:00"))
    datos.remito("R1", "Clínica Centro", m, ("Transportes Sur",))
    elegir_reporte(pantalla, "tiempos")
    pantalla.generar()
    assert ["Clínica", "Clínica Centro", "1", "6,0 h / 6,0 h", "0 de 1 (0,0 %)", "—", "0"] in pantalla.tabla.textos()
    assert pantalla.lugar_grafico.content.src.startswith(b"\x89PNG")

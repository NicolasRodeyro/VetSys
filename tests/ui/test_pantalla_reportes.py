from datetime import datetime

import pytest

from app.reportes import REPORTES
from app.ui.pantallas.reportes import TODAS, PantallaReportes
from tests.reportes.test_facturacion import cerrar_consulta_el
from tests.ui.conftest import elegir, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaReportes:
    pantalla = PantallaReportes(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


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
    pantalla.generar()

    assert mensajes.errores == []
    assert pantalla.resultado.visible
    assert pantalla.titulo_resultado.value == "Facturación por clínica y servicio"
    assert ["10/2026", "Clínica Centro", "Hemograma", "Laboratorio", "1", "$ 12.500,00", "$ 0,00", "—"] \
        in pantalla.tabla.textos()
    assert pantalla.notas.controls
    assert pantalla.lugar_grafico.content.src.startswith(b"\x89PNG")


def test_filtrar_por_otra_clinica_deja_la_tabla_sin_ventas(pantalla, un_comprobante):
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

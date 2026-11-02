from decimal import Decimal

import pytest

from app.servicios import consultas as svc
from app.ui.entradas import en_pesos
from app.ui.pantallas.comprobantes import PantallaComprobantes
from tests.servicios.conftest import mascota, veterinario
from tests.ui.conftest import elegir_consulta, elegir_mascota, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaComprobantes:
    pantalla = PantallaComprobantes(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


@pytest.fixture
def consulta_con_ordenes():
    consulta = svc.registrar_consulta(mascota("30111222", "Toby").id, veterinario("MP-1001").id, "CONSULTA")
    svc.emitir_orden(consulta.id, "Hemograma")
    svc.emitir_orden(consulta.id, "Urocultivo")
    return consulta


def abrir(p):
    elegir_mascota(p.selector, "Toby", "paz")
    elegir_consulta(p.selector)


def test_los_importes_se_muestran_en_pesos_argentinos():
    assert en_pesos(Decimal("12500")) == "$ 12.500,00"
    assert en_pesos(Decimal("25300.75")) == "$ 25.300,75"
    assert en_pesos(Decimal("0.5")) == "$ 0,50"


def test_una_consulta_abierta_muestra_lo_que_se_va_a_cobrar(pantalla, consulta_con_ordenes):
    abrir(pantalla)
    assert pantalla.pendiente.visible and not pantalla.comprobante.visible
    assert [t.value for t in pantalla.resumen.controls] == [
        "• Hemograma: $ 12.500,00", "• Urocultivo: $ 9.800,50"]


def test_cerrar_sin_honorarios_o_con_importe_invalido_se_explica(pantalla, consulta_con_ordenes, mensajes):
    abrir(pantalla)
    pantalla.cerrar()
    assert "importe" in mensajes.errores[-1]
    pantalla.honorarios.value = "-5"
    pantalla.cerrar()
    assert "negativo" in mensajes.errores[-1]
    assert not svc.obtener_consulta(consulta_con_ordenes.id).cerrada


def test_cerrar_la_consulta_emite_el_comprobante(pantalla, consulta_con_ordenes, mensajes):
    abrir(pantalla)
    pantalla.honorarios.value = "3000,25"
    pantalla.cerrar()

    assert mensajes.errores == [] and mensajes.exitos == ["Consulta cerrada: comprobante emitido."]
    assert pantalla.comprobante.visible and not pantalla.pendiente.visible
    assert pantalla.tabla_items.cantidad == 3  # la consulta y las dos órdenes
    assert "Total $ 25.300,75" in pantalla.total.value and "Paz, Ana" in pantalla.total.value
    assert svc.obtener_consulta(consulta_con_ordenes.id).comprobante.total == Decimal("25300.75")


def test_una_consulta_ya_cerrada_muestra_su_comprobante(pantalla, consulta_con_ordenes):
    svc.cerrar_consulta(consulta_con_ordenes.id, "1000")
    abrir(pantalla)
    assert pantalla.comprobante.visible and not pantalla.pendiente.visible


def test_una_consulta_sin_ordenes_solo_cobra_la_consulta(pantalla):
    svc.registrar_consulta(mascota("30111222", "Toby").id, veterinario("MP-1001").id, "CONTROL")
    abrir(pantalla)
    assert "solo se cobra la consulta" in pantalla.resumen.controls[0].value
    pantalla.honorarios.value = "2500"
    pantalla.cerrar()
    assert pantalla.tabla_items.cantidad == 1


def test_sin_consulta_elegida_no_hay_nada_que_cerrar(pantalla, mensajes):
    pantalla.cerrar()
    assert "Elegí la consulta" in mensajes.errores[-1]
    assert not pantalla.pendiente.visible and not pantalla.comprobante.visible


def test_los_botones_no_reciben_el_evento(pantalla):
    assert sin_parametros(pantalla.cerrar) and sin_parametros(pantalla.mostrar)

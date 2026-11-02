from datetime import datetime
from decimal import Decimal

import pytest

from app.dominio.comprobante import Comprobante, ItemComprobante
from app.dominio.consulta import Consulta
from app.dominio.enums import MotivoRechazo, TipoConsulta
from app.dominio.excepciones import ReglaNegocio
from app.dominio.muestra import Muestra
from app.dominio.tipo_analisis import TipoAnalisis

FECHA = datetime(2026, 5, 10, 11, 0)
CIERRE = datetime(2026, 5, 10, 11, 45)
HONORARIOS = Decimal("3000.50")


@pytest.fixture
def consulta(perro, veterinario) -> Consulta:
    return Consulta(TipoConsulta.CONSULTA, FECHA, perro, veterinario)


@pytest.fixture
def urocultivo() -> TipoAnalisis:
    return TipoAnalisis("Urocultivo", Decimal("8750.25"), "Orina", 2.0, 8.0, 24)


# --- Comprobante sin y con derivación ---

def test_comprobante_sin_derivacion_solo_tiene_la_consulta(consulta):
    comprobante = consulta.cerrar(HONORARIOS, CIERRE)

    assert comprobante.items == (ItemComprobante("Consulta", HONORARIOS),)
    assert comprobante.total == HONORARIOS
    assert not comprobante.items[0].es_laboratorio


def test_comprobante_con_derivacion_suma_la_consulta_y_cada_orden(consulta, hemograma, urocultivo):
    consulta.emitir_orden(hemograma)
    consulta.emitir_orden(urocultivo)

    comprobante = consulta.cerrar(HONORARIOS, CIERRE)

    assert [(i.descripcion, i.monto, i.es_laboratorio) for i in comprobante.items] == [
        ("Consulta", Decimal("3000.50"), False),
        ("Hemograma", Decimal("12500"), True),
        ("Urocultivo", Decimal("8750.25"), True),
    ]
    assert comprobante.total == Decimal("24250.75")


def test_el_total_es_decimal_exacto_y_no_float(consulta, hemograma):
    consulta.emitir_orden(TipoAnalisis("A", Decimal("0.10"), "Sangre", 2.0, 8.0, 24))
    consulta.emitir_orden(TipoAnalisis("B", Decimal("0.20"), "Sangre", 2.0, 8.0, 24))
    comprobante = consulta.cerrar(Decimal("0"), CIERRE)

    assert isinstance(comprobante.total, Decimal)
    assert comprobante.total == Decimal("0.30")  # con float daría 0.30000000000000004


def test_el_item_de_la_consulta_lleva_el_nombre_del_tipo(perro, veterinario):
    urgencia = Consulta(TipoConsulta.URGENCIA, FECHA, perro, veterinario)
    assert urgencia.cerrar(HONORARIOS, CIERRE).items[0].descripcion == "Urgencia"


def test_comprobante_conoce_su_consulta_y_al_cliente_que_paga(consulta, cliente):
    comprobante = consulta.cerrar(HONORARIOS, CIERRE)
    assert comprobante.consulta is consulta
    assert comprobante.cliente is cliente
    assert comprobante.fecha_hora == CIERRE


# --- Un solo comprobante por consulta ---

def test_cerrar_deja_la_consulta_cerrada_con_su_comprobante(consulta):
    assert not consulta.cerrada and consulta.comprobante is None
    comprobante = consulta.cerrar(HONORARIOS, CIERRE)
    assert consulta.cerrada
    assert consulta.comprobante is comprobante


def test_no_se_puede_cerrar_dos_veces(consulta):
    primero = consulta.cerrar(HONORARIOS, CIERRE)
    with pytest.raises(ReglaNegocio, match="ya está cerrada"):
        consulta.cerrar(HONORARIOS, CIERRE)
    assert consulta.comprobante is primero


def test_una_consulta_cerrada_no_admite_nuevas_ordenes(consulta, hemograma):
    consulta.cerrar(HONORARIOS, CIERRE)
    with pytest.raises(ReglaNegocio, match="no admite nuevas órdenes"):
        consulta.emitir_orden(hemograma)
    assert consulta.ordenes == ()


def test_honorarios_negativos_fallan_y_la_consulta_sigue_abierta(consulta):
    with pytest.raises(ReglaNegocio, match="negativos"):
        consulta.cerrar(Decimal("-1"), CIERRE)
    assert not consulta.cerrada


def test_comprobante_sin_items_falla(consulta):
    with pytest.raises(ReglaNegocio):
        Comprobante(consulta, CIERRE, [])


def test_items_del_comprobante_no_se_modifican_desde_afuera(consulta):
    comprobante = consulta.cerrar(HONORARIOS, CIERRE)
    with pytest.raises(AttributeError):
        comprobante.items.append("x")  # es una tupla


# --- Re-extracción sin cargo ---

def rechazar(muestra: Muestra) -> None:
    muestra.empaquetar("x")
    muestra.despachar("x")
    muestra.recibir(False, "x", [MotivoRechazo.PRECINTO_ROTO])


def test_re_extraccion_despues_de_cerrar_no_cambia_el_comprobante(consulta, hemograma, reloj):
    orden = consulta.emitir_orden(hemograma)
    primera = Muestra(orden, "Dr. Gómez", reloj=reloj)
    comprobante = consulta.cerrar(HONORARIOS, CIERRE)
    total_antes, items_antes = comprobante.total, comprobante.items

    rechazar(primera)
    Muestra(orden, "Dr. Gómez", observacion="Re-extracción", reloj=reloj)  # nueva muestra, misma orden

    assert len(orden.muestras) == 2
    assert comprobante.total == total_antes
    assert comprobante.items == items_antes
    assert consulta.comprobante is comprobante


def test_se_cobra_una_vez_por_orden_aunque_tenga_varias_muestras(consulta, hemograma, reloj):
    orden = consulta.emitir_orden(hemograma)
    rechazar(Muestra(orden, "Dr. Gómez", reloj=reloj))
    Muestra(orden, "Dr. Gómez", reloj=reloj)  # re-extracción antes de cerrar

    comprobante = consulta.cerrar(HONORARIOS, CIERRE)

    assert [i.descripcion for i in comprobante.items] == ["Consulta", "Hemograma"]
    assert comprobante.total == HONORARIOS + hemograma.precio

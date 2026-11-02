from datetime import datetime

import pytest

from app.dominio.enums import EstadoPrecinto, MotivoRechazo
from app.dominio.excepciones import ReglaNegocio
from app.dominio.laboratorio import Laboratorio
from app.dominio.recepcion import DetalleRecepcion, Recepcion

LLEGADA = datetime(2026, 6, 1, 12, 0)


@pytest.fixture
def conservadora(crear_conservadora):
    return crear_conservadora(temp_min=4.0, temp_max=6.0)  # rango 4 a 6 °C


# --- DetalleRecepcion: precinto y temperatura ---

def test_precinto_intacto_y_temperatura_en_rango_se_acepta(conservadora):
    detalle = DetalleRecepcion(conservadora, EstadoPrecinto.INTACTO, 5.0)
    assert detalle.aceptada
    assert detalle.motivos == ()


def test_precinto_roto_se_rechaza(conservadora):
    detalle = DetalleRecepcion(conservadora, EstadoPrecinto.ROTO, 5.0)
    assert not detalle.aceptada
    assert detalle.motivos == (MotivoRechazo.PRECINTO_ROTO,)


@pytest.mark.parametrize("temperatura", [3.9, 6.1, 20.0, -5.0])
def test_temperatura_fuera_de_rango_se_rechaza(conservadora, temperatura):
    detalle = DetalleRecepcion(conservadora, EstadoPrecinto.INTACTO, temperatura)
    assert not detalle.aceptada
    assert detalle.motivos == (MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO,)


@pytest.mark.parametrize("temperatura", [4.0, 6.0])
def test_temperatura_justo_en_el_borde_se_acepta(conservadora, temperatura):
    assert DetalleRecepcion(conservadora, EstadoPrecinto.INTACTO, temperatura).aceptada


def test_pueden_darse_los_dos_motivos_a_la_vez(conservadora):
    detalle = DetalleRecepcion(conservadora, EstadoPrecinto.ROTO, 15.0)
    assert not detalle.aceptada
    assert detalle.motivos == (
        MotivoRechazo.PRECINTO_ROTO, MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO
    )


# --- Recepcion ---

def recepcion_con(*detalles) -> Recepcion:
    return Recepcion(Laboratorio("Laboratorio Central", "Bv. Illia 1"), "Bioq. Pérez", LLEGADA, detalles)


def test_recepcion_sin_detalles_falla():
    with pytest.raises(ReglaNegocio):
        recepcion_con()


def test_recepcion_con_todas_las_conservadoras_aceptadas(crear_conservadora):
    a, b = crear_conservadora("C-1"), crear_conservadora("C-2")
    recepcion = recepcion_con(
        DetalleRecepcion(a, EstadoPrecinto.INTACTO, 5.0),
        DetalleRecepcion(b, EstadoPrecinto.INTACTO, 5.0),
    )
    assert recepcion.todas_aceptadas
    assert not recepcion.ninguna_aceptada


def test_recepcion_con_algunas_rechazadas(crear_conservadora):
    a, b = crear_conservadora("C-1"), crear_conservadora("C-2")
    recepcion = recepcion_con(
        DetalleRecepcion(a, EstadoPrecinto.INTACTO, 5.0),
        DetalleRecepcion(b, EstadoPrecinto.ROTO, 5.0),
    )
    assert not recepcion.todas_aceptadas
    assert not recepcion.ninguna_aceptada


def test_recepcion_con_todas_rechazadas(crear_conservadora):
    a, b = crear_conservadora("C-1"), crear_conservadora("C-2")
    recepcion = recepcion_con(
        DetalleRecepcion(a, EstadoPrecinto.ROTO, 5.0),
        DetalleRecepcion(b, EstadoPrecinto.INTACTO, 30.0),
    )
    assert recepcion.ninguna_aceptada
    assert not recepcion.todas_aceptadas


def test_los_detalles_no_se_modifican_desde_afuera(conservadora):
    recepcion = recepcion_con(DetalleRecepcion(conservadora, EstadoPrecinto.INTACTO, 5.0))
    with pytest.raises(AttributeError):
        recepcion.detalles.append("x")  # es una tupla

"""Cada estado dice qué operaciones permite; la interfaz muestra solo esos botones."""

import pytest

from app.dominio.enums import MotivoRechazo
from app.dominio.estados_muestra import (
    Analizada, Empaquetada, EnTransito, Extraida, Rechazada, Recibida,
)
from app.dominio.estados_remito import (
    OPERACIONES as OPERACIONES_REMITO,
    Abierto, Cerrado, Recibido, RecibidoParcial, Rechazado,
)
from app.dominio.estados_remito import EnTransito as RemitoEnTransito
from app.dominio.excepciones import TransicionInvalida

PERMITIDAS_MUESTRA = {
    Extraida(): ("empaquetar",),
    Empaquetada(): ("despachar",),
    EnTransito(): ("recibir",),
    Recibida(): ("analizar",),
    Analizada(): (),
    Rechazada([MotivoRechazo.PRECINTO_ROTO]): (),
}

PERMITIDAS_REMITO = {
    Abierto(): ("agregar_conservadora", "quitar_conservadora", "cerrar"),
    Cerrado(): ("despachar",),
    RemitoEnTransito(): ("registrar_tramo", "registrar_recepcion"),
    Recibido(): (),
    RecibidoParcial(): (),
    Rechazado(): (),
}


@pytest.mark.parametrize("estado, esperadas", PERMITIDAS_MUESTRA.items(), ids=lambda e: getattr(e, "nombre", ""))
def test_operaciones_permitidas_de_cada_estado_de_la_muestra(estado, esperadas):
    assert estado.operaciones_permitidas == esperadas


@pytest.mark.parametrize("estado, esperadas", PERMITIDAS_REMITO.items(), ids=lambda e: getattr(e, "nombre", ""))
def test_operaciones_permitidas_de_cada_estado_del_remito(estado, esperadas):
    assert estado.operaciones_permitidas == esperadas


def test_los_estados_finales_no_permiten_ninguna_operacion():
    for estado in (*PERMITIDAS_MUESTRA, *PERMITIDAS_REMITO):
        assert (estado.operaciones_permitidas == ()) == estado.es_final


def test_lo_que_no_esta_permitido_lo_rechaza_el_estado():
    """La lista sale de lo que cada estado sobrescribe; esto confirma que lo que no está en la
    lista realmente se rechaza con TransicionInvalida (la lista y el comportamiento coinciden)."""
    llamadas = {
        "agregar_conservadora": lambda e: e.agregar_conservadora(None, None),
        "quitar_conservadora": lambda e: e.quitar_conservadora(None, None),
        "cerrar": lambda e: e.cerrar(None),
        "despachar": lambda e: e.despachar(None, "x", "", ""),
        "registrar_tramo": lambda e: e.registrar_tramo(None, None),
        "registrar_recepcion": lambda e: e.registrar_recepcion(None, None),
    }
    for estado in PERMITIDAS_REMITO:
        for operacion in OPERACIONES_REMITO:
            if operacion not in estado.operaciones_permitidas:
                with pytest.raises(TransicionInvalida):
                    llamadas[operacion](estado)

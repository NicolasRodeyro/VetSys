import pytest

from app.dominio.enums import MotivoRechazo
from app.dominio.estados_muestra import (
    Analizada, Empaquetada, EnTransito, Extraida, Rechazada, Recibida,
)
from app.dominio.estados_remito import (
    Abierto, Cerrado, Recibido, RecibidoParcial, Rechazado,
)
from app.dominio.estados_remito import EnTransito as RemitoEnTransito
from app.persistencia.mapeo_estados import estado_de_muestra, estado_de_remito

ESTADOS_MUESTRA = [Extraida, Empaquetada, EnTransito, Recibida, Analizada]
ESTADOS_REMITO = [Abierto, Cerrado, RemitoEnTransito, Recibido, RecibidoParcial, Rechazado]


@pytest.mark.parametrize("clase", ESTADOS_MUESTRA)
def test_cada_estado_de_muestra_se_reconstruye_desde_su_nombre(clase):
    assert type(estado_de_muestra(clase.nombre)) is clase


def test_la_rechazada_se_reconstruye_con_sus_motivos():
    estado = estado_de_muestra("RECHAZADA", [MotivoRechazo.PRECINTO_ROTO])
    assert type(estado) is Rechazada
    assert estado.motivos == (MotivoRechazo.PRECINTO_ROTO,)


@pytest.mark.parametrize("clase", ESTADOS_REMITO)
def test_cada_estado_de_remito_se_reconstruye_desde_su_nombre(clase):
    assert type(estado_de_remito(clase.nombre)) is clase


def test_los_nombres_de_muestra_son_los_mismos_que_acepta_la_base():
    # Los CHECK de 001_inicial.sql y las clases de estado tienen que decir lo mismo.
    esperados = {"EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA", "ANALIZADA", "RECHAZADA"}
    assert {c.nombre for c in ESTADOS_MUESTRA} | {Rechazada.nombre} == esperados


def test_los_nombres_de_remito_son_los_mismos_que_acepta_la_base():
    esperados = {"ABIERTO", "CERRADO", "EN_TRANSITO", "RECIBIDO", "RECIBIDO_PARCIAL", "RECHAZADO"}
    assert {c.nombre for c in ESTADOS_REMITO} == esperados


def test_un_estado_desconocido_da_un_error_claro():
    with pytest.raises(ValueError, match="PERDIDA"):
        estado_de_muestra("PERDIDA")
    with pytest.raises(ValueError, match="ANULADO"):
        estado_de_remito("ANULADO")

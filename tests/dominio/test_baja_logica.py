from datetime import date

import pytest

from app.dominio.enums import Sexo
from app.dominio.especie import Especie
from app.dominio.excepciones import ReglaNegocio
from app.dominio.mascota import Mascota


@pytest.fixture
def toby(cliente) -> Mascota:
    return Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)


# --- Cliente ---

def test_un_cliente_nuevo_esta_activo(cliente):
    assert cliente.activo


def test_cliente_sin_mascotas_se_puede_dar_de_baja_y_reactivar(cliente):
    cliente.dar_de_baja()
    assert not cliente.activo
    cliente.reactivar()
    assert cliente.activo


def test_no_se_da_de_baja_a_un_cliente_con_mascotas_activas(cliente, toby):
    with pytest.raises(ReglaNegocio, match="mascotas activas"):
        cliente.dar_de_baja()
    assert cliente.activo


def test_se_da_de_baja_al_cliente_cuando_sus_mascotas_ya_estan_de_baja(cliente, toby):
    toby.dar_de_baja()
    cliente.dar_de_baja()
    assert not cliente.activo
    assert cliente.mascotas == (toby,)  # la baja es lógica: nada se borra


def test_no_se_agregan_mascotas_a_un_cliente_dado_de_baja(cliente):
    cliente.dar_de_baja()
    with pytest.raises(ReglaNegocio, match="dado de baja"):
        Mascota("Rex", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)
    assert cliente.mascotas == ()


# --- Mascota ---

def test_una_mascota_nueva_esta_activa(toby):
    assert toby.activa


def test_la_baja_de_la_mascota_conserva_su_historia_clinica(toby):
    toby.historia_clinica.alergias = "Polen"
    toby.dar_de_baja()
    assert not toby.activa
    assert toby.historia_clinica.alergias == "Polen"


def test_se_reactiva_una_mascota_dada_de_baja(toby):
    toby.dar_de_baja()
    toby.reactivar()
    assert toby.activa


def test_no_se_reactiva_una_mascota_si_su_responsable_esta_de_baja(cliente, toby):
    toby.dar_de_baja()
    cliente.dar_de_baja()
    with pytest.raises(ReglaNegocio, match="responsable está dado de baja"):
        toby.reactivar()
    assert not toby.activa


# --- id ---

def test_las_entidades_no_tienen_id_hasta_que_se_guardan(cliente, toby, clinica, veterinario):
    for entidad in (cliente, toby, clinica, veterinario):
        assert entidad.id is None

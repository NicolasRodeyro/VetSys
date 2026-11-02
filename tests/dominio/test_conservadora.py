from datetime import datetime
from decimal import Decimal

import pytest

from app.dominio.conservadora import Conservadora
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.tipo_analisis import TipoAnalisis

AHORA = datetime(2026, 6, 1, 10, 0)


# --- Datos de la conservadora ---

def test_capacidad_cero_o_negativa_falla():
    with pytest.raises(ReglaNegocio):
        Conservadora("C-1", 0, 2.0, 8.0)


def test_rango_de_temperatura_invertido_falla():
    with pytest.raises(ReglaNegocio):
        Conservadora("C-1", 5, 8.0, 2.0)


def test_admite_temperatura_dentro_de_su_rango_incluyendo_los_bordes(crear_conservadora):
    conservadora = crear_conservadora(temp_min=4.0, temp_max=6.0)
    assert conservadora.admite_temperatura(4.0)
    assert conservadora.admite_temperatura(6.0)
    assert not conservadora.admite_temperatura(3.9)
    assert not conservadora.admite_temperatura(6.1)


# --- Empaquetado ---

def test_agregar_muestra_la_empaqueta(crear_conservadora, crear_muestra):
    conservadora, muestra = crear_conservadora(), crear_muestra()
    conservadora.agregar_muestra(muestra, "Enf. Ruiz", "Clínica Centro")

    assert muestra.estado.nombre == "EMPAQUETADA"
    assert conservadora.muestras == (muestra,)


def test_el_empaquetado_queda_en_la_trazabilidad_de_la_muestra(crear_conservadora, crear_muestra):
    conservadora, muestra = crear_conservadora("C-7"), crear_muestra()
    muestra.suscribir(RegistroTrazabilidad())

    conservadora.agregar_muestra(muestra, "Enf. Ruiz", "Clínica Centro")

    empaquetado = muestra.historial[-1]
    assert empaquetado.nuevo == "EMPAQUETADA"
    assert empaquetado.responsable == "Enf. Ruiz"
    assert "C-7" in empaquetado.observacion


def test_conservadora_lleva_muestras_de_distintas_ordenes(crear_conservadora, crear_muestra):
    conservadora = crear_conservadora()
    primera, segunda = crear_muestra(), crear_muestra()
    conservadora.agregar_muestra(primera, "Enf. Ruiz")
    conservadora.agregar_muestra(segunda, "Enf. Ruiz")
    assert primera.orden is not segunda.orden
    assert len(conservadora.muestras) == 2


def test_rechaza_muestra_si_la_temperatura_no_es_compatible(crear_conservadora, crear_muestra):
    # El hemograma pide 2 a 8 °C; esta conservadora llega hasta 12 °C.
    conservadora = crear_conservadora(temp_min=4.0, temp_max=12.0)
    muestra = crear_muestra()

    with pytest.raises(ReglaNegocio, match="no es compatible"):
        conservadora.agregar_muestra(muestra, "Enf. Ruiz")

    assert muestra.estado.nombre == "EXTRAIDA"  # no se tocó la muestra
    assert conservadora.muestras == ()


def test_acepta_muestra_si_el_rango_de_la_conservadora_cabe_justo_en_el_del_analisis(
    crear_conservadora, crear_muestra
):
    conservadora = crear_conservadora(temp_min=2.0, temp_max=8.0)
    conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz")
    assert len(conservadora.muestras) == 1


def test_cada_muestra_se_valida_contra_su_propio_analisis(crear_conservadora, crear_muestra):
    congelado = TipoAnalisis("Cultivo", Decimal("9000"), "Tejido", -25.0, -15.0, 48)
    conservadora = crear_conservadora(temp_min=4.0, temp_max=6.0)
    with pytest.raises(ReglaNegocio, match="Cultivo"):
        conservadora.agregar_muestra(crear_muestra(congelado), "Enf. Ruiz")


def test_rechaza_muestra_si_no_hay_capacidad(crear_conservadora, crear_muestra):
    conservadora = crear_conservadora(capacidad=2)
    conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz")
    conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz")

    sobrante = crear_muestra()
    with pytest.raises(ReglaNegocio, match="llena"):
        conservadora.agregar_muestra(sobrante, "Enf. Ruiz")
    assert sobrante.estado.nombre == "EXTRAIDA"


def test_rechaza_muestra_que_ya_no_esta_extraida(crear_conservadora, crear_muestra):
    # Lo valida el State de la muestra: empaquetar() solo se permite en Extraída.
    una, otra = crear_conservadora("C-1"), crear_conservadora("C-2")
    muestra = crear_muestra()
    una.agregar_muestra(muestra, "Enf. Ruiz")

    with pytest.raises(TransicionInvalida):
        otra.agregar_muestra(muestra, "Enf. Ruiz")
    assert otra.muestras == ()


def test_lista_de_muestras_no_se_modifica_desde_afuera(crear_conservadora):
    with pytest.raises(AttributeError):
        crear_conservadora().muestras.append("x")  # es una tupla


# --- Precinto ---

def test_precintar_coloca_el_precinto(crear_conservadora, crear_muestra):
    conservadora = crear_conservadora()
    assert conservadora.precinto is None
    conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz")

    precinto = conservadora.precintar("P-0001", "Enf. Ruiz", AHORA)

    assert conservadora.precinto is precinto
    assert precinto.numero == "P-0001"
    assert precinto.fecha_colocacion == AHORA


def test_no_se_puede_precintar_una_conservadora_vacia(crear_conservadora):
    with pytest.raises(ReglaNegocio, match="vacía"):
        crear_conservadora().precintar("P-0001", "Enf. Ruiz", AHORA)


def test_no_se_puede_precintar_dos_veces(crear_conservadora, crear_muestra):
    conservadora = crear_conservadora()
    conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz")
    conservadora.precintar("P-0001", "Enf. Ruiz", AHORA)
    with pytest.raises(ReglaNegocio, match="ya tiene precinto"):
        conservadora.precintar("P-0002", "Enf. Ruiz", AHORA)


def test_conservadora_precintada_no_acepta_mas_muestras(crear_conservadora, crear_muestra):
    conservadora = crear_conservadora()
    conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz")
    conservadora.precintar("P-0001", "Enf. Ruiz", AHORA)

    tardia = crear_muestra()
    with pytest.raises(ReglaNegocio, match="precintada"):
        conservadora.agregar_muestra(tardia, "Enf. Ruiz")
    assert tardia.estado.nombre == "EXTRAIDA"

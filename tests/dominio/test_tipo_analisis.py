from decimal import Decimal

import pytest

from app.dominio.excepciones import ReglaNegocio
from app.dominio.tipo_analisis import TipoAnalisis


def hemograma(**cambios) -> TipoAnalisis:
    datos = dict(
        nombre="Hemograma",
        precio=Decimal("12500.50"),
        tipo_muestra="Sangre",
        temp_min=2.0,
        temp_max=8.0,
        horas_max_transito=24,
    )
    datos.update(cambios)
    return TipoAnalisis(**datos)


def test_tipo_analisis_guarda_el_precio_como_decimal():
    assert hemograma().precio == Decimal("12500.50")


def test_rango_de_temperatura_invertido_falla():
    with pytest.raises(ReglaNegocio):
        hemograma(temp_min=10.0, temp_max=2.0)


def test_admite_temperatura_dentro_del_rango_incluyendo_los_bordes():
    analisis = hemograma()
    assert analisis.admite_temperatura(2.0)
    assert analisis.admite_temperatura(5.0)
    assert analisis.admite_temperatura(8.0)


def test_no_admite_temperatura_fuera_del_rango():
    analisis = hemograma()
    assert not analisis.admite_temperatura(1.9)
    assert not analisis.admite_temperatura(8.1)


def test_admite_rango_si_el_contenedor_queda_dentro_del_que_pide_el_analisis():
    analisis = hemograma()  # pide 2 a 8 °C
    assert analisis.admite_rango(4.0, 6.0)
    assert analisis.admite_rango(2.0, 8.0)  # justo en los bordes
    assert not analisis.admite_rango(1.0, 6.0)  # se pasa por abajo
    assert not analisis.admite_rango(4.0, 9.0)  # se pasa por arriba

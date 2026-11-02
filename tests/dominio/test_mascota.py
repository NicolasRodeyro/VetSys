from datetime import date

import pytest

from app.dominio.cliente import Cliente
from app.dominio.enums import Sexo
from app.dominio.especie import Especie
from app.dominio.excepciones import ReglaNegocio
from app.dominio.mascota import Mascota


def crear_cliente() -> Cliente:
    return Cliente("30111222", "Ana", "Paz", "351-555-0000", "ana@mail.com", "Calle 1")


def test_mascota_sin_responsable_falla():
    with pytest.raises(ReglaNegocio):
        Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), None)


def test_mascota_con_responsable_queda_en_la_lista_del_cliente():
    cliente = crear_cliente()
    mascota = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)

    assert mascota.responsable is cliente
    assert cliente.mascotas == (mascota,)


def test_no_se_puede_agregar_a_un_cliente_una_mascota_de_otro():
    duenio = crear_cliente()
    otro = crear_cliente()
    mascota = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), duenio)

    with pytest.raises(ReglaNegocio):
        otro.agregar_mascota(mascota)


def test_edad_en_meses_cuenta_meses_completos():
    mascota = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 15), crear_cliente())

    assert mascota.edad_en_meses(date(2026, 2, 14)) == 0
    assert mascota.edad_en_meses(date(2026, 2, 15)) == 1
    assert mascota.edad_en_meses(date(2027, 1, 15)) == 12


def test_edad_en_fecha_anterior_al_nacimiento_falla():
    mascota = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 15), crear_cliente())

    with pytest.raises(ReglaNegocio):
        mascota.edad_en_meses(date(2025, 12, 31))


def test_mascota_nace_con_su_historia_clinica():
    mascota = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 15), crear_cliente())

    assert mascota.historia_clinica.mascota is mascota
    assert mascota.historia_clinica.vacunas_aplicadas == ()

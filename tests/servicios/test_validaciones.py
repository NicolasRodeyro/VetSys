from datetime import date, datetime
from decimal import Decimal

import pytest

from app.dominio.enums import EstadoPrecinto, Sexo
from app.dominio.excepciones import ReglaNegocio
from app.servicios import validaciones as v
from app.servicios.excepciones import EntradaInvalida


# --- Textos ---

def test_texto_obligatorio_limpia_espacios():
    assert v.texto_obligatorio("  Ana   María  ", "El nombre") == "Ana María"


@pytest.mark.parametrize("vacio", ["", "   ", None, "\t\n"])
def test_texto_obligatorio_rechaza_vacios(vacio):
    with pytest.raises(EntradaInvalida, match="El nombre es obligatorio"):
        v.texto_obligatorio(vacio, "El nombre")


def test_texto_demasiado_largo_se_rechaza():
    with pytest.raises(EntradaInvalida, match="no puede superar los 10"):
        v.texto_obligatorio("x" * 11, "El nombre", maximo=10)
    with pytest.raises(EntradaInvalida):
        v.texto_opcional("x" * 11, "La dirección", maximo=10)


def test_texto_opcional_acepta_vacio():
    assert v.texto_opcional(None, "La dirección") == ""
    assert v.texto_opcional("  Calle   1 ", "La dirección") == "Calle 1"


def test_un_dato_sospechoso_se_trata_como_texto_comun():
    # No se "ejecuta" ni se rechaza por parecer SQL: es solo texto (el SQL va parametrizado).
    assert v.texto_obligatorio("Robert'); DROP TABLE clientes;--", "El nombre") == \
        "Robert'); DROP TABLE clientes;--"


# --- DNI, email, teléfono ---

@pytest.mark.parametrize("entrada", ["30111222", "30.111.222", "30 111 222", " 30-111-222 ", 30111222])
def test_dni_se_normaliza_a_solo_digitos(entrada):
    assert v.dni(entrada) == "30111222"


@pytest.mark.parametrize("malo", ["", "123456", "123456789", "30A11222", None, "abcdefgh"])
def test_dni_invalido(malo):
    with pytest.raises(EntradaInvalida, match="DNI"):
        v.dni(malo)


def test_email():
    assert v.email_opcional("  Ana.Paz@Mail.COM ") == "ana.paz@mail.com"
    assert v.email_opcional("") == "" and v.email_opcional(None) == ""
    for malo in ("sin-arroba", "a@b", "a b@c.com", "@x.com"):
        with pytest.raises(EntradaInvalida, match="email"):
            v.email_opcional(malo)


def test_telefono():
    assert v.telefono_opcional("351 555-0101") == "351 555-0101"
    assert v.telefono_opcional("+54 (351) 555-0101") == "+54 (351) 555-0101"
    assert v.telefono_opcional(None) == ""
    for malo in ("abc", "12345", "351-555-0101 ext 4", "1" * 16):
        with pytest.raises(EntradaInvalida, match="teléfono"):
            v.telefono_opcional(malo)


# --- Fechas ---

def test_fecha_no_futura():
    hoy = date(2026, 11, 2)
    assert v.fecha_no_futura(date(2026, 11, 2), "La fecha", hoy) == hoy
    assert v.fecha_no_futura(datetime(2026, 1, 5, 10, 0), "La fecha", hoy) == date(2026, 1, 5)
    with pytest.raises(EntradaInvalida, match="no puede ser futura"):
        v.fecha_no_futura(date(2026, 11, 3), "La fecha", hoy)
    with pytest.raises(EntradaInvalida, match="no es una fecha"):
        v.fecha("2026-01-05", "La fecha")  # un texto no es una fecha


def test_fecha_hora_exige_datetime():
    assert v.fecha_hora(datetime(2026, 6, 1, 10, 0), "El inicio") == datetime(2026, 6, 1, 10, 0)
    with pytest.raises(EntradaInvalida):
        v.fecha_hora(date(2026, 6, 1), "El inicio")


# --- Números ---

@pytest.mark.parametrize("entrada, esperado", [("5,5", 5.5), ("5.5", 5.5), (" -20 ", -20.0), (7, 7.0), (2.5, 2.5)])
def test_numero_acepta_coma_o_punto(entrada, esperado):
    assert v.numero(entrada, "La temperatura") == esperado


@pytest.mark.parametrize("malo", ["abc", "", None, "5,5,5", True])
def test_numero_invalido(malo):
    with pytest.raises(EntradaInvalida, match="La temperatura"):
        v.numero(malo, "La temperatura")


def test_entero_positivo():
    assert v.entero_positivo("30", "La duración") == 30
    for malo in ("0", "-5", "2.5", "abc", None, True):
        with pytest.raises(EntradaInvalida, match="La duración"):
            v.entero_positivo(malo, "La duración")


def test_monto_devuelve_decimal_exacto():
    assert v.monto("3000,50", "Los honorarios") == Decimal("3000.50")
    assert v.monto(3000, "Los honorarios") == Decimal("3000")
    assert isinstance(v.monto("1.5", "Los honorarios"), Decimal)
    for malo, mensaje in (("-1", "negativo"), ("abc", "importe"), ("1.234", "2 decimales"), ("NaN", "negativo")):
        with pytest.raises(EntradaInvalida, match=mensaje):
            v.monto(malo, "Los honorarios")


# --- Opciones (enums) ---

def test_opcion_acepta_el_enum_su_nombre_o_su_valor_en_cualquier_mayuscula():
    assert v.opcion(Sexo.MACHO, Sexo, "El sexo") is Sexo.MACHO
    assert v.opcion("hembra", Sexo, "El sexo") is Sexo.HEMBRA
    assert v.opcion(" Intacto ", EstadoPrecinto, "El precinto") is EstadoPrecinto.INTACTO


def test_opcion_invalida_dice_cuales_son_las_validas():
    with pytest.raises(EntradaInvalida, match="MACHO, HEMBRA"):
        v.opcion("otro", Sexo, "El sexo")


def test_todos_los_errores_de_entrada_se_atrapan_como_regla_de_negocio():
    with pytest.raises(ReglaNegocio):  # así la interfaz usa un solo except
        v.dni("mal")

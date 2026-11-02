from datetime import datetime

import pytest

from app.dominio.enums import MotivoRechazo
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.dominio.observadores_muestra import NotificadorCliente, RegistroTrazabilidad
from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado

HORA = datetime(2026, 6, 2, 9, 0)

HEMATOCRITO = ValorResultado("Hematocrito", 41.0, "%", 37.0, 55.0)
LEUCOCITOS = ValorResultado("Leucocitos", 25.0, "mil/µl", 6.0, 17.0)  # alto


# --- ValorResultado ---

@pytest.mark.parametrize("valor", [37.0, 45.0, 55.0])  # incluye los bordes
def test_valor_dentro_del_rango_de_referencia(valor):
    assert not ValorResultado("Hematocrito", valor, "%", 37.0, 55.0).fuera_de_rango()


@pytest.mark.parametrize("valor", [36.9, 55.1, 0.0, 99.0])
def test_valor_fuera_del_rango_de_referencia(valor):
    assert ValorResultado("Hematocrito", valor, "%", 37.0, 55.0).fuera_de_rango()


def test_parametro_que_solo_tiene_maximo():
    assert not ValorResultado("Urea", 40.0, "mg/dl", ref_max=60.0).fuera_de_rango()
    assert ValorResultado("Urea", 80.0, "mg/dl", ref_max=60.0).fuera_de_rango()


def test_parametro_que_solo_tiene_minimo():
    assert not ValorResultado("Albúmina", 3.0, "g/dl", ref_min=2.5).fuera_de_rango()
    assert ValorResultado("Albúmina", 2.0, "g/dl", ref_min=2.5).fuera_de_rango()


def test_parametro_sin_referencias_nunca_esta_fuera_de_rango():
    assert not ValorResultado("Observación", 123.0, "u").fuera_de_rango()


def test_rango_de_referencia_invertido_falla():
    with pytest.raises(ReglaNegocio):
        ValorResultado("Hematocrito", 41.0, "%", ref_min=55.0, ref_max=37.0)


# --- Registrar el resultado pasa la muestra a Analizada ---

def recibida(crear_muestra):
    muestra = crear_muestra()
    muestra.empaquetar("Enf. Ruiz")
    muestra.despachar("Enf. Ruiz")
    muestra.recibir(True, "Bioq. Pérez")
    return muestra


def test_registrar_resultado_pasa_la_muestra_a_analizada(crear_muestra):
    muestra = recibida(crear_muestra)
    resultado = ResultadoAnalisis(muestra, "Bioq. Pérez", HORA, [HEMATOCRITO])

    assert muestra.estado.nombre == "ANALIZADA"
    assert resultado.muestra is muestra
    assert resultado.valores == (HEMATOCRITO,)


def test_el_resultado_queda_en_la_trazabilidad_y_avisa_al_cliente(crear_muestra, cliente):
    muestra = recibida(crear_muestra)
    muestra.suscribir(RegistroTrazabilidad())
    notificador = NotificadorCliente(cliente)
    muestra.suscribir(notificador)

    ResultadoAnalisis(muestra, "Bioq. Pérez", HORA, [HEMATOCRITO], ubicacion="Laboratorio")

    ultimo = muestra.historial[-1]
    assert (ultimo.anterior, ultimo.nuevo) == ("RECIBIDA", "ANALIZADA")
    assert ultimo.responsable == "Bioq. Pérez"
    assert ultimo.ubicacion == "Laboratorio"
    assert len(notificador.avisos) == 1


def preparar(muestra, estado):
    if estado == "EXTRAIDA":
        return
    muestra.empaquetar("x")
    if estado == "EMPAQUETADA":
        return
    muestra.despachar("x")
    if estado == "EN_TRANSITO":
        return
    if estado == "RECHAZADA":
        muestra.recibir(False, "x", [MotivoRechazo.PRECINTO_ROTO])
        return
    muestra.recibir(True, "x")
    muestra.analizar("x")  # ANALIZADA


@pytest.mark.parametrize(
    "estado", ["EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECHAZADA", "ANALIZADA"]
)
def test_resultado_sobre_una_muestra_no_recibida_falla(crear_muestra, estado):
    muestra = crear_muestra()
    preparar(muestra, estado)
    estado_antes = muestra.estado

    with pytest.raises(TransicionInvalida):
        ResultadoAnalisis(muestra, "Bioq. Pérez", HORA, [HEMATOCRITO])

    assert muestra.estado is estado_antes


def test_resultado_sin_valores_falla_y_no_toca_la_muestra(crear_muestra):
    muestra = recibida(crear_muestra)
    with pytest.raises(ReglaNegocio, match="al menos un valor"):
        ResultadoAnalisis(muestra, "Bioq. Pérez", HORA, [])
    assert muestra.estado.nombre == "RECIBIDA"


# --- Consulta del resultado ---

def test_valores_fuera_de_rango_devuelve_solo_los_anormales(crear_muestra):
    resultado = ResultadoAnalisis(
        recibida(crear_muestra), "Bioq. Pérez", HORA, [HEMATOCRITO, LEUCOCITOS]
    )
    assert resultado.valores_fuera_de_rango() == (LEUCOCITOS,)


def test_valores_no_se_modifican_desde_afuera(crear_muestra):
    resultado = ResultadoAnalisis(recibida(crear_muestra), "Bioq. Pérez", HORA, [HEMATOCRITO])
    with pytest.raises(AttributeError):
        resultado.valores.append("x")  # es una tupla

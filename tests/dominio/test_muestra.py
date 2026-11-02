from itertools import product

import pytest

from app.dominio.enums import MotivoRechazo
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.dominio.muestra import Muestra

# --- Ayudas para llevar una muestra a cada estado ---

def a_extraida(m): pass
def a_empaquetada(m): m.empaquetar("Enf. Ruiz", "Clínica Centro")
def a_en_transito(m): a_empaquetada(m); m.despachar("Enf. Ruiz", "Clínica Centro")
def a_recibida(m): a_en_transito(m); m.recibir(True, "Bioq. Pérez", ubicacion="Laboratorio")
def a_analizada(m): a_recibida(m); m.analizar("Bioq. Pérez", "Laboratorio")
def a_rechazada(m):
    a_en_transito(m)
    m.recibir(False, "Bioq. Pérez", [MotivoRechazo.PRECINTO_ROTO], "Laboratorio")

LLEGADA = {
    "EXTRAIDA": a_extraida, "EMPAQUETADA": a_empaquetada, "EN_TRANSITO": a_en_transito,
    "RECIBIDA": a_recibida, "ANALIZADA": a_analizada, "RECHAZADA": a_rechazada,
}

OPERACIONES = {
    "empaquetar": lambda m: m.empaquetar("x"),
    "despachar": lambda m: m.despachar("x"),
    "recibir": lambda m: m.recibir(True, "x"),
    "analizar": lambda m: m.analizar("x"),
}

# Única operación que permite cada estado (según el ciclo de vida de CLAUDE.md §4.2).
PERMITIDA = {
    "EXTRAIDA": "empaquetar", "EMPAQUETADA": "despachar",
    "EN_TRANSITO": "recibir", "RECIBIDA": "analizar",
    "ANALIZADA": None, "RECHAZADA": None,
}


@pytest.fixture
def muestra(orden, reloj) -> Muestra:
    return Muestra(orden, "Dr. Gómez", "Clínica Centro", reloj=reloj)


# --- Recorrido y transiciones válidas ---

def test_muestra_nueva_esta_extraida_y_activa(muestra):
    assert muestra.estado.nombre == "EXTRAIDA"
    assert muestra.esta_activa()
    assert not muestra.estado.es_final


def test_recorrido_completo_feliz(muestra):
    muestra.empaquetar("Enf. Ruiz")
    assert muestra.estado.nombre == "EMPAQUETADA"
    muestra.despachar("Enf. Ruiz")
    assert muestra.estado.nombre == "EN_TRANSITO"
    muestra.recibir(True, "Bioq. Pérez")
    assert muestra.estado.nombre == "RECIBIDA"
    muestra.analizar("Bioq. Pérez")
    assert muestra.estado.nombre == "ANALIZADA"
    assert muestra.estado.es_final
    assert muestra.esta_activa()


def test_rechazo_desde_en_transito(muestra):
    a_en_transito(muestra)
    muestra.recibir(
        False, "Bioq. Pérez",
        [MotivoRechazo.PRECINTO_ROTO, MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO],
    )
    assert muestra.estado.nombre == "RECHAZADA"
    assert muestra.estado.es_final
    assert not muestra.esta_activa()
    assert muestra.estado.motivos == (
        MotivoRechazo.PRECINTO_ROTO, MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO
    )


def test_rechazo_sin_motivos_falla_y_no_cambia_el_estado(muestra):
    a_en_transito(muestra)
    with pytest.raises(ReglaNegocio, match="al menos un motivo"):
        muestra.recibir(False, "Bioq. Pérez")
    assert muestra.estado.nombre == "EN_TRANSITO"


def test_aceptar_con_motivos_de_rechazo_falla_y_no_cambia_el_estado(muestra):
    a_en_transito(muestra)
    with pytest.raises(ReglaNegocio, match="aceptada"):
        muestra.recibir(True, "Bioq. Pérez", [MotivoRechazo.PRECINTO_ROTO])
    assert muestra.estado.nombre == "EN_TRANSITO"


# --- Transiciones inválidas: cada estado solo permite su operación ---

COMBINACIONES_INVALIDAS = [
    (estado, operacion)
    for estado, operacion in product(LLEGADA, OPERACIONES)
    if PERMITIDA[estado] != operacion
]


@pytest.mark.parametrize("estado, operacion", COMBINACIONES_INVALIDAS)
def test_transicion_invalida_lanza_error_y_no_cambia_nada(muestra, estado, operacion):
    LLEGADA[estado](muestra)
    estado_antes = muestra.estado

    with pytest.raises(TransicionInvalida):
        OPERACIONES[operacion](muestra)

    assert muestra.estado is estado_antes


def test_el_mensaje_de_error_dice_que_operacion_y_en_que_estado(muestra):
    with pytest.raises(TransicionInvalida, match="despachar.*EXTRAIDA"):
        muestra.despachar("x")


def test_no_se_puede_desempaquetar_ni_volver_atras(muestra):
    # No existe ninguna operación que lleve a Extraida: el único camino es hacia adelante.
    a_empaquetada(muestra)
    with pytest.raises(TransicionInvalida):
        muestra.empaquetar("x")
    assert muestra.estado.nombre == "EMPAQUETADA"


# --- Historial de la extracción ---

def test_la_extraccion_es_el_primer_renglon_del_historial(muestra):
    (extraccion,) = muestra.historial
    assert extraccion.anterior is None
    assert extraccion.nuevo == "EXTRAIDA"
    assert extraccion.responsable == "Dr. Gómez"
    assert extraccion.ubicacion == "Clínica Centro"


def test_historial_no_se_modifica_desde_afuera(muestra):
    with pytest.raises(AttributeError):
        muestra.historial.append("x")  # es una tupla


# --- Muestra y orden de derivación ---

def test_la_muestra_se_agrega_sola_a_su_orden(orden, reloj):
    muestra = Muestra(orden, "Dr. Gómez", reloj=reloj)
    assert orden.muestra_activa() is muestra
    assert muestra.orden is orden
    assert muestra.tipo_analisis is orden.tipo_analisis


def test_no_se_puede_extraer_otra_muestra_mientras_hay_una_activa(orden, reloj):
    Muestra(orden, "Dr. Gómez", reloj=reloj)
    with pytest.raises(ReglaNegocio, match="muestra activa"):
        Muestra(orden, "Dr. Gómez", reloj=reloj)
    assert len(orden.muestras) == 1


def test_re_extraccion_despues_de_un_rechazo(orden, reloj):
    primera = Muestra(orden, "Dr. Gómez", reloj=reloj)
    a_rechazada(primera)
    assert orden.muestra_activa() is None

    segunda = Muestra(orden, "Dr. Gómez", observacion="Re-extracción", reloj=reloj)

    assert orden.muestra_activa() is segunda
    assert orden.muestras == (primera, segunda)


def test_muestra_analizada_sigue_contando_como_activa(orden, reloj):
    primera = Muestra(orden, "Dr. Gómez", reloj=reloj)
    a_analizada(primera)
    with pytest.raises(ReglaNegocio, match="muestra activa"):
        Muestra(orden, "Dr. Gómez", reloj=reloj)

from datetime import datetime

import pytest

from app.dominio.cambio_estado import CambioEstado
from app.dominio.enums import MotivoRechazo
from app.dominio.excepciones import TransicionInvalida
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import (
    AlertaRechazo,
    NotificadorCliente,
    ObservadorMuestra,
    RegistroTrazabilidad,
)


@pytest.fixture
def muestra(orden, reloj) -> Muestra:
    return Muestra(orden, "Dr. Gómez", "Clínica Centro", reloj=reloj)


def recorrido_feliz(muestra: Muestra) -> None:
    muestra.empaquetar("Enf. Ruiz", "Clínica Centro", "Conservadora 7")
    muestra.despachar("Enf. Ruiz", "Clínica Centro")
    muestra.recibir(True, "Bioq. Pérez", ubicacion="Laboratorio")
    muestra.analizar("Bioq. Pérez", "Laboratorio")


def recorrido_con_rechazo(muestra: Muestra) -> None:
    muestra.empaquetar("Enf. Ruiz")
    muestra.despachar("Enf. Ruiz")
    muestra.recibir(
        False, "Bioq. Pérez", [MotivoRechazo.PRECINTO_ROTO], "Laboratorio", "Precinto roto"
    )


# --- RegistroTrazabilidad ---

def test_el_historial_registra_cada_cambio_en_orden(muestra):
    muestra.suscribir(RegistroTrazabilidad())
    recorrido_feliz(muestra)

    pasos = [(c.anterior, c.nuevo) for c in muestra.historial]
    assert pasos == [
        (None, "EXTRAIDA"),
        ("EXTRAIDA", "EMPAQUETADA"),
        ("EMPAQUETADA", "EN_TRANSITO"),
        ("EN_TRANSITO", "RECIBIDA"),
        ("RECIBIDA", "ANALIZADA"),
    ]


def test_cada_renglon_del_historial_continua_al_anterior(muestra):
    muestra.suscribir(RegistroTrazabilidad())
    recorrido_feliz(muestra)
    for previo, siguiente in zip(muestra.historial, muestra.historial[1:]):
        assert siguiente.anterior == previo.nuevo


def test_el_historial_guarda_fecha_responsable_ubicacion_y_observacion(muestra):
    muestra.suscribir(RegistroTrazabilidad())
    recorrido_feliz(muestra)

    empaquetado = muestra.historial[1]
    assert empaquetado.responsable == "Enf. Ruiz"
    assert empaquetado.ubicacion == "Clínica Centro"
    assert empaquetado.observacion == "Conservadora 7"
    # El reloj falso avanza 30 minutos por consulta: las fechas van en orden.
    fechas = [c.fecha_hora for c in muestra.historial]
    assert fechas == sorted(fechas)
    assert fechas[0] == datetime(2026, 6, 1, 9, 0)


def test_el_historial_guarda_los_motivos_del_rechazo(muestra):
    muestra.suscribir(RegistroTrazabilidad())
    recorrido_con_rechazo(muestra)

    rechazo = muestra.historial[-1]
    assert rechazo.nuevo == "RECHAZADA"
    assert rechazo.motivos == (MotivoRechazo.PRECINTO_ROTO,)
    assert rechazo.observacion == "Precinto roto"


def test_una_transicion_invalida_no_agrega_nada_al_historial(muestra):
    muestra.suscribir(RegistroTrazabilidad())
    with pytest.raises(TransicionInvalida):
        muestra.despachar("x")
    assert len(muestra.historial) == 1  # solo la extracción


# --- AlertaRechazo ---

def test_alerta_rechazo_solo_reacciona_a_rechazada(muestra):
    alerta = AlertaRechazo()
    muestra.suscribir(alerta)
    recorrido_feliz(muestra)
    assert alerta.alertas == ()


def test_alerta_rechazo_avisa_cuando_la_muestra_es_rechazada(muestra):
    alerta = AlertaRechazo()
    muestra.suscribir(alerta)
    recorrido_con_rechazo(muestra)

    assert len(alerta.alertas) == 1
    assert "precinto roto" in alerta.alertas[0]
    assert "re-extracción" in alerta.alertas[0]


# --- NotificadorCliente ---

def test_notificador_cliente_solo_avisa_cuando_se_analiza(muestra, cliente):
    notificador = NotificadorCliente(cliente)
    muestra.suscribir(notificador)

    muestra.empaquetar("Enf. Ruiz")
    muestra.despachar("Enf. Ruiz")
    muestra.recibir(True, "Bioq. Pérez")
    assert notificador.avisos == ()  # todavía no está el resultado

    muestra.analizar("Bioq. Pérez")
    assert notificador.avisos == ("Ana Paz: ya está el resultado de Hemograma",)


def test_notificador_cliente_no_avisa_si_la_muestra_es_rechazada(muestra, cliente):
    notificador = NotificadorCliente(cliente)
    muestra.suscribir(notificador)
    recorrido_con_rechazo(muestra)
    assert notificador.avisos == ()


# --- Mecánica del patrón ---

def test_todos_los_observadores_reciben_el_aviso(muestra, cliente):
    registro, alerta, notificador = RegistroTrazabilidad(), AlertaRechazo(), NotificadorCliente(cliente)
    for observador in (registro, alerta, notificador):
        muestra.suscribir(observador)

    recorrido_feliz(muestra)

    assert len(muestra.historial) == 5
    assert alerta.alertas == ()
    assert len(notificador.avisos) == 1


def test_el_observador_recibe_la_muestra_y_el_cambio(muestra):
    recibidos = []

    class Espia(ObservadorMuestra):
        def actualizar(self, muestra, cambio):
            recibidos.append((muestra, cambio))

    espia = Espia()
    muestra.suscribir(espia)
    muestra.empaquetar("Enf. Ruiz")

    (muestra_recibida, cambio), = recibidos
    assert muestra_recibida is muestra
    assert isinstance(cambio, CambioEstado)
    assert (cambio.anterior, cambio.nuevo) == ("EXTRAIDA", "EMPAQUETADA")


def test_un_observador_desuscripto_no_recibe_mas_avisos(muestra):
    alerta = AlertaRechazo()
    muestra.suscribir(alerta)
    muestra.desuscribir(alerta)
    recorrido_con_rechazo(muestra)
    assert alerta.alertas == ()


def test_sin_observadores_la_muestra_cambia_de_estado_igual(muestra):
    recorrido_feliz(muestra)
    assert muestra.estado.nombre == "ANALIZADA"

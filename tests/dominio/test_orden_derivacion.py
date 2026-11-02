from datetime import datetime

import pytest

from app.dominio.consulta import Consulta
from app.dominio.enums import Prioridad, TipoConsulta
from app.dominio.excepciones import ReglaNegocio


class MuestraFalsa:
    """Reemplaza a Muestra (Fase 3): la orden solo necesita saber si está activa."""

    def __init__(self, activa: bool = True) -> None:
        self.activa = activa

    def esta_activa(self) -> bool:
        return self.activa


def test_orden_nueva_no_tiene_muestra_activa(orden):
    assert orden.muestra_activa() is None
    assert orden.muestras == ()


def test_orden_tiene_prioridad_normal_por_defecto(orden):
    assert orden.prioridad is Prioridad.NORMAL


def test_orden_acepta_la_primera_muestra(orden):
    muestra = MuestraFalsa()
    orden.agregar_muestra(muestra)
    assert orden.muestra_activa() is muestra


def test_orden_rechaza_una_segunda_muestra_activa(orden):
    orden.agregar_muestra(MuestraFalsa())
    with pytest.raises(ReglaNegocio, match="muestra activa"):
        orden.agregar_muestra(MuestraFalsa())
    assert len(orden.muestras) == 1


def test_orden_acepta_re_extraccion_tras_un_rechazo(orden):
    rechazada = MuestraFalsa()
    orden.agregar_muestra(rechazada)
    rechazada.activa = False  # el laboratorio la rechazó

    assert orden.muestra_activa() is None
    nueva = MuestraFalsa()
    orden.agregar_muestra(nueva)

    assert orden.muestra_activa() is nueva
    assert orden.muestras == (rechazada, nueva)  # la rechazada queda en la historia de la orden


def test_lista_de_muestras_no_se_modifica_desde_afuera(orden):
    with pytest.raises(AttributeError):
        orden.muestras.append("x")  # es una tupla


# --- La orden se emite desde la consulta ---

def test_consulta_emite_ordenes_de_derivacion(perro, veterinario, hemograma):
    consulta = Consulta(TipoConsulta.CONSULTA, datetime(2026, 5, 10, 11, 0), perro, veterinario)
    assert consulta.ordenes == ()

    orden = consulta.emitir_orden(hemograma, Prioridad.URGENTE)

    assert orden.tipo_analisis is hemograma
    assert orden.prioridad is Prioridad.URGENTE
    assert consulta.ordenes == (orden,)

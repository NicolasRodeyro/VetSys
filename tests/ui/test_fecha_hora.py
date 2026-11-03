"""Selector de fecha y hora: valor como date/time, avisos por campo y redondeo de «ahora»."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.ui.fecha_hora import SelectorFechaHora, dia_local, redondear_adelante
from app.ui.pantalla import Pantalla
from tests.ui.conftest import sin_parametros

pytestmark = pytest.mark.usefixtures("ahora")


class PantallaDeMentira(Pantalla):
    clave, titulo, icono, grupo = "x", "X", None, "X"

    def build(self):
        return None


@pytest.fixture
def selector(sesion_ui) -> SelectorFechaHora:
    return SelectorFechaHora(PantallaDeMentira(sesion_ui))


@pytest.mark.parametrize("momento, esperado", [
    (datetime(2026, 11, 2, 12, 0), datetime(2026, 11, 2, 12, 0)),
    (datetime(2026, 11, 2, 12, 1), datetime(2026, 11, 2, 12, 5)),
    (datetime(2026, 11, 2, 12, 5, 30), datetime(2026, 11, 2, 12, 10)),
    (datetime(2026, 11, 2, 12, 56), datetime(2026, 11, 2, 13, 0)),
    (datetime(2026, 11, 2, 23, 58), datetime(2026, 11, 3, 0, 0)),
])
def test_redondea_hacia_adelante_a_multiplos_de_cinco(momento, esperado):
    assert redondear_adelante(momento) == esperado


def test_el_dia_elegido_no_se_corre_con_el_huso_horario():
    assert dia_local(date(2026, 11, 9)) == date(2026, 11, 9)
    assert dia_local(datetime(2026, 11, 9, 0, 0)) == date(2026, 11, 9)
    con_huso = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    assert dia_local(con_huso) == con_huso.astimezone().date()


def test_empieza_vacio_y_sin_valor(selector):
    assert selector.vacio() and selector.valor is None
    assert selector.faltantes() == ["la fecha", "la hora"]


def test_poner_ahora_propone_el_momento_actual(selector):
    selector.poner_ahora()
    assert selector.valor == datetime(2026, 11, 2, 12, 0)
    assert selector.fecha.value == "02/11/2026" and selector.hora.value == "12:00"
    assert not selector.vacio() and selector.faltantes() == []


def test_el_valor_junta_la_fecha_y_la_hora_sin_parsear_texto(selector):
    selector.elegir_fecha(date(2026, 11, 9))
    assert selector.valor is None and selector.faltantes() == ["la hora"]
    selector.elegir_hora(time(10, 30, 45))
    assert selector.valor == datetime(2026, 11, 9, 10, 30)  # sin segundos


def test_el_calendario_con_huso_horario_elige_el_dia_local(selector):
    selector.elegir_fecha(datetime(2026, 11, 9, 15, 0, tzinfo=timezone(timedelta(hours=-3))))
    assert selector.fecha_elegida == datetime(2026, 11, 9, 15, 0, tzinfo=timezone(timedelta(hours=-3))).astimezone().date()


def test_marca_en_rojo_solo_lo_que_falta_y_lo_limpia_al_elegir(selector):
    selector.marcar_faltantes()
    assert selector.fecha.error == "Elegí la fecha" and selector.hora.error == "Elegí la hora"
    selector.elegir_fecha(date(2026, 11, 9))
    assert selector.fecha.error is None and selector.hora.error == "Elegí la hora"
    selector.elegir_hora(time(9, 0))
    assert selector.hora.error is None


def test_limpiar_avisos(selector):
    selector.marcar_faltantes()
    selector.limpiar_avisos()
    assert selector.fecha.error is None and selector.hora.error is None


def test_los_campos_son_de_solo_lectura_y_abren_calendario_y_reloj(selector):
    assert selector.fecha.read_only and selector.hora.read_only
    assert sin_parametros(selector.fecha.on_click) and sin_parametros(selector.hora.on_click)


def test_avisa_a_la_pantalla_cuando_cambia_algo(sesion_ui):
    cambios = []
    selector = SelectorFechaHora(PantallaDeMentira(sesion_ui), al_cambiar=lambda: cambios.append(1))
    selector.elegir_fecha(date(2026, 11, 9))
    selector.elegir_hora(time(9, 0))
    selector.elegir_fecha(None)  # cancelar el calendario no cambia nada
    assert len(cambios) == 2

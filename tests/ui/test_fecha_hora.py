"""Selector de fecha y hora: el valor se arma sin ventana; el calendario y el reloj de Flet no se abren acá."""

from datetime import date, datetime, time, timezone
from types import SimpleNamespace

import pytest

from app.servicios.excepciones import EntradaInvalida
from app.ui.fecha_hora import SelectorFechaHora, a_fecha_local

pytestmark = pytest.mark.usefixtures("ahora")  # el reloj de los tests marca 2026-11-02 12:00


def test_empieza_vacio_y_pide_lo_que_falta():
    selector = SelectorFechaHora()
    with pytest.raises(EntradaInvalida, match="elegí la fecha"):
        selector.valor("El inicio")
    selector.poner_fecha(date(2026, 11, 9))
    with pytest.raises(EntradaInvalida, match="elegí la hora"):
        selector.valor("El inicio")


def test_junta_fecha_y_hora_y_las_muestra_en_los_campos():
    selector = SelectorFechaHora()
    selector.poner(datetime(2026, 11, 9, 10, 5, 33))  # los segundos se descartan
    assert selector.valor("El inicio") == datetime(2026, 11, 9, 10, 5)
    assert (selector.campo_fecha.value, selector.campo_hora.value) == ("09/11/2026", "10:05")


def test_poner_none_los_limpia():
    selector = SelectorFechaHora()
    selector.poner(datetime(2026, 11, 9, 10, 0))
    selector.poner(None)
    assert selector.fecha is None and selector.hora is None
    assert selector.campo_fecha.value == "" and selector.campo_hora.value == ""


def test_los_campos_son_de_solo_lectura_para_no_escribir_un_formato_mal():
    selector = SelectorFechaHora()
    assert selector.campo_fecha.read_only and selector.campo_hora.read_only


def test_propone_el_momento_actual_redondeado_al_proximo_paso(monkeypatch):
    selector = SelectorFechaHora(paso_minutos=15)
    selector.poner_ahora()
    assert selector.valor("El inicio") == datetime(2026, 11, 2, 12, 0)  # 12:00 ya es múltiplo

    from app.servicios import tiempo
    monkeypatch.setattr(tiempo, "ahora", lambda: datetime(2026, 11, 2, 12, 7, 40))
    selector.poner_ahora()
    assert selector.valor("El inicio") == datetime(2026, 11, 2, 12, 15)


def test_la_fecha_del_calendario_se_toma_del_dia_elegido():
    assert a_fecha_local(date(2026, 11, 9)) == date(2026, 11, 9)
    assert a_fecha_local(datetime(2026, 11, 9, 0, 0)) == date(2026, 11, 9)
    # Con zona horaria se pasa a la hora local antes de quedarse con el día.
    # (mediodía UTC es el mismo día en cualquier huso horario, así el test no depende de la máquina)
    assert a_fecha_local(datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)) == date(2026, 11, 9)


# ---- Las ventanas de Flet: se prueban con una «página» falsa que guarda lo que se le muestra ----

class PaginaFalsa:
    def __init__(self) -> None:
        self.mostrados: list = []

    def show_dialog(self, dialogo) -> None:
        self.mostrados.append(dialogo)


def con_pagina(selector: SelectorFechaHora) -> PaginaFalsa:
    pagina = PaginaFalsa()
    for nombre in ("campo_fecha", "campo_hora"):
        real = getattr(selector, nombre)
        # El campo real no tiene `page` hasta estar en una ventana: se lo reemplaza por uno que sí.
        setattr(selector, nombre, SimpleNamespace(
            page=pagina, update=lambda: None, value=real.value, read_only=True))
    return pagina


def test_el_calendario_abre_en_la_fecha_elegida_y_al_aceptar_la_guarda():
    selector = SelectorFechaHora()
    selector.poner(datetime(2026, 11, 9, 10, 0))
    pagina = con_pagina(selector)

    selector.elegir_fecha()
    calendario = pagina.mostrados[-1]
    assert calendario.value.date() == date(2026, 11, 9)
    assert calendario.first_date.date() == date(2026, 11, 2)  # no se pueden elegir días ya pasados

    calendario.value = datetime(2026, 12, 24)
    calendario.on_change()
    assert selector.fecha == date(2026, 12, 24)
    assert selector.campo_fecha.value == "24/12/2026"


def test_el_reloj_es_de_24_horas_y_al_aceptar_guarda_la_hora():
    selector = SelectorFechaHora()
    pagina = con_pagina(selector)

    selector.elegir_hora()
    reloj = pagina.mostrados[-1]
    assert reloj.hour_format.name == "H24"

    reloj.value = time(18, 30)
    reloj.on_change()
    assert selector.hora == time(18, 30)
    assert selector.campo_hora.value == "18:30"

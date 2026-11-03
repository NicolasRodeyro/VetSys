from datetime import date, datetime, time

import pytest

from app.servicios import clientes
from app.ui.pantallas.turnos import PantallaTurnos
from tests.servicios.conftest import mascota, veterinario
from tests.ui.conftest import elegir, elegir_mascota, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaTurnos:
    pantalla = PantallaTurnos(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


def preparar(p, vet="MP-1001", mascota_nombre="Toby", inicio=datetime(2026, 11, 9, 10, 0), duracion="30"):
    p.veterinario.value = str(veterinario(vet).id)
    p.cargar_agenda()
    elegir_mascota(p.selector, mascota_nombre, "paz")
    p.inicio.poner(inicio)
    p.duracion.value = duracion


def test_ofrece_los_veterinarios_y_propone_la_hora_actual(pantalla):
    assert len(pantalla.veterinario.options) == 4
    assert (pantalla.inicio.fecha, pantalla.inicio.hora) == (date(2026, 11, 2), time(12, 0))
    assert (pantalla.inicio.campo_fecha.value, pantalla.inicio.campo_hora.value) == ("02/11/2026", "12:00")
    assert pantalla.tabla.cantidad == 0


def test_reservar_sin_elegir_veterinario_o_mascota_se_explica(pantalla, mensajes):
    pantalla.reservar()
    # Dice qué falta, en la barra de mensajes, en un aviso junto al botón y en rojo en cada campo.
    assert "el veterinario" in mensajes.errores[-1] and "la mascota" in mensajes.errores[-1]
    assert pantalla.aviso.visible and "el veterinario" in pantalla.aviso.content.controls[1].value
    assert pantalla.veterinario.error_text == "Elegí un veterinario"
    assert pantalla.selector.lista.error_text == "Elegí la mascota"
    assert pantalla.tabla.cantidad == 0

    pantalla.veterinario.value = str(veterinario("MP-1001").id)
    pantalla.cargar_agenda()
    assert pantalla.veterinario.error_text is None  # al elegirlo, el aviso en rojo desaparece
    pantalla.reservar()
    assert "el veterinario" not in mensajes.errores[-1] and "la mascota" in mensajes.errores[-1]


def test_el_aviso_desaparece_al_corregir_y_reservar(pantalla, mensajes):
    pantalla.reservar()
    assert pantalla.aviso.visible
    preparar(pantalla)
    pantalla.reservar()
    assert not pantalla.aviso.visible and mensajes.exitos == ["Turno reservado."]
    assert pantalla.veterinario.error_text is None and pantalla.selector.lista.error_text is None


def test_un_error_de_la_reserva_tambien_queda_escrito_junto_al_boton(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    preparar(pantalla, inicio=datetime(2026, 11, 9, 10, 15))
    pantalla.reservar()
    assert "se superpone" in pantalla.aviso.content.controls[1].value


def test_despues_de_reservar_el_formulario_queda_limpio(pantalla, mensajes):
    preparar(pantalla, inicio=datetime(2026, 11, 9, 10, 0), duracion="45")
    pantalla.reservar()
    assert mensajes.exitos == ["Turno reservado."]

    assert pantalla.selector.busqueda.value == "" and pantalla.selector.mascota_id is None
    assert pantalla.selector.lista.options == [] and not pantalla.selector.buscador.panel.visible
    assert pantalla.duracion.value == "30"
    assert (pantalla.inicio.fecha, pantalla.inicio.hora) == (date(2026, 11, 2), time(12, 0))  # vuelve a «ahora»
    assert pantalla.veterinario.value == str(veterinario("MP-1001").id)  # la agenda sigue a la vista
    assert pantalla.tabla.cantidad == 1


def test_si_la_reserva_falla_no_se_borra_lo_cargado(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    preparar(pantalla, inicio=datetime(2026, 11, 9, 10, 15))
    pantalla.reservar()  # se superpone
    assert pantalla.selector.mascota_id is not None
    assert pantalla.inicio.valor("El inicio") == datetime(2026, 11, 9, 10, 15)


def test_reservar_un_turno_lo_muestra_en_la_agenda(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    assert mensajes.errores == [] and mensajes.exitos == ["Turno reservado."]
    assert pantalla.tabla.cantidad == 1


def test_un_turno_superpuesto_se_rechaza(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    preparar(pantalla, inicio=datetime(2026, 11, 9, 10, 15))
    pantalla.reservar()
    assert "se superpone" in mensajes.errores[-1]
    assert pantalla.tabla.cantidad == 1


def test_un_turno_contiguo_se_acepta(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    preparar(pantalla, inicio=datetime(2026, 11, 9, 10, 30))
    pantalla.reservar()
    assert mensajes.errores == [] and pantalla.tabla.cantidad == 2


@pytest.mark.parametrize("duracion, mensaje", [("0", "mayor a cero"), ("abc", "número entero")])
def test_duracion_invalida(pantalla, mensajes, duracion, mensaje):
    preparar(pantalla, duracion=duracion)
    pantalla.reservar()
    assert mensaje in mensajes.errores[-1]
    assert pantalla.tabla.cantidad == 0


def test_sin_fecha_o_sin_hora_se_pide_elegirla(pantalla, mensajes):
    preparar(pantalla)
    pantalla.inicio.poner_fecha(None)
    pantalla.reservar()
    assert "la fecha" in mensajes.errores[-1] and "la hora" not in mensajes.errores[-1]
    assert pantalla.inicio.campo_fecha.error_text == "Elegí la fecha"

    pantalla.inicio.poner_fecha(date(2026, 11, 9))
    pantalla.inicio.poner_hora(None)
    pantalla.reservar()
    assert "la hora" in mensajes.errores[-1] and "la fecha" not in mensajes.errores[-1]
    assert pantalla.inicio.campo_hora.error_text == "Elegí la hora"
    assert pantalla.tabla.cantidad == 0


def test_fecha_y_hora_se_eligen_por_separado(pantalla, mensajes):
    preparar(pantalla)
    pantalla.inicio.poner_fecha(date(2026, 12, 1))
    pantalla.inicio.poner_hora(time(16, 45))
    pantalla.reservar()
    assert mensajes.errores == []
    assert pantalla.tabla.textos()[0][0] == "01/12/2026 16:45"


def test_al_volver_a_la_pantalla_no_pisa_la_fecha_elegida(pantalla):
    pantalla.inicio.poner(datetime(2026, 12, 1, 16, 45))
    pantalla.al_mostrar()
    assert pantalla.inicio.valor("El inicio") == datetime(2026, 12, 1, 16, 45)


def test_cancelar_un_turno_con_el_boton_de_la_fila_libera_el_horario(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    boton = pantalla.tabla._tabla.rows[0].cells[-1].content
    assert sin_parametros(boton.on_click)
    boton.on_click()

    assert mensajes.exitos[-1] == "Turno cancelado."
    assert pantalla.tabla.cantidad == 0  # no se muestra...
    pantalla.ver_cancelados.value = True
    pantalla.cargar_agenda()
    assert pantalla.tabla.cantidad == 1  # ...pero no se borró
    preparar(pantalla)
    pantalla.reservar()  # y el horario quedó libre
    assert mensajes.errores == []


def test_cambiar_de_veterinario_muestra_otra_agenda(pantalla):
    preparar(pantalla)
    pantalla.reservar()
    pantalla.veterinario.value = str(veterinario("MP-1002").id)
    pantalla.cargar_agenda()
    assert pantalla.tabla.cantidad == 0


def test_los_botones_no_reciben_el_evento(pantalla):
    for manejador in (pantalla.reservar, pantalla.cargar_agenda):
        assert sin_parametros(manejador)


def test_una_mascota_de_baja_no_aparece_en_el_selector(pantalla):
    clientes.dar_de_baja_mascota(mascota("30111222", "Toby").id)
    pantalla.selector.busqueda.value = "paz"
    pantalla.selector.buscar()
    assert [o.text.split(" ")[0] for o in pantalla.selector.lista.options] == ["Mimi"]
    elegir(pantalla.selector.lista, "Mimi")
    assert pantalla.selector.mascota_id == mascota("30111222", "Mimi").id

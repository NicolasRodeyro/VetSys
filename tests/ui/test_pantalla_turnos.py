from datetime import datetime

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
    p.momento.poner(inicio)
    p.duracion.value = duracion


def test_ofrece_los_veterinarios_y_propone_la_hora_actual(pantalla):
    assert len(pantalla.veterinario.options) == 4
    assert pantalla.momento.valor == datetime(2026, 11, 2, 12, 0)  # AHORA, ya redondeado a 5 minutos
    assert pantalla.momento.fecha.value == "02/11/2026" and pantalla.momento.hora.value == "12:00"
    assert pantalla.tabla.cantidad == 0


def test_reservar_sin_nada_elegido_avisa_que_falta_en_tres_lugares(pantalla, mensajes):
    pantalla.momento.poner_fecha(None)
    pantalla.momento.poner_hora(None)
    pantalla.reservar()
    esperado = "Para reservar el turno falta elegir: el veterinario, la mascota, la fecha, la hora."
    assert mensajes.errores[-1] == esperado                      # 1. barra de mensajes
    assert pantalla.aviso_reserva.visible and pantalla._texto_aviso.value == esperado  # 2. recuadro junto al botón
    assert pantalla.veterinario.error_text == "Elegí un veterinario"                   # 3. campos en rojo
    assert pantalla.selector.lista.error_text == "Elegí la mascota"
    assert pantalla.momento.fecha.error == "Elegí la fecha" and pantalla.momento.hora.error == "Elegí la hora"
    assert pantalla.tabla.cantidad == 0


def test_reservar_sin_mascota_dice_solo_eso(pantalla, mensajes):
    pantalla.veterinario.value = str(veterinario("MP-1001").id)
    pantalla.reservar()
    assert mensajes.errores[-1] == "Para reservar el turno falta elegir: la mascota."


def test_los_avisos_desaparecen_al_elegir_lo_que_faltaba(pantalla):
    pantalla.reservar()
    assert pantalla.aviso_reserva.visible
    pantalla.veterinario.value = str(veterinario("MP-1001").id)
    pantalla.cargar_agenda()
    assert pantalla.veterinario.error_text is None
    assert "la mascota" in pantalla._texto_aviso.value and "el veterinario" not in pantalla._texto_aviso.value
    elegir_mascota(pantalla.selector, "Toby", "paz")
    assert not pantalla.aviso_reserva.visible and pantalla.selector.lista.error_text is None


def test_reservar_un_turno_lo_muestra_en_la_agenda(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    assert mensajes.errores == [] and mensajes.exitos == ["Turno reservado."]
    assert pantalla.tabla.cantidad == 1
    assert not pantalla.aviso_reserva.visible


def test_despues_de_reservar_se_limpia_el_formulario_pero_no_el_veterinario(pantalla):
    preparar(pantalla, duracion="45")
    pantalla.reservar()
    assert pantalla.selector.mascota_id is None and pantalla.selector.busqueda.value == ""
    assert pantalla.momento.valor == datetime(2026, 11, 2, 12, 0) and pantalla.duracion.value == "30"
    assert pantalla.veterinario.value == str(veterinario("MP-1001").id)
    assert pantalla.tabla.cantidad == 1


def test_si_la_reserva_falla_no_se_borra_nada(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    preparar(pantalla, inicio=datetime(2026, 11, 9, 10, 15))
    pantalla.reservar()
    assert "se superpone" in mensajes.errores[-1]
    assert pantalla.aviso_reserva.visible and "se superpone" in pantalla._texto_aviso.value  # también junto al botón
    assert pantalla.selector.mascota_id is not None and pantalla.momento.valor == datetime(2026, 11, 9, 10, 15)
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
def test_datos_invalidos(pantalla, mensajes, duracion, mensaje):
    preparar(pantalla, duracion=duracion)
    pantalla.reservar()
    assert mensaje in mensajes.errores[-1]
    assert pantalla.tabla.cantidad == 0


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

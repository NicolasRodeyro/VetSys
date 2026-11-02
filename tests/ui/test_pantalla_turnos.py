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


def preparar(p, vet="MP-1001", mascota_nombre="Toby", inicio="2026-11-09 10:00", duracion="30"):
    p.veterinario.value = str(veterinario(vet).id)
    p.cargar_agenda()
    elegir_mascota(p.selector, mascota_nombre, "paz")
    p.inicio.value, p.duracion.value = inicio, duracion


def test_ofrece_los_veterinarios_y_propone_la_hora_actual(pantalla):
    assert len(pantalla.veterinario.options) == 4
    assert pantalla.inicio.value == "2026-11-02 12:00"
    assert pantalla.tabla.cantidad == 0


def test_reservar_sin_elegir_veterinario_o_mascota_se_explica(pantalla, mensajes):
    pantalla.reservar()
    assert "Elegí el veterinario" in mensajes.errores[-1]
    pantalla.veterinario.value = str(veterinario("MP-1001").id)
    pantalla.reservar()
    assert "Elegí la mascota" in mensajes.errores[-1]


def test_reservar_un_turno_lo_muestra_en_la_agenda(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    assert mensajes.errores == [] and mensajes.exitos == ["Turno reservado."]
    assert pantalla.tabla.cantidad == 1


def test_un_turno_superpuesto_se_rechaza(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    pantalla.inicio.value = "2026-11-09 10:15"
    pantalla.reservar()
    assert "se superpone" in mensajes.errores[-1]
    assert pantalla.tabla.cantidad == 1


def test_un_turno_contiguo_se_acepta(pantalla, mensajes):
    preparar(pantalla)
    pantalla.reservar()
    pantalla.inicio.value = "2026-11-09 10:30"
    pantalla.reservar()
    assert mensajes.errores == [] and pantalla.tabla.cantidad == 2


@pytest.mark.parametrize("inicio, duracion, mensaje", [
    ("mañana a la tarde", "30", "AAAA-MM-DD HH:MM"), ("2026-11-09 10:00", "0", "mayor a cero"), ("2026-11-09 10:00", "abc", "número entero")])
def test_datos_invalidos(pantalla, mensajes, inicio, duracion, mensaje):
    preparar(pantalla, inicio=inicio, duracion=duracion)
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

from datetime import date

import pytest

from app.servicios import clientes as svc
from app.ui.pantallas.mascotas import PantallaMascotas
from tests.servicios.conftest import mascota
from tests.ui.conftest import sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaMascotas:
    pantalla = PantallaMascotas(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


def elegir_a_ana(p):
    p.busqueda.value = "paz"
    p.buscar_clientes()
    p.clientes.value = p.clientes.options[0].key
    p.elegir_cliente()


def test_la_pantalla_ofrece_las_especies_del_catalogo(pantalla):
    assert sorted(o.key for o in pantalla.especie.options) == ["Conejo", "Gato", "Perro"]


def test_buscar_un_cliente_y_ver_sus_mascotas(pantalla):
    elegir_a_ana(pantalla)
    assert len(pantalla.clientes.options) == 1
    assert pantalla.tabla.cantidad == 2  # Toby y Mimi


def test_buscar_un_cliente_que_no_existe_avisa(pantalla, mensajes):
    pantalla.busqueda.value = "zzz"
    pantalla.buscar_clientes()
    assert "No se encontró ningún cliente" in mensajes.errores[0]
    assert pantalla.tabla.cantidad == 0


def test_alta_de_una_mascota_para_el_cliente_elegido(pantalla, mensajes):
    elegir_a_ana(pantalla)
    pantalla.nombre.value, pantalla.especie.value, pantalla.sexo.value = "Rocky", "Perro", "MACHO"
    pantalla.nacimiento.value = "2026-05-01"
    pantalla.guardar()

    assert mensajes.errores == [] and mensajes.exitos == ["Mascota guardada."]
    assert pantalla.tabla.cantidad == 3
    assert "Rocky" in pantalla.titulo_formulario.value and pantalla.historia.visible  # quedó elegida


def test_no_se_da_de_alta_una_mascota_sin_elegir_cliente(pantalla, mensajes):
    pantalla.nombre.value, pantalla.especie.value, pantalla.sexo.value = "Rocky", "Perro", "MACHO"
    pantalla.nacimiento.value = "2026-05-01"
    pantalla.guardar()
    assert "elegí el cliente" in mensajes.errores[0]


@pytest.mark.parametrize("fecha, mensaje", [("mañana", "AAAA-MM-DD"), ("2027-01-01", "no puede ser futura"), ("", "AAAA-MM-DD")])
def test_fecha_de_nacimiento_invalida(pantalla, mensajes, fecha, mensaje):
    elegir_a_ana(pantalla)
    pantalla.nombre.value, pantalla.especie.value, pantalla.sexo.value = "Rocky", "Perro", "MACHO"
    pantalla.nacimiento.value = fecha
    pantalla.guardar()
    assert mensaje in mensajes.errores[0]
    assert pantalla.tabla.cantidad == 2


def test_elegir_una_mascota_muestra_su_historia_y_sus_vacunas_pendientes(pantalla):
    elegir_a_ana(pantalla)
    toby = mascota("30111222", "Toby")
    pantalla.elegir_mascota(toby.id)

    assert pantalla.nombre.value == "Toby" and pantalla.especie.value == "Perro"
    assert pantalla.especie.disabled and pantalla.nacimiento.disabled  # no se corrigen
    assert pantalla.historia.visible
    assert pantalla.tabla_vacunas.cantidad == 2  # Sextuple y Antirrabica del seed
    assert len(pantalla.pendientes.controls) == 2  # Sextuple (refuerzo vencido) y Tos de las perreras
    assert {o.key for o in pantalla.vacuna.options} == {"Sextuple", "Antirrabica", "Tos de las perreras"}


def test_modificar_el_nombre_de_una_mascota(pantalla, mensajes):
    elegir_a_ana(pantalla)
    toby = mascota("30111222", "Toby")
    pantalla.elegir_mascota(toby.id)
    pantalla.nombre.value = "Tobías"
    pantalla.guardar()
    assert mensajes.errores == []
    assert svc.obtener_mascota(toby.id).nombre == "Tobías"


def test_guardar_las_alergias_y_antecedentes(pantalla, mensajes):
    toby = mascota("30111222", "Toby")
    pantalla.elegir_mascota(toby.id)
    pantalla.alergias.value, pantalla.antecedentes.value = "Polen", "Operado en 2026"
    pantalla.guardar_historia()
    assert mensajes.exitos[-1] == "Historia clínica guardada."
    assert svc.obtener_mascota(toby.id).historia_clinica.alergias == "Polen"


def test_aplicar_una_vacuna_la_saca_de_las_pendientes(pantalla, mensajes):
    luna = mascota("33222111", "Luna")  # gata de 4 meses sin vacunas
    pantalla.elegir_mascota(luna.id)
    assert len(pantalla.pendientes.controls) == 3

    pantalla.vacuna.value = "Triple felina"
    pantalla.aplicar_vacuna()

    assert mensajes.exitos[-1] == "Vacuna registrada."
    assert pantalla.tabla_vacunas.cantidad == 1 and len(pantalla.pendientes.controls) == 2


def test_aplicar_una_vacuna_con_fecha_futura_se_rechaza(pantalla, mensajes):
    luna = mascota("33222111", "Luna")
    pantalla.elegir_mascota(luna.id)
    pantalla.vacuna.value, pantalla.fecha_vacuna.value = "Triple felina", "2027-01-01"
    pantalla.aplicar_vacuna()
    assert "no puede ser futura" in mensajes.errores[0]
    assert pantalla.tabla_vacunas.cantidad == 0


def test_baja_y_reactivacion_de_una_mascota(pantalla, mensajes):
    luna = mascota("33222111", "Luna")
    pantalla.elegir_mascota(luna.id)
    pantalla.dar_de_baja()
    assert pantalla.boton_reactivar.visible and not pantalla.boton_baja.visible
    assert "DADA DE BAJA" in pantalla.estado.value
    pantalla.reactivar()
    assert pantalla.boton_baja.visible and svc.obtener_mascota(luna.id).activa


def test_nueva_limpia_el_formulario_y_oculta_la_historia(pantalla):
    pantalla.elegir_mascota(mascota("30111222", "Toby").id)
    pantalla.nueva()
    assert pantalla.nombre.value == "" and not pantalla.historia.visible
    assert not pantalla.especie.disabled


def test_los_botones_no_reciben_el_evento(pantalla):
    for manejador in (pantalla.buscar_clientes, pantalla.elegir_cliente, pantalla.nueva, pantalla.guardar,
                      pantalla.dar_de_baja, pantalla.reactivar, pantalla.guardar_historia, pantalla.aplicar_vacuna):
        assert sin_parametros(manejador)


def test_la_fecha_por_defecto_de_la_vacuna_es_hoy(pantalla):
    pantalla.elegir_mascota(mascota("30111222", "Toby").id)
    assert pantalla.fecha_vacuna.value == date(2026, 11, 2).isoformat()


# ---- búsqueda en vivo del cliente ----

def escribir_cliente(p, texto):
    p.busqueda.value = texto
    p.buscador._al_escribir()


def test_al_escribir_aparece_la_lista_de_clientes(pantalla):
    escribir_cliente(pantalla, "paz")
    assert pantalla.buscador.panel.visible
    assert [f.title.value for f in pantalla.buscador.filas.controls] == ["Paz, Ana"]


def test_tocar_un_cliente_de_la_lista_muestra_sus_mascotas(pantalla):
    escribir_cliente(pantalla, "paz")
    pantalla.buscador.filas.controls[0].on_click()
    assert pantalla.busqueda.value == "Paz, Ana"
    assert pantalla.clientes.value == pantalla.clientes.options[0].key
    assert pantalla.tabla.cantidad == 2  # Toby y Mimi
    assert not pantalla.buscador.panel.visible


def test_al_seguir_escribiendo_se_descarta_el_cliente_elegido(pantalla):
    escribir_cliente(pantalla, "paz")
    pantalla.buscador.filas.controls[0].on_click()
    escribir_cliente(pantalla, "paze")
    assert pantalla.clientes.options == [] and pantalla.tabla.cantidad == 0
    assert not pantalla.historia.visible


def test_buscar_con_el_boton_sigue_funcionando_y_cierra_la_lista(pantalla):
    escribir_cliente(pantalla, "paz")
    pantalla.buscar_clientes()
    assert not pantalla.buscador.panel.visible
    assert len(pantalla.clientes.options) == 1

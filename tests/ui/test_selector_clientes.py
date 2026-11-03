"""La búsqueda de cliente muestra, mientras se escribe, la lista de clientes que coinciden.

Es el mismo componente (BuscadorClientes) en el selector de mascota (Turnos, Consultas,
Comprobantes, Muestras) y en la pantalla de Mascotas.
"""

import pytest

from app.ui.pantallas.turnos import PantallaTurnos
from app.ui.selectores import SelectorMascota
from tests.ui.conftest import sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def selector(sesion_ui):
    pantalla = PantallaTurnos(sesion_ui)
    pantalla.build()
    return pantalla.selector


def titulos(selector) -> list[str]:
    return [fila.title.value for fila in selector.buscador.filas.controls]


def tocar(selector, apellido: str) -> None:
    """Toca en la lista el cliente de ese apellido, como lo haría el usuario."""
    fila = next(f for f in selector.buscador.filas.controls if f.title.value.startswith(apellido))
    fila.on_click()


def escribir(selector, texto: str) -> None:
    selector.busqueda.value = texto
    selector.buscador._al_escribir()


def test_al_tocar_el_campo_vacio_se_ofrecen_todos_los_clientes(selector):
    selector.buscador._al_enfocar()
    assert selector.buscador.panel.visible
    assert len(titulos(selector)) == 10
    assert titulos(selector)[0].startswith("Castro")  # ordenados por apellido


def test_mientras_se_escribe_la_lista_se_va_acotando(selector):
    escribir(selector, "p")
    primeros = len(titulos(selector))
    escribir(selector, "paz")
    assert titulos(selector) == ["Paz, Ana"]
    assert 1 < primeros <= 10


def test_se_encuentra_tambien_por_dni_y_por_nombre(selector):
    escribir(selector, "2844")
    assert titulos(selector) == ["Gómez, Luis"]
    escribir(selector, "sof")
    assert titulos(selector) == ["Luna, Sofía"]


def test_cada_renglon_muestra_el_dni_y_las_mascotas(selector):
    escribir(selector, "paz")
    detalle = selector.buscador.filas.controls[0].subtitle.value
    assert "30111222" in detalle and "Toby" in detalle and "Mimi" in detalle


def test_elegir_un_cliente_carga_sus_mascotas(selector):
    escribir(selector, "paz")
    tocar(selector, "Paz")
    assert selector.busqueda.value == "Paz, Ana"
    assert not selector.buscador.panel.visible
    assert sorted(o.text.split(" ")[0] for o in selector.lista.options) == ["Mimi", "Toby"]
    assert selector.mascota_id is None  # tiene dos: hay que elegir cuál


def test_un_cliente_con_una_sola_mascota_la_deja_elegida(selector):
    escribir(selector, "gómez")
    tocar(selector, "Gómez")
    assert [o.text.split(" ")[0] for o in selector.lista.options] == ["Rex"]
    assert selector.mascota_id is not None


def test_sin_coincidencias_lo_dice(selector):
    escribir(selector, "zzzz")
    assert titulos(selector) == []
    assert selector.buscador.panel.visible and "No hay clientes" in selector.buscador.titulo


def test_al_volver_a_escribir_se_descarta_la_mascota_elegida(selector):
    escribir(selector, "gómez")
    tocar(selector, "Gómez")
    assert selector.mascota_id is not None
    escribir(selector, "gómezz")  # el usuario sigue escribiendo: ya no es ese cliente
    assert selector.mascota_id is None and selector.lista.options == []


def test_avisa_a_las_pantallas_cuando_cambia_la_mascota(sesion_ui):
    avisos = []
    pantalla = PantallaTurnos(sesion_ui)
    pantalla.build()
    selector = SelectorMascota(pantalla, lambda: avisos.append(selector.mascota_id))
    escribir(selector, "gómez")
    tocar(selector, "Gómez")
    assert avisos and avisos[-1] is not None
    escribir(selector, "gómezz")
    assert avisos[-1] is None


def test_la_lista_se_puede_cerrar(selector):
    selector.buscador._al_enfocar()
    selector.buscador.cerrar()
    assert not selector.buscador.panel.visible


def test_una_lista_larga_se_acota_y_pide_seguir_escribiendo(selector, monkeypatch):
    from app.ui import buscador_clientes
    monkeypatch.setattr(buscador_clientes, "MAX_SUGERENCIAS", 3)
    selector.buscador._al_enfocar()
    assert len(titulos(selector)) == 3
    assert "10 clientes" in selector.buscador.titulo and "acotar" in selector.buscador.titulo


def test_enter_o_buscar_siguen_cargando_las_mascotas_de_lo_escrito(selector):
    selector.busqueda.value = "paz"
    selector.buscar()
    assert sorted(o.text.split(" ")[0] for o in selector.lista.options) == ["Mimi", "Toby"]
    assert not selector.buscador.panel.visible


def test_limpiar_vacia_el_campo_la_lista_y_las_mascotas(selector):
    escribir(selector, "paz")
    tocar(selector, "Paz")
    selector.limpiar()
    assert selector.busqueda.value == "" and selector.lista.options == [] and not selector.buscador.panel.visible


def test_los_manejadores_no_reciben_el_evento(selector):
    for manejador in (selector.buscar, selector.buscador.sugerir, selector.buscador.cerrar,
                      selector.buscador._al_escribir, selector.buscador._al_enfocar):
        assert sin_parametros(manejador)

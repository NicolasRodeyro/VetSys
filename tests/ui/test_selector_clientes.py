"""Búsqueda de cliente en vivo: la lista se arma al tocar el campo y se acota al escribir."""

import pytest

from app.ui.buscador_clientes import MAXIMO_VISIBLE, BuscadorClientes
from app.ui.pantalla import Pantalla
from app.ui.selectores import SelectorMascota
from tests.ui.conftest import elegir_cliente_en_la_lista, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


class PantallaDeMentira(Pantalla):
    clave, titulo, icono, grupo = "x", "X", None, "X"

    def build(self):
        return None


@pytest.fixture
def pantalla(sesion_ui) -> PantallaDeMentira:
    return PantallaDeMentira(sesion_ui)


@pytest.fixture
def buscador(pantalla) -> BuscadorClientes:
    return BuscadorClientes(pantalla)


def test_al_tocar_el_campo_vacio_aparecen_todos_los_clientes(buscador):
    assert not buscador.abierta
    buscador.abrir()
    assert buscador.abierta and len(buscador.coincidencias) == 10
    assert buscador._resumen.value == "10 cliente(s)"


def test_al_escribir_la_lista_se_acota_por_dni_apellido_o_nombre(buscador):
    for texto in ("paz", "30111222", "ana"):
        buscador.campo.value = texto
        buscador.escribir()
        assert any(x.dni == "30111222" for x in buscador.coincidencias)
    buscador.campo.value = "zzz"
    buscador.escribir()
    assert buscador.coincidencias == [] and "No hay clientes que coincidan" in buscador._resumen.value


def test_cada_renglon_muestra_apellido_nombre_dni_y_mascotas(buscador):
    buscador.campo.value = "paz"
    buscador.escribir()
    titulo, detalle = buscador.textos_de_la_lista()[0]
    assert titulo.startswith("Paz,") and "DNI 30111222" in detalle
    assert "Toby" in detalle and "Mimi" in detalle


def test_tocar_un_cliente_lo_elige_y_cierra_la_lista(pantalla):
    elegidos = []
    buscador = BuscadorClientes(pantalla, al_elegir=elegidos.append)
    elegir_cliente_en_la_lista(buscador, "paz")
    assert buscador.cliente is elegidos[0] and buscador.cliente.dni == "30111222"
    assert not buscador.abierta and "30111222" in buscador.campo.value


def test_seguir_escribiendo_descarta_lo_elegido(pantalla):
    avisos = []
    buscador = BuscadorClientes(pantalla, al_escribir=lambda: avisos.append(1))
    elegir_cliente_en_la_lista(buscador, "paz")
    avisos.clear()
    buscador.campo.value = "pa"
    buscador.escribir()
    assert buscador.cliente is None and avisos == [1]


def test_la_lista_se_puede_cerrar(buscador):
    buscador.abrir()
    buscador.cerrar()
    assert not buscador.abierta


def test_enter_o_buscar_arman_la_lista_y_avisan(pantalla):
    avisos = []
    buscador = BuscadorClientes(pantalla, al_buscar=lambda: avisos.append(1))
    buscador.campo.value = "paz"
    buscador.buscar()
    assert buscador.abierta and len(buscador.coincidencias) == 1 and avisos == [1]


def test_se_muestran_como_maximo_30_clientes(buscador, monkeypatch):
    clientes = [type("C", (), dict(id=i, apellido=f"A{i}", nombre="N", dni=str(i), mascotas=[]))() for i in range(45)]
    monkeypatch.setattr(buscador, "buscar_ahora", lambda: clientes)
    buscador.abrir()
    assert len(buscador.coincidencias) == MAXIMO_VISIBLE
    assert "Mostrando 30 de 45" in buscador._resumen.value


def test_los_manejadores_no_reciben_el_evento(buscador):
    for manejador in (buscador.abrir, buscador.escribir, buscador.buscar, buscador.cerrar):
        assert sin_parametros(manejador)


# --- el selector de mascota que usan Turnos, Consultas, Comprobantes y Muestras ---

def test_un_cliente_con_dos_mascotas_las_ofrece(pantalla):
    selector = SelectorMascota(pantalla)
    elegir_cliente_en_la_lista(selector.buscador, "paz")
    assert sorted(o.text.split(" ")[0] for o in selector.lista.options) == ["Mimi", "Toby"]
    assert selector.mascota_id is None


def test_un_cliente_con_una_sola_mascota_la_deja_elegida(pantalla):
    selector = SelectorMascota(pantalla)
    for posicion, cliente in enumerate(selector.buscador.buscar_ahora()):
        if len([m for m in cliente.mascotas if m.activa]) == 1:
            selector.buscador.campo.value = cliente.dni
            selector.buscador.escribir()
            selector.buscador.elegir(cliente.id)
            break
    else:
        pytest.skip("el seed no tiene un cliente con una sola mascota")
    assert selector.mascota_id is not None


def test_seguir_escribiendo_descarta_la_mascota_elegida(pantalla):
    selector = SelectorMascota(pantalla)
    elegir_cliente_en_la_lista(selector.buscador, "paz")
    selector.lista.value = selector.lista.options[0].key
    selector.busqueda.value = "pazz"
    selector.buscador.escribir()
    assert selector.mascota_id is None and selector.lista.options == []


def test_enter_ofrece_las_mascotas_de_todos_los_que_coinciden(pantalla):
    selector = SelectorMascota(pantalla)
    selector.busqueda.value = "paz"
    selector.buscar()
    assert len(selector.lista.options) == 2


def test_limpiar_vacia_todo(pantalla):
    selector = SelectorMascota(pantalla)
    elegir_cliente_en_la_lista(selector.buscador, "paz")
    selector.limpiar()
    assert selector.busqueda.value == "" and selector.lista.options == [] and selector.buscador.cliente is None

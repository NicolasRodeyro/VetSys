import pytest

from app.servicios import clientes as svc
from app.ui.pantallas.clientes import PantallaClientes
from tests.ui.conftest import sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaClientes:
    pantalla = PantallaClientes(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


def completar(p, dni="40123456", nombre="Sofía", apellido="Ramírez", telefono="351 555-9999",
              email="sofia@mail.com", direccion="Calle 7"):
    p.dni.value, p.nombre.value, p.apellido.value = dni, nombre, apellido
    p.telefono.value, p.email.value, p.direccion.value = telefono, email, direccion


def test_la_pantalla_se_arma_y_lista_los_clientes_al_mostrarse(pantalla):
    assert pantalla.tabla.cantidad == 10


def test_buscar_filtra_la_tabla(pantalla):
    pantalla.busqueda.value = "paz"
    pantalla.buscar()
    assert pantalla.tabla.cantidad == 1
    pantalla.busqueda.value = "zzz"
    pantalla.buscar()
    assert pantalla.tabla.cantidad == 0


def test_la_tabla_se_filtra_mientras_se_escribe(pantalla):
    assert pantalla.busqueda.on_change is not None and sin_parametros(pantalla.busqueda.on_change)
    pantalla.busqueda.value = "paz"
    pantalla.busqueda.on_change()
    assert pantalla.tabla.cantidad == 1


def test_tildar_incluir_bajas_actualiza_la_tabla_al_instante(pantalla):
    assert pantalla.incluir_bajas.on_change is not None and sin_parametros(pantalla.incluir_bajas.on_change)


def test_los_clientes_de_baja_solo_aparecen_si_se_pide(pantalla):
    ana = svc.buscar_clientes("30111222")[0]
    for m in ana.mascotas:
        svc.dar_de_baja_mascota(m.id)
    svc.dar_de_baja_cliente(ana.id)

    pantalla.buscar()
    assert pantalla.tabla.cantidad == 9
    pantalla.incluir_bajas.value = True
    pantalla.buscar()
    assert pantalla.tabla.cantidad == 10


def test_elegir_un_cliente_llena_el_formulario(pantalla):
    ana = svc.buscar_clientes("30111222")[0]
    pantalla.elegir(ana.id)

    assert (pantalla.dni.value, pantalla.nombre.value, pantalla.apellido.value) == ("30111222", "Ana", "Paz")
    assert pantalla.telefono.value == "351-555-0101"
    assert "Paz, Ana" in pantalla.titulo_formulario.value
    assert pantalla.boton_baja.visible and not pantalla.boton_reactivar.visible


def test_el_boton_de_cada_fila_funciona_sin_recibir_el_evento(pantalla):
    boton = pantalla.tabla._tabla.rows[0].cells[-1].content  # el lápiz de la primera fila
    assert sin_parametros(boton.on_click)
    boton.on_click()  # como lo llama Flet
    assert pantalla.dni.value == "32999888"  # Castro, la primera fila


def test_los_botones_de_la_pantalla_no_reciben_el_evento(pantalla):
    for manejador in (pantalla.buscar, pantalla.guardar, pantalla.nuevo, pantalla.dar_de_baja, pantalla.reactivar):
        assert sin_parametros(manejador)


def test_dar_de_alta_un_cliente_nuevo(pantalla, mensajes):
    completar(pantalla)
    pantalla.guardar()

    assert mensajes.errores == [] and mensajes.exitos == ["Cliente guardado."]
    assert svc.buscar_clientes("40123456")[0].nombre == "Sofía"
    assert pantalla.tabla.cantidad == 11  # se recargó la lista
    assert "Ramírez, Sofía" in pantalla.titulo_formulario.value  # y quedó editando al nuevo


def test_un_dato_invalido_se_muestra_y_no_se_guarda_nada(pantalla, mensajes):
    completar(pantalla, dni="123", email="mal")
    pantalla.guardar()

    assert mensajes.exitos == []
    assert "DNI" in mensajes.errores[0]
    assert len(svc.buscar_clientes()) == 10


def test_un_dni_repetido_se_informa(pantalla, mensajes):
    completar(pantalla, dni="30111222")
    pantalla.guardar()
    assert "Ya existe un cliente con el DNI 30111222" in mensajes.errores[0]


def test_modificar_un_cliente_existente(pantalla, mensajes):
    ana = svc.buscar_clientes("30111222")[0]
    pantalla.elegir(ana.id)
    pantalla.telefono.value = "351 000-1111"
    pantalla.guardar()

    assert mensajes.errores == []
    assert svc.obtener_cliente(ana.id).telefono == "351 000-1111"
    assert len(svc.buscar_clientes()) == 10  # no se creó uno nuevo


def test_nuevo_limpia_el_formulario(pantalla):
    ana = svc.buscar_clientes("30111222")[0]
    pantalla.elegir(ana.id)
    pantalla.nuevo()

    assert (pantalla.dni.value, pantalla.nombre.value) == ("", "")
    assert pantalla.titulo_formulario.value == "Nuevo cliente"
    assert not pantalla.boton_baja.visible and not pantalla.boton_reactivar.visible


def test_la_baja_con_mascotas_activas_se_rechaza_y_se_le_explica_al_usuario(pantalla, mensajes):
    ana = svc.buscar_clientes("30111222")[0]
    pantalla.elegir(ana.id)
    pantalla.dar_de_baja()

    assert "mascotas activas" in mensajes.errores[0]
    assert svc.obtener_cliente(ana.id).activo


def test_baja_y_reactivacion_cambian_los_botones(pantalla, mensajes):
    marta = svc.buscar_clientes("33222111")[0]
    svc.dar_de_baja_mascota(marta.mascotas[0].id)
    pantalla.elegir(marta.id)

    pantalla.dar_de_baja()
    assert mensajes.exitos[-1] == "Cliente dado de baja."
    assert pantalla.boton_reactivar.visible and not pantalla.boton_baja.visible
    assert "DADO DE BAJA" in pantalla.estado.value

    pantalla.reactivar()
    assert mensajes.exitos[-1] == "Cliente reactivado."
    assert pantalla.boton_baja.visible and not pantalla.boton_reactivar.visible


def test_un_error_inesperado_no_rompe_la_ventana(pantalla, mensajes, monkeypatch):
    monkeypatch.setattr(svc, "buscar_clientes", lambda *a, **k: 1 / 0)
    pantalla.buscar()
    assert "Error inesperado" in mensajes.errores[0]

from datetime import datetime

import pytest

from app.servicios import consultas as svc, turnos
from app.ui.pantallas.consultas import PantallaConsultas
from tests.servicios.conftest import mascota, veterinario
from tests.ui.conftest import elegir, elegir_mascota, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def pantalla(sesion_ui) -> PantallaConsultas:
    pantalla = PantallaConsultas(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


def preparar(p, dni="paz", nombre="Toby", vet="MP-1001", tipo="CONSULTA"):
    elegir_mascota(p.selector, nombre, dni)
    p.veterinario.value = str(veterinario(vet).id)
    p._cargar_turnos()
    p.tipo.value = tipo


def test_ofrece_los_veterinarios_y_el_catalogo_de_analisis(pantalla):
    assert len(pantalla.veterinario.options) == 4
    assert len(pantalla.analisis.options) == 5
    assert "Hemograma · $ 12.500,00" in next(o.text for o in pantalla.analisis.options if o.key == "Hemograma")


def test_registrar_sin_mascota_o_sin_veterinario_se_explica(pantalla, mensajes):
    pantalla.registrar()
    assert "Elegí la mascota" in mensajes.errores[-1]
    elegir_mascota(pantalla.selector, "Toby", "paz")
    pantalla.registrar()
    assert "Elegí el veterinario" in mensajes.errores[-1]


def test_una_consulta_con_vacunas_pendientes_se_registra_y_se_avisa(pantalla, mensajes):
    preparar(pantalla, dni="rossi", nombre="Luna", tipo="CONTROL")  # gata de 4 meses sin vacunas
    pantalla.diagnostico.value = "Control de rutina"
    pantalla.registrar()

    assert mensajes.errores == [] and mensajes.exitos == []  # con advertencias solo se muestra el aviso
    titulo, lineas = mensajes.avisos[0]
    assert "vacunas pendientes" in titulo
    assert lineas == ["Vacuna pendiente: Triple felina", "Vacuna pendiente: Antirrabica", "Vacuna pendiente: Leucemia felina"]
    assert pantalla.tabla.cantidad == 1  # la consulta ya está registrada
    assert pantalla.detalle.visible and len(pantalla.advertencias.controls) == 3
    assert pantalla.diagnostico.value == ""  # el formulario quedó listo para otra


def test_una_consulta_sin_advertencias_solo_confirma(pantalla, mensajes):
    preparar(pantalla, dni="gómez", nombre="Rex")  # vacunado en abril
    pantalla.registrar()
    assert mensajes.exitos == ["Consulta registrada."] and mensajes.avisos == []


def test_una_urgencia_no_necesita_turno(pantalla, mensajes):
    preparar(pantalla, tipo="URGENCIA")
    pantalla.registrar()
    assert mensajes.errores == []
    assert svc.obtener_consulta(1).turno is None


def test_se_puede_atender_un_turno_reservado(pantalla, mensajes):
    toby, vet = mascota("30111222", "Toby"), veterinario("MP-1001")
    turnos.reservar_turno(vet.id, toby.id, datetime(2026, 11, 2, 12, 30), 30)
    preparar(pantalla, tipo="CONTROL")
    assert [o.text for o in pantalla.turno.options] == ["Sin turno", "02/11/2026 12:30"]

    elegir(pantalla.turno, "02/11/2026")
    pantalla.registrar()
    assert mensajes.errores == []
    assert svc.obtener_consulta(1).turno is not None


def test_emitir_una_orden_de_derivacion(pantalla, mensajes):
    preparar(pantalla, dni="gómez", nombre="Rex")
    pantalla.registrar()
    pantalla.emitir_orden()
    assert "Elegí el análisis" in mensajes.errores[-1]

    elegir(pantalla.analisis, "Hemograma")
    pantalla.prioridad.value = "URGENTE"
    pantalla.emitir_orden()

    assert mensajes.exitos[-1] == "Orden de derivación emitida."
    assert pantalla.tabla_ordenes.cantidad == 1
    assert svc.obtener_consulta(1).ordenes[0].prioridad.value == "URGENTE"


def test_guardar_cambios_del_diagnostico(pantalla, mensajes):
    preparar(pantalla, dni="gómez", nombre="Rex")
    pantalla.registrar()
    pantalla.diagnostico_detalle.value = "Gastroenteritis"
    pantalla.guardar_cambios()
    assert mensajes.exitos[-1] == "Consulta actualizada."
    assert svc.obtener_consulta(1).diagnostico == "Gastroenteritis"


def test_una_consulta_cerrada_no_se_puede_modificar_desde_la_pantalla(pantalla):
    preparar(pantalla, dni="gómez", nombre="Rex")
    pantalla.registrar()
    svc.cerrar_consulta(1, "3000")

    pantalla.elegir(1)

    assert "CERRADA" in pantalla.titulo_detalle.value
    assert not pantalla.boton_guardar.visible and not pantalla.formulario_orden.visible
    assert pantalla.diagnostico_detalle.disabled


def test_cambiar_de_mascota_oculta_el_detalle(pantalla):
    preparar(pantalla, dni="gómez", nombre="Rex")
    pantalla.registrar()
    assert pantalla.detalle.visible
    elegir_mascota(pantalla.selector, "Toby", "paz")
    assert not pantalla.detalle.visible and pantalla.tabla.cantidad == 0


def test_los_botones_no_reciben_el_evento(pantalla):
    for manejador in (pantalla.registrar, pantalla.guardar_cambios, pantalla.emitir_orden):
        assert sin_parametros(manejador)

"""Criterio de aceptación de la Fase 8: se puede recorrer el flujo completo desde la interfaz.

consulta -> orden -> muestra -> conservadora -> remito -> envío -> recepción -> resultado,
y el flujo de rechazo con re-extracción. Solo se usan las pantallas, como lo haría una persona.
"""

from decimal import Decimal

import pytest

from app.servicios import consultas as svc_consultas
from app.ui.pantallas.comprobantes import PantallaComprobantes
from app.ui.pantallas.conservadoras import PantallaConservadoras
from app.ui.pantallas.consultas import PantallaConsultas
from app.ui.pantallas.muestras import PantallaMuestras
from app.ui.pantallas.recepcion import PantallaRecepcion
from app.ui.pantallas.remitos import PantallaRemitos
from app.ui.pantallas.resultados import PantallaResultados
from app.ui.pantallas.turnos import PantallaTurnos
from tests.servicios.conftest import veterinario
from tests.ui.conftest import elegir, elegir_consulta, elegir_mascota

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


@pytest.fixture
def ui(sesion_ui):
    """Todas las pantallas, ya armadas, compartiendo la misma sesión (mensajero y operador)."""
    pantallas = {}
    for clase in (PantallaTurnos, PantallaConsultas, PantallaMuestras, PantallaConservadoras,
                  PantallaRemitos, PantallaRecepcion, PantallaResultados, PantallaComprobantes):
        pantallas[clase.clave] = clase(sesion_ui)
        pantallas[clase.clave].build()
        pantallas[clase.clave].al_mostrar()
    return pantallas


def enviar_por_pantallas(ui, codigo: str, precinto: str):
    """Conservadora -> empaquetar -> precintar -> remito -> cerrar -> despachar -> tramo -> recepción."""
    cons, rem, rec = ui["conservadoras"], ui["remitos"], ui["recepcion"]
    cons.al_mostrar()
    cons.codigo.value, cons.temp_min.value, cons.temp_max.value = codigo, "4", "6"
    cons.crear()
    elegir(cons.muestra, "#")
    cons.empaquetar()
    cons.numero_precinto.value = f"P-{codigo}"
    cons.precintar()

    rem.al_mostrar()
    rem.clinica.value, rem.laboratorio.value = rem.clinica.options[0].key, rem.laboratorio.options[0].key
    rem.crear()
    elegir(rem.libres, codigo)
    rem.agregar()
    rem.cerrar()
    rem.despachar()
    rem.origen.value, rem.destino.value, rem.transportista.value = "Clínica Centro", "Laboratorio", "Transportes Sur"
    rem.salida.value, rem.temperatura.value = "2026-11-02 12:30", "5,2"
    rem.registrar_tramo()

    rec.al_mostrar()
    rec.remito.value = rec.remito.options[0].key
    rec.elegir()
    rec._filas[0].temperatura.value = "5,2"
    rec._filas[0].precinto.value = precinto
    rec.registrar()


def test_el_flujo_completo_con_rechazo_y_re_extraccion_se_recorre_desde_la_interfaz(ui, mensajes):
    # 1. Turno y consulta de Toby: tiene vacunas pendientes -> se advierte, no se bloquea
    turnos, consultas = ui["turnos"], ui["consultas"]
    turnos.veterinario.value = str(veterinario("MP-1001").id)
    turnos.cargar_agenda()
    elegir_mascota(turnos.selector, "Toby", "paz")
    turnos.inicio.value = "2026-11-02 12:00"
    turnos.reservar()
    assert turnos.tabla.cantidad == 1

    elegir_mascota(consultas.selector, "Toby", "paz")
    consultas.veterinario.value = str(veterinario("MP-1001").id)
    consultas._cargar_turnos()
    elegir(consultas.turno, "02/11/2026")
    consultas.tipo.value = "CONTROL"
    consultas.diagnostico.value = "Control anual"
    consultas.registrar()
    titulo, advertencias = mensajes.avisos[0]
    assert "vacunas pendientes" in titulo and len(advertencias) == 2

    # 2. Orden de derivación
    elegir(consultas.analisis, "Hemograma")
    consultas.emitir_orden()
    assert consultas.tabla_ordenes.cantidad == 1

    # 3. Extracción de la muestra
    muestras = ui["muestras"]
    elegir_mascota(muestras.selector, "Toby", "paz")
    elegir_consulta(muestras.selector)
    muestras.selector.lista_ordenes.value = muestras.selector.lista_ordenes.options[0].key
    muestras.selector._orden_elegida()
    muestras.registrar_extraccion()
    primera = int(muestras.tabla._tabla.rows[0].cells[0].content.value)

    # 4. Primer envío: llega con el precinto roto -> se rechaza y se avisa a la clínica
    enviar_por_pantallas(ui, "C-1", "ROTO")
    titulo, alertas = mensajes.avisos[-1]
    assert "Rechazado" in titulo and "re-extracción" in alertas[0]

    # 5. Re-extracción sin cargo desde la pantalla de muestras
    muestras.filtro.value = "RECHAZADA"
    muestras.cargar()
    muestras.elegir(primera)
    assert muestras.boton_reextraer.visible
    muestras.re_extraer()
    segunda = int(muestras.titulo_detalle.value.split("#")[1].split(" ")[0])
    assert segunda != primera

    # 6. Segundo envío: llega bien
    enviar_por_pantallas(ui, "C-2", "INTACTO")
    assert "todas las muestras aceptadas" in mensajes.exitos[-1]

    # 7. Resultado: se avisa al responsable
    res = ui["resultados"]
    res.al_mostrar()
    res.muestra.value = res.muestra.options[0].key
    res.parametro.value, res.valor.value, res.unidad.value, res.ref_min.value, res.ref_max.value = "Hematocrito", "41", "%", "37", "55"
    res.agregar_valor()
    res.registrar()
    assert mensajes.avisos[-1] == ("Resultado registrado", ["Ana Paz: ya está el resultado de Hemograma"])

    # 8. Se cierra la consulta: un solo análisis cobrado
    comp = ui["comprobantes"]
    elegir_mascota(comp.selector, "Toby", "paz")
    elegir_consulta(comp.selector)
    comp.honorarios.value = "3000"
    comp.cerrar()
    assert "Total $ 15.500,00" in comp.total.value
    assert comp.tabla_items.cantidad == 2  # la consulta y UN análisis, aunque hubo dos extracciones

    assert mensajes.errores == []  # en todo el recorrido no hubo un solo error
    assert svc_consultas.obtener_consulta(1).comprobante.total == Decimal("15500.00")

from datetime import datetime
from decimal import Decimal

import pytest

from app.dominio.enums import Prioridad, TipoConsulta
from app.dominio.excepciones import ReglaNegocio
from app.servicios import clientes, consultas, turnos
from app.servicios.excepciones import EntradaInvalida, NoEncontrado
from tests.servicios.conftest import AHORA, mascota, veterinario

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


def _consulta(dni="30111222", nombre="Toby", matricula="MP-1001", tipo="CONSULTA", **extra):
    return consultas.registrar_consulta(mascota(dni, nombre).id, veterinario(matricula).id, tipo, **extra)


# --- Registrar consulta (con advertencias de vacunas) ---

def test_registrar_consulta_usa_la_hora_actual_por_defecto(cx):
    consulta = _consulta(diagnostico="  Control   de rutina ")
    assert consulta.id is not None and consulta.tipo is TipoConsulta.CONSULTA
    assert consulta.fecha_hora == AHORA
    assert consulta.diagnostico == "Control de rutina"


def test_una_consulta_con_vacunas_pendientes_se_registra_igual_pero_advierte(cx):
    # Luna (gata nacida el 01/07/2026) tiene 4 meses y ninguna vacuna aplicada.
    consulta = _consulta(dni="33222111", nombre="Luna")

    assert consulta.advertencias == (
        "Vacuna pendiente: Triple felina", "Vacuna pendiente: Antirrabica", "Vacuna pendiente: Leucemia felina")
    guardada = consultas.obtener_consulta(consulta.id)  # se registró y las advertencias quedaron guardadas
    assert guardada.advertencias == consulta.advertencias
    assert [c.id for c in consultas.listar_consultas_de_mascota(guardada.mascota.id)] == [consulta.id]


def test_una_mascota_con_las_vacunas_al_dia_no_genera_advertencias(cx):
    rex = mascota("28444555", "Rex")  # vacunado en abril de 2026
    assert consultas.registrar_consulta(rex.id, veterinario("MP-1001").id, "control").advertencias == ()


def test_una_urgencia_no_necesita_turno(cx):
    urgencia = _consulta(tipo="urgencia")
    assert urgencia.turno is None and urgencia.tipo is TipoConsulta.URGENCIA


def test_consulta_con_turno(cx):
    toby, vet = mascota("30111222", "Toby"), veterinario("MP-1001")
    turno = turnos.reservar_turno(vet.id, toby.id, datetime(2026, 11, 2, 12, 0), 30)
    consulta = consultas.registrar_consulta(toby.id, vet.id, "CONTROL", turno_id=turno.id)
    assert consulta.turno.id == turno.id


def test_un_turno_no_se_atiende_dos_veces(cx):
    toby, vet = mascota("30111222", "Toby"), veterinario("MP-1001")
    turno = turnos.reservar_turno(vet.id, toby.id, datetime(2026, 11, 2, 12, 0), 30)
    consultas.registrar_consulta(toby.id, vet.id, "CONTROL", turno_id=turno.id)
    with pytest.raises(ReglaNegocio, match="ya fue atendido"):
        consultas.registrar_consulta(toby.id, vet.id, "CONTROL", turno_id=turno.id)


def test_el_turno_tiene_que_ser_del_mismo_veterinario_y_de_la_misma_mascota(cx):
    toby, rex = mascota("30111222", "Toby"), mascota("28444555", "Rex")
    turno = turnos.reservar_turno(veterinario("MP-1001").id, toby.id, datetime(2026, 11, 2, 12, 0), 30)

    with pytest.raises(ReglaNegocio, match="otro veterinario"):
        consultas.registrar_consulta(toby.id, veterinario("MP-2001").id, "CONTROL", turno_id=turno.id)
    with pytest.raises(ReglaNegocio, match="otra mascota"):
        consultas.registrar_consulta(rex.id, veterinario("MP-1001").id, "CONTROL", turno_id=turno.id)


def test_no_se_atiende_a_una_mascota_dada_de_baja(cx):
    toby = mascota("30111222", "Toby")
    clientes.dar_de_baja_mascota(toby.id)
    with pytest.raises(ReglaNegocio, match="dada de baja"):
        consultas.registrar_consulta(toby.id, veterinario("MP-1001").id, "CONTROL")
    assert cx.execute("SELECT COUNT(*) FROM consultas").fetchone()[0] == 0


def test_registrar_consulta_con_datos_invalidos(cx):
    toby, vet = mascota("30111222", "Toby"), veterinario("MP-1001")
    with pytest.raises(EntradaInvalida, match="tipo de consulta"):
        consultas.registrar_consulta(toby.id, vet.id, "chequeo")
    with pytest.raises(EntradaInvalida, match="fecha y hora"):
        consultas.registrar_consulta(toby.id, vet.id, "CONTROL", fecha_hora="hoy")
    with pytest.raises(NoEncontrado, match="el veterinario"):
        consultas.registrar_consulta(toby.id, 9999, "CONTROL")


def test_actualizar_diagnostico_y_tratamiento(cx):
    consulta = _consulta()
    consultas.actualizar_consulta(consulta.id, diagnostico="Gastroenteritis", tratamiento="Dieta blanda")
    guardada = consultas.obtener_consulta(consulta.id)
    assert (guardada.diagnostico, guardada.tratamiento) == ("Gastroenteritis", "Dieta blanda")


# --- Órdenes de derivación ---

def test_emitir_ordenes_de_derivacion(cx):
    consulta = _consulta()
    urgente = consultas.emitir_orden(consulta.id, "Hemograma", "urgente")
    consultas.emitir_orden(consulta.id, "Urocultivo")

    assert urgente.id is not None and urgente.prioridad is Prioridad.URGENTE
    guardada = consultas.obtener_consulta(consulta.id)
    assert [(o.tipo_analisis.nombre, o.prioridad) for o in guardada.ordenes] == [
        ("Hemograma", Prioridad.URGENTE), ("Urocultivo", Prioridad.NORMAL)]


def test_emitir_una_orden_de_un_analisis_que_no_existe(cx):
    consulta = _consulta()
    with pytest.raises(NoEncontrado, match="el tipo de análisis"):
        consultas.emitir_orden(consulta.id, "Resonancia")
    assert consultas.obtener_consulta(consulta.id).ordenes == ()


# --- Cerrar la consulta y emitir el comprobante ---

def test_cerrar_la_consulta_emite_el_comprobante_con_la_consulta_y_cada_orden(cx):
    consulta = _consulta()
    consultas.emitir_orden(consulta.id, "Hemograma")  # 12500.00
    consultas.emitir_orden(consulta.id, "Urocultivo")  # 9800.50

    comprobante = consultas.cerrar_consulta(consulta.id, "3000,25")

    assert [(i.descripcion, i.monto, i.es_laboratorio) for i in comprobante.items] == [
        ("Consulta", Decimal("3000.25"), False), ("Hemograma", Decimal("12500.00"), True),
        ("Urocultivo", Decimal("9800.50"), True)]
    assert comprobante.total == Decimal("25300.75")  # Decimal exacto

    guardada = consultas.obtener_consulta(consulta.id)
    assert guardada.cerrada and guardada.comprobante.total == Decimal("25300.75")
    assert guardada.comprobante.fecha_hora == AHORA
    assert guardada.comprobante.cliente.dni == "30111222"


def test_una_consulta_cerrada_no_se_puede_modificar_ni_cerrar_de_nuevo(cx):
    consulta = _consulta()
    consultas.cerrar_consulta(consulta.id, 1000)

    with pytest.raises(ReglaNegocio, match="ya está cerrada"):
        consultas.cerrar_consulta(consulta.id, 1000)
    with pytest.raises(ReglaNegocio, match="no admite nuevas órdenes"):
        consultas.emitir_orden(consulta.id, "Hemograma")
    with pytest.raises(ReglaNegocio, match="no se puede modificar"):
        consultas.actualizar_consulta(consulta.id, diagnostico="otro")
    assert cx.execute("SELECT COUNT(*) FROM comprobantes").fetchone()[0] == 1


@pytest.mark.parametrize("honorarios, mensaje", [("-5", "negativo"), ("abc", "importe"), ("10.123", "2 decimales")])
def test_cerrar_con_honorarios_invalidos_deja_la_consulta_abierta(cx, honorarios, mensaje):
    consulta = _consulta()
    with pytest.raises(EntradaInvalida, match=mensaje):
        consultas.cerrar_consulta(consulta.id, honorarios)
    assert not consultas.obtener_consulta(consulta.id).cerrada


def test_cerrar_una_consulta_que_no_existe(cx):
    with pytest.raises(NoEncontrado, match="la consulta"):
        consultas.cerrar_consulta(9999, 1000)

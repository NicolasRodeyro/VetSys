from datetime import datetime

import pytest

from app.dominio.excepciones import ReglaNegocio
from app.servicios import clientes, consultas, turnos
from app.servicios.excepciones import EntradaInvalida, NoEncontrado
from tests.servicios.conftest import mascota, veterinario

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")

LUNES_10 = datetime(2026, 11, 9, 10, 0)


def turnos_en_la_base(cx) -> int:
    return cx.execute("SELECT COUNT(*) FROM turnos").fetchone()[0]


def test_reservar_un_turno(cx):
    vet, toby = veterinario("MP-1001"), mascota("30111222", "Toby")
    turno = turnos.reservar_turno(vet.id, toby.id, LUNES_10, 30)

    assert turno.id is not None and turno.fin == datetime(2026, 11, 9, 10, 30)
    (guardado,) = turnos.listar_turnos(vet.id)
    assert guardado.mascota.nombre == "Toby" and guardado.inicio == LUNES_10


def test_no_se_pueden_superponer_turnos_del_mismo_veterinario(cx):
    vet, toby, rex = veterinario("MP-1001"), mascota("30111222", "Toby"), mascota("28444555", "Rex")
    turnos.reservar_turno(vet.id, toby.id, LUNES_10, 30)

    with pytest.raises(ReglaNegocio, match="se superpone"):
        turnos.reservar_turno(vet.id, rex.id, datetime(2026, 11, 9, 10, 15), 30)

    assert turnos_en_la_base(cx) == 1  # el rechazado no quedó guardado
    turnos.reservar_turno(vet.id, rex.id, datetime(2026, 11, 9, 10, 30), 30)  # contiguo: ok
    assert len(turnos.listar_turnos(vet.id)) == 2


def test_la_superposicion_se_detecta_aunque_los_turnos_se_hayan_cargado_en_otra_sesion(cx):
    # Cada llamada a un servicio es una sesión nueva: la agenda tiene que volver completa de la base.
    vet, toby = veterinario("MP-1001"), mascota("30111222", "Toby")
    turnos.reservar_turno(vet.id, toby.id, LUNES_10, 60)
    with pytest.raises(ReglaNegocio, match="se superpone"):
        turnos.reservar_turno(vet.id, toby.id, datetime(2026, 11, 9, 10, 30), 15)


def test_dos_veterinarios_pueden_atender_a_la_misma_hora(cx):
    toby, rex = mascota("30111222", "Toby"), mascota("28444555", "Rex")
    turnos.reservar_turno(veterinario("MP-1001").id, toby.id, LUNES_10, 30)
    turnos.reservar_turno(veterinario("MP-1002").id, rex.id, LUNES_10, 30)


def test_cancelar_un_turno_libera_el_horario(cx):
    vet, toby, rex = veterinario("MP-1001"), mascota("30111222", "Toby"), mascota("28444555", "Rex")
    turno = turnos.reservar_turno(vet.id, toby.id, LUNES_10, 30)

    cancelado = turnos.cancelar_turno(turno.id)

    assert cancelado.estado.value == "CANCELADO"
    assert turnos.listar_turnos(vet.id) == []  # no aparece en la agenda...
    assert len(turnos.listar_turnos(vet.id, incluir_cancelados=True)) == 1  # ...pero no se borró
    turnos.reservar_turno(vet.id, rex.id, LUNES_10, 30)  # el horario quedó libre


def test_no_se_cancela_un_turno_que_ya_fue_atendido(cx):
    vet, toby = veterinario("MP-1001"), mascota("30111222", "Toby")
    turno = turnos.reservar_turno(vet.id, toby.id, LUNES_10, 30)
    consultas.registrar_consulta(toby.id, vet.id, "CONTROL", turno_id=turno.id)

    with pytest.raises(ReglaNegocio, match="ya fue atendido"):
        turnos.cancelar_turno(turno.id)
    assert turnos.listar_turnos(vet.id)[0].estado.value == "PROGRAMADO"


def test_cancelar_un_turno_que_no_existe(cx):
    with pytest.raises(NoEncontrado, match="el turno"):
        turnos.cancelar_turno(9999)


def test_no_se_reservan_turnos_para_una_mascota_dada_de_baja(cx):
    vet, toby = veterinario("MP-1001"), mascota("30111222", "Toby")
    clientes.dar_de_baja_mascota(toby.id)
    with pytest.raises(ReglaNegocio, match="dada de baja"):
        turnos.reservar_turno(vet.id, toby.id, LUNES_10, 30)
    assert turnos_en_la_base(cx) == 0


@pytest.mark.parametrize("inicio, duracion, mensaje", [
    ("2026-11-09 10:00", 30, "fecha y hora"),
    (LUNES_10, 0, "mayor a cero"),
    (LUNES_10, "abc", "número entero"),
])
def test_reservar_con_datos_invalidos(cx, inicio, duracion, mensaje):
    vet, toby = veterinario("MP-1001"), mascota("30111222", "Toby")
    with pytest.raises(EntradaInvalida, match=mensaje):
        turnos.reservar_turno(vet.id, toby.id, inicio, duracion)


def test_reservar_con_ids_que_no_existen(cx):
    toby = mascota("30111222", "Toby")
    with pytest.raises(NoEncontrado, match="el veterinario"):
        turnos.reservar_turno(9999, toby.id, LUNES_10, 30)
    with pytest.raises(NoEncontrado, match="la mascota"):
        turnos.reservar_turno(veterinario("MP-1001").id, 9999, LUNES_10, 30)


def test_la_agenda_sale_ordenada_por_fecha(cx):
    vet, toby = veterinario("MP-1001"), mascota("30111222", "Toby")
    for hora in (14, 9, 11):
        turnos.reservar_turno(vet.id, toby.id, datetime(2026, 11, 9, hora, 0), 30)
    assert [t.inicio.hour for t in turnos.listar_turnos(vet.id)] == [9, 11, 14]

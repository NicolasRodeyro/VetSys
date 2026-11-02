from datetime import datetime

import pytest

from app.dominio.enums import EstadoTurno
from app.dominio.excepciones import ReglaNegocio
from app.dominio.turno import Turno
from app.dominio.veterinario import Veterinario


def turno_a_las(hora: int, minuto: int, duracion: int, mascota) -> Turno:
    return Turno(datetime(2026, 6, 1, hora, minuto), duracion, mascota)


# --- Turno ---

def test_turno_calcula_su_fin(perro):
    assert turno_a_las(10, 0, 30, perro).fin == datetime(2026, 6, 1, 10, 30)


def test_turno_con_duracion_cero_o_negativa_falla(perro):
    with pytest.raises(ReglaNegocio):
        turno_a_las(10, 0, 0, perro)
    with pytest.raises(ReglaNegocio):
        turno_a_las(10, 0, -15, perro)


def test_turnos_contiguos_no_se_superponen(perro):
    primero = turno_a_las(10, 0, 30, perro)
    segundo = turno_a_las(10, 30, 30, perro)
    assert not primero.se_superpone_con(segundo)
    assert not segundo.se_superpone_con(primero)


@pytest.mark.parametrize(
    "hora, minuto, duracion",
    [
        (10, 0, 30),   # mismo horario
        (10, 15, 30),  # empieza en la mitad del otro
        (9, 45, 30),   # termina en la mitad del otro
        (10, 5, 10),   # queda adentro del otro
        (9, 0, 120),   # contiene al otro
    ],
)
def test_turnos_superpuestos_se_detectan(perro, hora, minuto, duracion):
    existente = turno_a_las(10, 0, 30, perro)
    nuevo = turno_a_las(hora, minuto, duracion, perro)
    assert nuevo.se_superpone_con(existente)
    assert existente.se_superpone_con(nuevo)


# --- Agenda del veterinario ---

def test_agenda_acepta_turnos_contiguos(veterinario, perro):
    veterinario.agregar_turno(turno_a_las(10, 0, 30, perro))
    veterinario.agregar_turno(turno_a_las(10, 30, 30, perro))
    assert len(veterinario.turnos) == 2


def test_agenda_rechaza_turno_superpuesto(veterinario, perro):
    veterinario.agregar_turno(turno_a_las(10, 0, 30, perro))
    with pytest.raises(ReglaNegocio, match="se superpone"):
        veterinario.agregar_turno(turno_a_las(10, 15, 30, perro))
    assert len(veterinario.turnos) == 1  # el rechazado no quedó en la agenda


def test_agenda_ignora_turnos_cancelados(veterinario, perro):
    cancelado = turno_a_las(10, 0, 30, perro)
    veterinario.agregar_turno(cancelado)
    cancelado.cancelar()
    assert cancelado.estado is EstadoTurno.CANCELADO

    # El horario quedó libre: se puede reservar de nuevo.
    veterinario.agregar_turno(turno_a_las(10, 0, 30, perro))
    assert len(veterinario.turnos) == 2


def test_cada_veterinario_tiene_su_propia_agenda(veterinario, clinica, perro):
    otro = Veterinario("MP-5678", "Marcos", "Ruiz", clinica)
    veterinario.agregar_turno(turno_a_las(10, 0, 30, perro))
    otro.agregar_turno(turno_a_las(10, 0, 30, perro))  # mismo horario, otro veterinario
    assert len(otro.turnos) == 1


def test_lista_de_turnos_no_se_modifica_desde_afuera(veterinario, perro):
    veterinario.agregar_turno(turno_a_las(10, 0, 30, perro))
    with pytest.raises(AttributeError):
        veterinario.turnos.append("x")  # es una tupla

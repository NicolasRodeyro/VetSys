"""Casos de uso: agenda de turnos (la regla de no superposición vive en Veterinario)."""

from __future__ import annotations

from datetime import datetime

from app.dominio.excepciones import ReglaNegocio
from app.dominio.turno import Turno
from app.servicios import validaciones as v
from app.servicios._comun import caso_de_uso, requerir


def reservar_turno(veterinario_id: int, mascota_id: int, inicio: datetime, duracion_minutos: int) -> Turno:
    inicio = v.fecha_hora(inicio, "El inicio del turno")
    duracion_minutos = v.entero_positivo(duracion_minutos, "La duración")
    with caso_de_uso() as ctx:
        # Hace falta la agenda completa para detectar superposiciones: obtener() la carga.
        veterinario = requerir(ctx.veterinarios.obtener(veterinario_id), "el veterinario", veterinario_id)
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        if not mascota.activa:
            raise ReglaNegocio(f"{mascota.nombre} está dada de baja: no se le pueden reservar turnos")
        turno = Turno(inicio, duracion_minutos, mascota)
        veterinario.agregar_turno(turno)  # lanza ReglaNegocio si se superpone con otro
        ctx.veterinarios.guardar(veterinario)
    return turno


def cancelar_turno(turno_id: int) -> Turno:
    with caso_de_uso() as ctx:
        veterinario = requerir(ctx.veterinarios.de_turno(turno_id), "el turno", turno_id)
        turno = ctx.veterinarios.turno_por_id(turno_id)
        if ctx.consultas.turno_tiene_consulta(turno):
            raise ReglaNegocio("El turno ya fue atendido: no se puede cancelar")
        turno.cancelar()
        ctx.veterinarios.guardar(veterinario)
    return turno


def listar_turnos(veterinario_id: int, incluir_cancelados: bool = False) -> list[Turno]:
    """Agenda de un veterinario, ordenada por fecha."""
    with caso_de_uso() as ctx:
        veterinario = requerir(ctx.veterinarios.obtener(veterinario_id), "el veterinario", veterinario_id)
        turnos = [t for t in veterinario.turnos if incluir_cancelados or t.estado.value != "CANCELADO"]
    return sorted(turnos, key=lambda turno: turno.inicio)

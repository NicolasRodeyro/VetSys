"""Reporte: vacunas pendientes de cada mascota, con los días de atraso y los datos de contacto.

Qué calcula (no está guardado en ninguna tabla):
- Qué vacunas del esquema de su especie le faltan a cada mascota a la fecha de corte, y desde cuándo.
- Los días de atraso: fecha de corte - fecha en que la vacuna venció.

Reutiliza el dominio: `HistoriaClinica.vacunas_pendientes_con_vencimiento()`, así la regla de qué está
pendiente sigue en un solo lugar (la misma que usa el aviso al registrar una consulta). Solo se
consideran las mascotas activas de clientes activos.

Filtros: la fecha de corte es el «Hasta» (el «Desde» no se usa, porque lo más urgente son justamente
las vacunas más atrasadas). Con una clínica elegida, solo las mascotas atendidas en esa clínica
(tienen al menos una consulta con un veterinario de ella, hasta la fecha de corte).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from app.dominio.mascota import Mascota
from app.persistencia.conexion import transaccion
from app.persistencia.contexto import Contexto
from app.reportes import formato
from app.reportes.filtros import FiltroReporte
from app.reportes.resultado import Grafico, ResultadoReporte

TITULO = "Vacunas pendientes y días de atraso"
DESCRIPCION = ("Mascotas activas con vacunas sin aplicar o con el refuerzo vencido a la fecha «Hasta» (el «Desde» no se usa). "
               "Con una clínica elegida, solo las mascotas atendidas en ella.")

# (nombre del tramo, atraso mínimo, atraso máximo); None = sin tope
TRAMOS = [("0 a 30 días", 0, 30), ("31 a 90 días", 31, 90), ("91 a 180 días", 91, 180), ("Más de 180 días", 181, None)]


@dataclass(frozen=True)
class Pendiente:
    mascota: str
    especie: str
    vacuna: str
    vencimiento: date
    atraso: int  # días entre el vencimiento y la fecha de corte
    responsable: str
    telefono: str
    email: str


# ---------------------------------------------------------------- lectura (dominio)

def _atendida_en(mascota: Mascota, clinica_id: int, corte: date) -> bool:
    return any(c.veterinario.clinica.id == clinica_id and c.fecha_hora.date() <= corte
               for c in mascota.historia_clinica.consultas)


def _leer(conexion: sqlite3.Connection, corte: date, clinica_id: int | None) -> list[Pendiente]:
    pendientes: list[Pendiente] = []
    for cliente in Contexto(conexion).clientes.listar():
        if not cliente.activo:
            continue
        for mascota in cliente.mascotas:
            # A una mascota que todavía no había nacido en la fecha de corte no se le calcula nada.
            if not mascota.activa or mascota.fecha_nacimiento > corte:
                continue
            if clinica_id is not None and not _atendida_en(mascota, clinica_id, corte):
                continue
            for vacuna, vencimiento in mascota.historia_clinica.vacunas_pendientes_con_vencimiento(corte):
                pendientes.append(Pendiente(
                    mascota.nombre, mascota.especie.nombre, vacuna.nombre, vencimiento, (corte - vencimiento).days,
                    f"{cliente.apellido}, {cliente.nombre}", cliente.telefono, cliente.email))
    return pendientes


# ---------------------------------------------------------------- cálculo (Python puro)

def ordenar(pendientes: list[Pendiente]) -> list[Pendiente]:
    """El mayor atraso primero (es lo más urgente de avisar); a igual atraso, por mascota y vacuna."""
    return sorted(pendientes, key=lambda p: (-p.atraso, p.mascota, p.vacuna))


def distribucion(pendientes: list[Pendiente]) -> list[int]:
    """Cuántas vacunas hay en cada tramo de TRAMOS, según sus días de atraso."""
    return [sum(1 for p in pendientes if minimo <= p.atraso and (maximo is None or p.atraso <= maximo))
            for _, minimo, maximo in TRAMOS]


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Mascota", "Especie", "Vacuna", "Venció el", "Días de atraso", "Responsable", "Teléfono", "Email"]


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    corte = filtro.hasta
    with transaccion() as conexion:
        pendientes = ordenar(_leer(conexion, corte, filtro.clinica_id))

    filas = [[p.mascota, p.especie, p.vacuna, f"{p.vencimiento:%d/%m/%Y}", str(p.atraso), p.responsable,
              p.telefono or formato.SIN_DATO, p.email or formato.SIN_DATO] for p in pendientes]
    mascotas = len({(p.mascota, p.responsable) for p in pendientes})
    notas = [f"Fecha de corte: {corte:%d/%m/%Y}. {mascotas} mascota(s) con {len(pendientes)} vacuna(s) pendiente(s)."
             if pendientes else f"Ninguna mascota tiene vacunas pendientes al {corte:%d/%m/%Y}."]
    grafico = Grafico("Vacunas pendientes según los días de atraso", [nombre for nombre, _, _ in TRAMOS],
                      {"Vacunas pendientes": [float(n) for n in distribucion(pendientes)]}, "Cantidad") if pendientes else None
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico)

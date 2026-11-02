"""Piezas comunes a los casos de uso (de uso interno de la capa de servicios)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TypeVar

from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.remito_biologico import RemitoBiologico
from app.persistencia.conexion import transaccion
from app.persistencia.contexto import Contexto
from app.servicios.excepciones import NoEncontrado

T = TypeVar("T")


@contextmanager
def caso_de_uso() -> Iterator[Contexto]:
    """Un caso de uso = una transacción: si algo falla, no queda nada a medias."""
    with transaccion() as conexion:
        yield Contexto(conexion)


def requerir(objeto: T | None, que: str, id_) -> T:
    if objeto is None:
        raise NoEncontrado(f"No existe {que} ({id_})")
    return objeto


def suscribir_trazabilidad(*muestras: Muestra) -> None:
    """Los observadores no se persisten: al cargar una muestra hay que suscribir
    RegistroTrazabilidad antes de cambiarle el estado (CLAUDE.md §4.4)."""
    for muestra in muestras:
        muestra.suscribir(RegistroTrazabilidad())


def muestras_de(remito: RemitoBiologico) -> list[Muestra]:
    return [m for conservadora in remito.conservadoras for m in conservadora.muestras]


def guardar_muestras(ctx: Contexto, muestras: list[Muestra]) -> None:
    """Guarda las muestras a través de sus órdenes (cada orden guarda sus muestras)."""
    ordenes = {id(m.orden): m.orden for m in muestras}
    for orden in ordenes.values():
        ctx.ordenes.guardar(orden)

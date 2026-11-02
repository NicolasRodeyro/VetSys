"""Mapeo entre el texto que se guarda en la base y las clases de estado (State).

Es el único lugar que sabe qué texto corresponde a qué clase, uno por cada State
(CLAUDE.md §6). Para guardar se usa `estado.nombre`; para reconstruir, estas funciones.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.dominio.enums import MotivoRechazo
from app.dominio.estados_muestra import (
    Analizada,
    Empaquetada,
    EnTransito,
    EstadoMuestra,
    Extraida,
    Rechazada,
    Recibida,
)
from app.dominio.estados_remito import (
    Abierto,
    Cerrado,
    EstadoRemito,
    Recibido,
    RecibidoParcial,
    Rechazado,
)
from app.dominio.estados_remito import EnTransito as RemitoEnTransito

# Cada fábrica recibe los motivos de rechazo; solo Rechazada los usa.
_ESTADOS_MUESTRA = {
    Extraida.nombre: lambda motivos: Extraida(),
    Empaquetada.nombre: lambda motivos: Empaquetada(),
    EnTransito.nombre: lambda motivos: EnTransito(),
    Recibida.nombre: lambda motivos: Recibida(),
    Analizada.nombre: lambda motivos: Analizada(),
    Rechazada.nombre: lambda motivos: Rechazada(motivos),
}

_ESTADOS_REMITO = {
    clase.nombre: clase
    for clase in (Abierto, Cerrado, RemitoEnTransito, Recibido, RecibidoParcial, Rechazado)
}


def estado_de_muestra(nombre: str, motivos: Iterable[MotivoRechazo] = ()) -> EstadoMuestra:
    try:
        return _ESTADOS_MUESTRA[nombre](motivos)
    except KeyError:
        raise ValueError(f"Estado de muestra desconocido en la base: {nombre!r}") from None


def estado_de_remito(nombre: str) -> EstadoRemito:
    try:
        return _ESTADOS_REMITO[nombre]()
    except KeyError:
        raise ValueError(f"Estado de remito desconocido en la base: {nombre!r}") from None

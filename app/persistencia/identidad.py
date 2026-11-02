"""Mapa de identidad: qué objeto del dominio corresponde a qué fila.

El dominio no conoce los ids de la base (CLAUDE.md §3), así que los repositorios
llevan este mapa. Sirve para dos cosas:
  * saber si un objeto ya está guardado (UPDATE) o es nuevo (INSERT);
  * que cargar dos veces la misma fila devuelva **el mismo objeto**, no dos copias.

Hay un mapa por contexto (ver contexto.py), es decir, por caso de uso.
"""

from __future__ import annotations

from typing import Any


class ObjetoNoGuardado(Exception):
    """Se pidió el id de un objeto que todavía no se guardó en la base."""


class HistorialIncompleto(Exception):
    """El historial de una muestra no llega hasta su estado actual.

    Pasa si se cambió de estado sin tener suscripto un RegistroTrazabilidad. Se avisa
    al guardar (o al cargar) para no dejar en la base una trazabilidad con huecos.
    """


class MapaIdentidad:
    def __init__(self) -> None:
        self._objetos: dict[tuple[str, int], Any] = {}
        self._ids: dict[tuple[str, int], int] = {}

    def registrar(self, tipo: str, id_: int, objeto: Any) -> None:
        # Se guarda el objeto en _objetos, así sigue vivo y su id() no se reutiliza.
        self._objetos[(tipo, id_)] = objeto
        self._ids[(tipo, id(objeto))] = id_
        if hasattr(objeto, "id"):
            # Las entidades tienen un atributo `id` (None hasta que se guardan) para que la
            # interfaz pueda referirse a ellas. El dominio no lo usa en ninguna regla.
            objeto.id = id_

    def obtener(self, tipo: str, id_: int) -> Any | None:
        return self._objetos.get((tipo, id_))

    def id_de(self, tipo: str, objeto: Any) -> int | None:
        return self._ids.get((tipo, id(objeto)))

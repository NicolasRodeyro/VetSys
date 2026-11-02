"""Clase base de las pantallas."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any

import flet as ft

from app.servicios.excepciones import ReglaNegocio
from app.ui.sesion import Sesion

registro = logging.getLogger(__name__)


def manejador(metodo: Callable[..., Any]) -> Callable[..., Any]:
    """Marca un método que atiende un evento de la interfaz (un clic, una selección...).

    Garantiza que al terminar la ventana se redibuje. Hace falta porque Flet solo actualiza
    solo al final de un evento si durante él NO se llamó a `update()`, y mostrar un mensaje
    lo hace internamente: los cambios posteriores al mensaje quedarían sin dibujar.
    (`wraps` conserva la firma: Flet decide si pasarle el evento según sus parámetros.)
    """

    @wraps(metodo)
    def envuelto(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return metodo(self, *args, **kwargs)
        finally:
            sesion = getattr(self, "sesion", None) or self._pantalla.sesion
            sesion.actualizar()

    return envuelto


class Pantalla:
    """Cada pantalla es una clase que guarda sus controles y arma su vista en `build()`.

    `ejecutar()` es el único lugar donde se atrapan los errores: los de regla de negocio
    (incluidas las entradas inválidas y las transiciones no permitidas) se le muestran al
    usuario con el mensaje del propio error; cualquier otro es un defecto y se registra.
    """

    clave = ""
    titulo = ""
    icono = ft.Icons.CIRCLE_OUTLINED
    grupo = ""

    def __init__(self, sesion: Sesion) -> None:
        self.sesion = sesion

    def build(self) -> ft.Control:
        raise NotImplementedError

    def al_mostrar(self) -> None:
        """Se llama cada vez que se navega a la pantalla: refresca las listas con la base."""

    def ejecutar(self, accion: Callable[[], object], ok: str | None = None) -> bool:
        """Corre `accion`; True si salió bien. Si falla, avisa al usuario y devuelve False."""
        try:
            accion()
        except ReglaNegocio as error:
            self.sesion.mensajero.error(str(error))
            return False
        except Exception as error:  # un defecto del programa, no del usuario
            registro.exception("Error inesperado en la pantalla %s", self.clave)
            self.sesion.mensajero.error(f"Error inesperado: {error}")
            return False
        if ok:
            self.sesion.mensajero.exito(ok)
        return True

    def avisar(self, titulo: str, lineas: Iterable[str]) -> None:
        lineas = list(lineas)
        if lineas:
            self.sesion.mensajero.aviso(titulo, lineas)

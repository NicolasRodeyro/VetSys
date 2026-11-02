"""Lo que comparten todas las pantallas durante el uso de la aplicación."""

from __future__ import annotations

from collections.abc import Callable

from app.servicios import validaciones as v
from app.servicios.excepciones import EntradaInvalida
from app.ui.mensajero import Mensajero


class Sesion:
    """El mensajero para hablarle al usuario y el *operador*: la persona que está usando el
    sistema, que se registra como responsable de cada operación (extracción, despacho...)."""

    def __init__(self, mensajero: Mensajero, leer_operador: Callable[[], str | None],
                 actualizar: Callable[[], None] = lambda: None) -> None:
        self.mensajero = mensajero
        self._leer_operador = leer_operador
        self._actualizar = actualizar

    def actualizar(self) -> None:
        """Redibuja la ventana (en los tests no hace nada)."""
        self._actualizar()

    def operador(self) -> str:
        try:
            return v.texto_obligatorio(self._leer_operador(), "El operador", 80)
        except EntradaInvalida:
            raise EntradaInvalida(
                "Indicá quién opera el sistema en el campo «Operador» (arriba a la derecha): "
                "queda registrado como responsable.") from None

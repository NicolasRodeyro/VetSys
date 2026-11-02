"""Errores de la capa de servicios.

Heredan de ReglaNegocio, así la interfaz puede atrapar todo con un solo
`except ReglaNegocio` y mostrar el mensaje al usuario.
"""

from app.dominio.excepciones import ReglaNegocio


class EntradaInvalida(ReglaNegocio):
    """Un dato que ingresó el usuario no es válido (vacío, mal formado, fuera de rango...)."""


class NoEncontrado(ReglaNegocio):
    """No existe lo que se pidió (por id, DNI, código...)."""

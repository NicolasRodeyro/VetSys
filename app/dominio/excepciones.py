"""Excepciones propias del dominio.

La capa web las atrapa y las muestra como mensajes al usuario.
"""


class ReglaNegocio(Exception):
    """Se violó una regla de negocio (ej. turno superpuesto, conservadora llena)."""


class TransicionInvalida(ReglaNegocio):
    """Se pidió una operación que el estado actual no permite (patrón State).

    Hereda de ReglaNegocio porque también es una regla de negocio violada:
    así quien quiera puede atrapar las dos con un solo `except ReglaNegocio`.
    """

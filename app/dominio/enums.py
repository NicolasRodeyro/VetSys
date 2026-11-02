"""Enumeraciones del dominio.

Se usa enum cuando el valor es solo una etiqueta, sin datos ni reglas propias
(CLAUDE.md §4.6). El valor en texto es el que se guarda en la base.
"""

from enum import Enum


class Sexo(Enum):
    MACHO = "MACHO"
    HEMBRA = "HEMBRA"


class TipoConsulta(Enum):
    CONTROL = "CONTROL"
    CONSULTA = "CONSULTA"
    URGENCIA = "URGENCIA"


class EstadoTurno(Enum):
    PROGRAMADO = "PROGRAMADO"
    CANCELADO = "CANCELADO"


class Prioridad(Enum):
    NORMAL = "NORMAL"
    URGENTE = "URGENTE"


class MotivoRechazo(Enum):
    PRECINTO_ROTO = "PRECINTO_ROTO"
    TEMPERATURA_FUERA_DE_RANGO = "TEMPERATURA_FUERA_DE_RANGO"


class EstadoPrecinto(Enum):
    """Estado en que el laboratorio encuentra el precinto al recibir la conservadora."""

    INTACTO = "INTACTO"
    ROTO = "ROTO"

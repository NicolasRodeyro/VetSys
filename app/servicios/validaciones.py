"""Sanitización de entradas: valida y normaliza lo que llega de la interfaz.

Todo dato que ingresa el usuario pasa por acá antes de llegar al dominio. Se limpia
(espacios de más, formatos), se valida (obligatorio, longitud, formato, rango) y, si
no sirve, se lanza EntradaInvalida con un mensaje que se le puede mostrar tal cual.

(La otra mitad de la defensa, contra la inyección de SQL, está en la persistencia: el
SQL siempre es parametrizado y los datos nunca se concatenan en la consulta.)
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import TypeVar

from app.servicios.excepciones import EntradaInvalida

E = TypeVar("E", bound=Enum)


def _limpiar(valor) -> str:
    """Pasa a texto y deja un solo espacio entre palabras."""
    return " ".join(str(valor if valor is not None else "").split())


def texto_obligatorio(valor, campo: str, maximo: int = 100) -> str:
    texto = _limpiar(valor)
    if not texto:
        raise EntradaInvalida(f"{campo} es obligatorio")
    if len(texto) > maximo:
        raise EntradaInvalida(f"{campo} no puede superar los {maximo} caracteres")
    return texto


def texto_opcional(valor, campo: str, maximo: int = 200) -> str:
    texto = _limpiar(valor)
    if len(texto) > maximo:
        raise EntradaInvalida(f"{campo} no puede superar los {maximo} caracteres")
    return texto


def dni(valor) -> str:
    """Acepta '30.111.222', '30 111 222' o '30111222' y devuelve solo los dígitos."""
    texto = re.sub(r"[.\s-]", "", str(valor if valor is not None else ""))
    if not re.fullmatch(r"\d{7,8}", texto):
        raise EntradaInvalida("El DNI debe tener 7 u 8 dígitos")
    return texto


def email_opcional(valor) -> str:
    texto = _limpiar(valor).lower()
    if texto and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", texto):
        raise EntradaInvalida("El email no es válido")
    return texto


def telefono_opcional(valor) -> str:
    texto = _limpiar(valor)
    if texto:
        digitos = re.sub(r"\D", "", texto)
        if not re.fullmatch(r"[\d\s+()\-]+", texto) or not 6 <= len(digitos) <= 15:
            raise EntradaInvalida("El teléfono no es válido")
    return texto


def fecha(valor, campo: str) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if not isinstance(valor, date):
        raise EntradaInvalida(f"{campo} no es una fecha válida")
    return valor


def fecha_no_futura(valor, campo: str, hoy: date) -> date:
    resultado = fecha(valor, campo)
    if resultado > hoy:
        raise EntradaInvalida(f"{campo} no puede ser futura")
    return resultado


def fecha_hora(valor, campo: str) -> datetime:
    if not isinstance(valor, datetime):
        raise EntradaInvalida(f"{campo} no es una fecha y hora válida")
    return valor


def numero(valor, campo: str) -> float:
    """Número con decimales; acepta coma o punto ('5,5' o '5.5'). Puede ser negativo (temperaturas)."""
    if isinstance(valor, bool):
        raise EntradaInvalida(f"{campo} no es un número válido")
    try:
        return float(str(valor).strip().replace(",", ".")) if isinstance(valor, str) else float(valor)
    except (TypeError, ValueError):
        raise EntradaInvalida(f"{campo} no es un número válido") from None


def entero_positivo(valor, campo: str) -> int:
    try:
        texto = str(valor).strip()
        entero = int(texto)
    except (TypeError, ValueError):
        raise EntradaInvalida(f"{campo} debe ser un número entero") from None
    if isinstance(valor, bool) or entero <= 0:
        raise EntradaInvalida(f"{campo} debe ser un número entero mayor a cero")
    return entero


def monto(valor, campo: str) -> Decimal:
    """Importe en pesos, nunca negativo, con a lo sumo 2 decimales. Devuelve Decimal (no float)."""
    try:
        resultado = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise EntradaInvalida(f"{campo} no es un importe válido") from None
    if not resultado.is_finite() or resultado < 0:
        raise EntradaInvalida(f"{campo} no puede ser negativo")
    if resultado != resultado.quantize(Decimal("0.01")):
        raise EntradaInvalida(f"{campo} admite hasta 2 decimales")
    return resultado


def opcion(valor, clase: type[E], campo: str) -> E:
    """Convierte a un enum: acepta el enum mismo o su nombre/valor en cualquier mayúscula."""
    if isinstance(valor, clase):
        return valor
    texto = _limpiar(valor).upper().replace(" ", "_")
    for miembro in clase:
        if texto in (miembro.name, str(miembro.value).upper()):
            return miembro
    validas = ", ".join(m.value for m in clase)
    raise EntradaInvalida(f"{campo} no es válido (opciones: {validas})")

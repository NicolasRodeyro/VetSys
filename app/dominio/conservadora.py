"""Conservadora isotérmica: contenedor que lleva muestras manteniendo la temperatura."""

from __future__ import annotations

from datetime import datetime

from app.dominio.excepciones import ReglaNegocio
from app.dominio.muestra import Muestra
from app.dominio.precinto import Precinto


class Conservadora:
    def __init__(self, codigo: str, capacidad: int, temp_min: float, temp_max: float) -> None:
        if capacidad <= 0:
            raise ReglaNegocio("La capacidad de la conservadora debe ser mayor a cero")
        if temp_min > temp_max:
            raise ReglaNegocio("La temperatura mínima no puede superar a la máxima")
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.codigo = codigo
        self._capacidad = capacidad
        self._temp_min = temp_min
        self._temp_max = temp_max
        self._muestras: list[Muestra] = []
        self._precinto: Precinto | None = None

    @property
    def capacidad(self) -> int:
        return self._capacidad

    @property
    def temp_min(self) -> float:
        return self._temp_min

    @property
    def temp_max(self) -> float:
        return self._temp_max

    @property
    def muestras(self) -> tuple[Muestra, ...]:
        return tuple(self._muestras)

    @property
    def precinto(self) -> Precinto | None:
        return self._precinto

    def admite_temperatura(self, temperatura: float) -> bool:
        return self._temp_min <= temperatura <= self._temp_max

    def agregar_muestra(self, muestra: Muestra, responsable: str, ubicacion: str = "") -> None:
        """Empaqueta la muestra en esta conservadora.

        Valida que la conservadora siga abierta, que cuide la temperatura que pide
        el análisis y que tenga lugar. Que la muestra esté recién extraída lo valida
        su propio estado: `empaquetar()` lanza TransicionInvalida en cualquier otro.
        Las muestras pueden ser de distintas órdenes.
        """
        if self._precinto is not None:
            raise ReglaNegocio("La conservadora ya está precintada: no se pueden agregar muestras")
        if not muestra.tipo_analisis.admite_rango(self._temp_min, self._temp_max):
            raise ReglaNegocio(
                f"La conservadora ({self._temp_min} a {self._temp_max} °C) no es compatible "
                f"con la temperatura que necesita {muestra.tipo_analisis.nombre}"
            )
        if len(self._muestras) >= self._capacidad:
            raise ReglaNegocio(f"La conservadora {self.codigo} está llena")

        # Si la muestra no está Extraída, empaquetar() falla y no se agrega nada.
        muestra.empaquetar(responsable, ubicacion, f"Conservadora {self.codigo}")
        self._muestras.append(muestra)

    def precintar(self, numero: str, responsable: str, fecha_colocacion: datetime) -> Precinto:
        """Coloca el precinto sanitario: desde ahí la conservadora queda cerrada."""
        if self._precinto is not None:
            raise ReglaNegocio("La conservadora ya tiene precinto")
        if not self._muestras:
            raise ReglaNegocio("No se puede precintar una conservadora vacía")
        self._precinto = Precinto(numero, fecha_colocacion, responsable)
        return self._precinto

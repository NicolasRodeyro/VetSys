"""Cliente: el responsable de una o más mascotas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.dominio.excepciones import ReglaNegocio

if TYPE_CHECKING:
    from app.dominio.mascota import Mascota


class Cliente:
    def __init__(
        self,
        dni: str,
        nombre: str,
        apellido: str,
        telefono: str,
        email: str,
        direccion: str,
    ) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.dni = dni
        self.nombre = nombre
        self.apellido = apellido
        self.telefono = telefono
        self.email = email
        self.direccion = direccion
        # La lista es privada: solo se agregan mascotas que tengan a este
        # cliente como responsable (ver agregar_mascota).
        self._mascotas: list[Mascota] = []
        self._activo = True

    @property
    def mascotas(self) -> tuple[Mascota, ...]:
        # Se devuelve una tupla para que no se pueda modificar desde afuera.
        return tuple(self._mascotas)

    @property
    def activo(self) -> bool:
        return self._activo

    def dar_de_baja(self) -> None:
        """Baja lógica: el cliente deja de aparecer, pero no se borra (sus mascotas,
        consultas y comprobantes siguen existiendo). Como toda mascota necesita un
        responsable, no se puede dar de baja a quien tiene mascotas activas."""
        if any(mascota.activa for mascota in self._mascotas):
            raise ReglaNegocio("No se puede dar de baja al cliente: tiene mascotas activas")
        self._activo = False

    def reactivar(self) -> None:
        self._activo = True

    def agregar_mascota(self, mascota: Mascota) -> None:
        if mascota.responsable is not self:
            raise ReglaNegocio("La mascota tiene otro responsable")
        if not self._activo:
            raise ReglaNegocio("El cliente está dado de baja: no se le pueden agregar mascotas")
        if mascota not in self._mascotas:
            self._mascotas.append(mascota)

    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

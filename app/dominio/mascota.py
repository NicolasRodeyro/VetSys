"""Mascota: siempre tiene exactamente un responsable."""

from datetime import date

from app.dominio.cliente import Cliente
from app.dominio.enums import Sexo
from app.dominio.especie import Especie
from app.dominio.excepciones import ReglaNegocio
from app.dominio.fechas import meses_entre
from app.dominio.historia_clinica import HistoriaClinica


class Mascota:
    def __init__(
        self,
        nombre: str,
        especie: Especie,
        sexo: Sexo,
        fecha_nacimiento: date,
        responsable: Cliente,
    ) -> None:
        # Regla de negocio: toda mascota tiene responsable. Se valida en el
        # constructor para que no pueda existir una Mascota sin él.
        if responsable is None:
            raise ReglaNegocio("Toda mascota debe tener un responsable")

        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.nombre = nombre
        self.sexo = sexo
        self._activa = True
        self._especie = especie
        self._fecha_nacimiento = fecha_nacimiento
        self._responsable = responsable
        # Composición: la historia clínica nace con la mascota y le pertenece.
        self._historia_clinica = HistoriaClinica(self)
        responsable.agregar_mascota(self)

    @property
    def activa(self) -> bool:
        return self._activa

    def dar_de_baja(self) -> None:
        """Baja lógica: la mascota se conserva con su historia clínica, pero ya no se atiende."""
        self._activa = False

    def reactivar(self) -> None:
        if not self._responsable.activo:
            raise ReglaNegocio("No se puede reactivar la mascota: su responsable está dado de baja")
        self._activa = True

    @property
    def especie(self) -> Especie:
        return self._especie

    @property
    def fecha_nacimiento(self) -> date:
        return self._fecha_nacimiento

    @property
    def responsable(self) -> Cliente:
        return self._responsable

    @property
    def historia_clinica(self) -> HistoriaClinica:
        return self._historia_clinica

    def edad_en_meses(self, fecha: date) -> int:
        if fecha < self._fecha_nacimiento:
            raise ReglaNegocio("La fecha es anterior al nacimiento de la mascota")
        return meses_entre(self._fecha_nacimiento, fecha)

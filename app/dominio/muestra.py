"""Muestra biológica: su estado y su trazabilidad.

La muestra no decide nada según su estado: delega en el objeto de estado
actual (patrón State, ver estados_muestra.py). Además es el sujeto del patrón
Observer: avisa a sus observadores en cada cambio (ver observadores_muestra.py).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import TYPE_CHECKING

from app.dominio.cambio_estado import CambioEstado
from app.dominio.enums import MotivoRechazo
from app.dominio.estados_muestra import EstadoMuestra, Extraida

if TYPE_CHECKING:
    from app.dominio.observadores_muestra import ObservadorMuestra
    from app.dominio.orden_derivacion import OrdenDerivacion
    from app.dominio.tipo_analisis import TipoAnalisis


class Muestra:
    def __init__(
        self,
        orden: OrdenDerivacion,
        responsable: str,
        ubicacion: str = "",
        observacion: str = "",
        reloj: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Extrae una muestra para una orden de derivación.

        `reloj` da la fecha y hora de cada cambio; se puede reemplazar en los
        tests para que las fechas sean predecibles.
        """
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self._orden = orden
        self._reloj = reloj
        self._observadores: list[ObservadorMuestra] = []
        self._estado: EstadoMuestra = Extraida()
        # La extracción es el origen de la muestra, no una transición:
        # la registra la propia muestra como primer renglón de su historial.
        self._historial: list[CambioEstado] = [
            CambioEstado(None, self._estado.nombre, reloj(), responsable, ubicacion, observacion)
        ]
        # Regla de negocio: una sola muestra activa por orden. Si la orden ya
        # tiene una, agregar_muestra() lanza ReglaNegocio y la muestra no se crea.
        orden.agregar_muestra(self)

    @property
    def orden(self) -> OrdenDerivacion:
        return self._orden

    @property
    def tipo_analisis(self) -> TipoAnalisis:
        return self._orden.tipo_analisis

    @property
    def estado(self) -> EstadoMuestra:
        return self._estado

    @property
    def historial(self) -> tuple[CambioEstado, ...]:
        # Tupla: desde afuera solo se puede leer.
        return tuple(self._historial)

    def esta_activa(self) -> bool:
        return self._estado.activa

    # --- Observer: la muestra es el sujeto ---

    def suscribir(self, observador: ObservadorMuestra) -> None:
        self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorMuestra) -> None:
        self._observadores.remove(observador)

    def agregar_al_historial(self, cambio: CambioEstado) -> None:
        """Solo agrega: el historial nunca se modifica ni se borra.

        Lo llama RegistroTrazabilidad, el observador que lleva la trazabilidad.
        """
        self._historial.append(cambio)

    # --- Operaciones: la muestra delega en su estado ---

    def empaquetar(self, responsable: str, ubicacion: str = "", observacion: str = "") -> None:
        self._estado.empaquetar(self, responsable, ubicacion, observacion)

    def despachar(self, responsable: str, ubicacion: str = "", observacion: str = "") -> None:
        self._estado.despachar(self, responsable, ubicacion, observacion)

    def recibir(
        self,
        aceptada: bool,
        responsable: str,
        motivos: Iterable[MotivoRechazo] = (),
        ubicacion: str = "",
        observacion: str = "",
    ) -> None:
        self._estado.recibir(self, aceptada, motivos, responsable, ubicacion, observacion)

    def analizar(self, responsable: str, ubicacion: str = "", observacion: str = "") -> None:
        self._estado.analizar(self, responsable, ubicacion, observacion)

    def cambiar_estado(
        self,
        nuevo_estado: EstadoMuestra,
        responsable: str,
        ubicacion: str = "",
        observacion: str = "",
    ) -> None:
        """La llaman los estados para hacer efectiva una transición.

        State y Observer se juntan acá: el estado decidió la transición y
        esta operación la aplica y avisa a los observadores.
        """
        anterior = self._estado
        self._estado = nuevo_estado
        cambio = CambioEstado(
            anterior.nombre,
            nuevo_estado.nombre,
            self._reloj(),
            responsable,
            ubicacion,
            observacion,
            nuevo_estado.motivos,
        )
        for observador in list(self._observadores):
            observador.actualizar(self, cambio)

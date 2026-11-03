"""Pantalla de turnos: la agenda de cada veterinario (no se superponen) y la reserva."""

from __future__ import annotations

import flet as ft

from app.servicios import catalogos
from app.servicios import turnos as svc
from app.servicios.excepciones import ReglaNegocio
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import en_texto
from app.ui.fecha_hora import SelectorFechaHora
from app.ui.pantalla import Pantalla, manejador
from app.ui.selectores import SelectorMascota


DURACION_POR_DEFECTO = "30"


class PantallaTurnos(Pantalla):
    clave = "turnos"
    titulo = "Turnos"
    icono = ft.Icons.EVENT_OUTLINED
    grupo = "Atención"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self.veterinario = c.desplegable("Veterinario", expandir=True, al_elegir=self.cargar_agenda)
        self.ver_cancelados = ft.Checkbox(label="Ver cancelados", value=False, on_change=self.cargar_agenda)
        self.tabla = c.Tabla(["Fecha y hora", "Duración", "Mascota", "Responsable", "Estado"], al_elegir=self.cancelar,
                             texto_boton="Cancelar turno", icono=ft.Icons.EVENT_BUSY_OUTLINED,
                             vacia="El veterinario no tiene turnos.")
        self.selector = SelectorMascota(self, self._revisar_avisos)
        self.momento = SelectorFechaHora(self, al_cambiar=self._revisar_avisos)
        self.duracion = c.campo("Duración (minutos)", DURACION_POR_DEFECTO, ancho=170)
        # El aviso va junto al botón: la pantalla es larga y el mensaje flotante podía quedar fuera de vista.
        fondo, color = tema.TONOS["peligro"]
        self._texto_aviso = ft.Text("", color=color, weight=ft.FontWeight.W_500, expand=True)
        self.aviso_reserva = ft.Container(
            ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=color, size=20), self._texto_aviso],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=fondo, border=ft.Border.all(1, color), border_radius=ft.BorderRadius.all(8),
            padding=ft.Padding.symmetric(vertical=8, horizontal=12), visible=False, expand=True)
        self._aviso_de_faltantes = False

    def build(self) -> ft.Control:
        agenda = tema.seccion(
            "Agenda del veterinario",
            tema.fila(self.veterinario, self.ver_cancelados), self.tabla.vista)
        reserva = tema.seccion(
            "Reservar un turno",
            tema.texto_tenue("Se reserva en la agenda del veterinario elegido arriba. Dos turnos del mismo veterinario no pueden superponerse."),
            self.selector.vista,
            tema.fila(self.momento.vista, self.duracion),
            tema.fila(c.boton("Reservar turno", ft.Icons.EVENT_AVAILABLE, self.reservar), self.aviso_reserva))
        return tema.pagina(tema.titulo_pantalla("Turnos", "Agenda de cada veterinario."), agenda, reserva)

    @manejador
    def al_mostrar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.veterinario, (
                (str(v.id), f"{v.apellido}, {v.nombre} · {v.clinica.nombre}") for v in catalogos.listar_veterinarios()),
                conservar=True)
            if self.momento.vacio():
                self.momento.poner_ahora()
        self.ejecutar(accion)
        self.cargar_agenda()

    @manejador
    def cargar_agenda(self) -> None:
        if self.veterinario.value:
            self.veterinario.error_text = None
            self._revisar_avisos()

        def accion() -> None:
            veterinario_id = c.clave_de(self.veterinario)
            turnos = svc.listar_turnos(veterinario_id, bool(self.ver_cancelados.value)) if veterinario_id else []
            self.tabla.cargar((t.id, [
                en_texto(t.inicio), f"{t.duracion_minutos} min", t.mascota.nombre,
                f"{t.mascota.responsable.apellido}, {t.mascota.responsable.nombre}",
                "Programado" if t.estado.value == "PROGRAMADO" else "Cancelado"]) for t in turnos)
        self.ejecutar(accion)

    # ----------------------------------------------------------- avisos de la reserva

    def _faltantes(self) -> list[str]:
        faltan = []
        if c.clave_de(self.veterinario) is None:
            faltan.append("el veterinario")
        if self.selector.mascota_id is None:
            faltan.append("la mascota")
        return faltan + self.momento.faltantes()

    def _marcar_faltantes(self) -> list[str]:
        """Pinta de rojo lo que falta y devuelve qué es."""
        self.veterinario.error_text = "Elegí un veterinario" if c.clave_de(self.veterinario) is None else None
        self.selector.lista.error_text = "Elegí la mascota" if self.selector.mascota_id is None else None
        self.momento.marcar_faltantes()
        return self._faltantes()

    def _mostrar_aviso(self, texto: str, faltantes: bool = False) -> None:
        self._texto_aviso.value = texto
        self.aviso_reserva.visible = True
        self._aviso_de_faltantes = faltantes

    def _ocultar_aviso(self) -> None:
        self.aviso_reserva.visible = False
        self._texto_aviso.value = ""
        self._aviso_de_faltantes = False

    def _limpiar_marcas(self) -> None:
        self.veterinario.error_text = self.selector.lista.error_text = None
        self.momento.limpiar_avisos()

    def _revisar_avisos(self) -> None:
        """Al elegir algo, desaparece su marca roja; el recuadro se achica o se va cuando ya no falta nada."""
        if self.veterinario.value:
            self.veterinario.error_text = None
        if not self._aviso_de_faltantes:
            return
        faltan = self._faltantes()
        if faltan:
            self._texto_aviso.value = self._texto_de_faltantes(faltan)
        else:
            self._ocultar_aviso()

    @staticmethod
    def _texto_de_faltantes(faltan: list[str]) -> str:
        return "Para reservar el turno falta elegir: " + ", ".join(faltan) + "."

    # ----------------------------------------------------------- acciones

    @manejador
    def reservar(self) -> None:
        faltan = self._marcar_faltantes()
        if faltan:
            texto = self._texto_de_faltantes(faltan)
            self._mostrar_aviso(texto, faltantes=True)
            self.sesion.mensajero.error(texto)
            return
        self._ocultar_aviso()

        def accion() -> None:
            try:
                svc.reservar_turno(c.clave_de(self.veterinario), self.selector.mascota_id,
                                   self.momento.valor, self.duracion.value)
            except Exception as error:  # también queda escrito junto al botón; ejecutar() lo informa
                self._mostrar_aviso(str(error) if isinstance(error, ReglaNegocio) else f"Error inesperado: {error}")
                raise
        if self.ejecutar(accion, "Turno reservado."):
            self._limpiar_formulario()
            self.cargar_agenda()

    def _limpiar_formulario(self) -> None:
        """Después de reservar: se vacían el cliente y la mascota, la fecha y la hora vuelven a «ahora» y la
        duración a 30. El veterinario se conserva: es la agenda que se está mirando."""
        self.selector.limpiar()
        self.momento.poner_ahora()
        self.duracion.value = DURACION_POR_DEFECTO
        self._limpiar_marcas()
        self._ocultar_aviso()

    @manejador
    def cancelar(self, turno_id: int) -> None:
        if self.ejecutar(lambda: svc.cancelar_turno(turno_id), "Turno cancelado."):
            self.cargar_agenda()

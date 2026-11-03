"""Pantalla de turnos: la agenda de cada veterinario (no se superponen) y la reserva."""

from __future__ import annotations

import flet as ft

from app.servicios import catalogos
from app.servicios import turnos as svc
from app.servicios.excepciones import EntradaInvalida, ReglaNegocio
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
        self.selector = SelectorMascota(self)
        self.inicio = SelectorFechaHora("Fecha del turno", "Hora")
        self.duracion = c.campo("Duración (minutos)", DURACION_POR_DEFECTO, ancho=170)
        # Junto al botón: lo que impide reservar, a la vista aunque la pantalla esté desplazada.
        self.aviso = ft.Container(
            ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=tema.TONOS["peligro"][1], size=18),
                    ft.Text("", color=tema.TONOS["peligro"][1], expand=True)], spacing=8),
            bgcolor=tema.TONOS["peligro"][0], border_radius=ft.BorderRadius.all(8),
            padding=ft.Padding.symmetric(vertical=8, horizontal=12), visible=False)

    def build(self) -> ft.Control:
        agenda = tema.seccion(
            "Agenda del veterinario",
            tema.fila(self.veterinario, self.ver_cancelados), self.tabla.vista)
        reserva = tema.seccion(
            "Reservar un turno",
            tema.texto_tenue("Se reserva en la agenda del veterinario elegido arriba. Dos turnos del mismo veterinario no pueden superponerse."),
            self.selector.vista,
            tema.fila(self.inicio.vista, self.duracion, c.boton("Reservar turno", ft.Icons.EVENT_AVAILABLE, self.reservar)),
            self.aviso)
        return tema.pagina(tema.titulo_pantalla("Turnos", "Agenda de cada veterinario."), agenda, reserva)

    @manejador
    def al_mostrar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.veterinario, (
                (str(v.id), f"{v.apellido}, {v.nombre} · {v.clinica.nombre}") for v in catalogos.listar_veterinarios()),
                conservar=True)
            if self.inicio.fecha is None:
                self.inicio.poner_ahora()
        self.ejecutar(accion)
        self.cargar_agenda()

    @manejador
    def cargar_agenda(self) -> None:
        def accion() -> None:
            veterinario_id = c.clave_de(self.veterinario)
            if veterinario_id:
                self.veterinario.error_text = None
            turnos = svc.listar_turnos(veterinario_id, bool(self.ver_cancelados.value)) if veterinario_id else []
            self.tabla.cargar((t.id, [
                en_texto(t.inicio), f"{t.duracion_minutos} min", t.mascota.nombre,
                f"{t.mascota.responsable.apellido}, {t.mascota.responsable.nombre}",
                "Programado" if t.estado.value == "PROGRAMADO" else "Cancelado"]) for t in turnos)
        self.ejecutar(accion)

    @manejador
    def reservar(self) -> None:
        self._avisar(None)

        def accion() -> None:
            faltan = self._marcar_faltantes()
            if faltan:
                raise EntradaInvalida("Para reservar el turno falta elegir: " + ", ".join(faltan) + ".")
            svc.reservar_turno(c.clave_de(self.veterinario), self.selector.mascota_id,
                               self.inicio.valor("El inicio"), self.duracion.value)

        def accion_con_aviso() -> None:
            try:
                accion()
            except ReglaNegocio as error:
                self._avisar(str(error))  # además de la barra, queda escrito junto al botón
                raise

        if self.ejecutar(accion_con_aviso, "Turno reservado."):
            self._limpiar_formulario()
            self.cargar_agenda()

    def _marcar_faltantes(self) -> list[str]:
        """Pone en rojo, en cada campo, lo que falta, y devuelve la lista para el mensaje."""
        faltan = []
        if c.clave_de(self.veterinario) is None:
            self.veterinario.error_text = "Elegí un veterinario"
            faltan.append("el veterinario (arriba, en «Agenda del veterinario»)")
        if self.selector.mascota_id is None:
            self.selector.lista.error_text = "Elegí la mascota"
            faltan.append("la mascota (buscá al cliente y elegí una de sus mascotas)")
        return faltan + self.inicio.marcar_faltantes()

    def _avisar(self, texto: str | None) -> None:
        self.aviso.visible = bool(texto)
        self.aviso.content.controls[1].value = texto or ""

    def _limpiar_formulario(self) -> None:
        """Después de reservar queda listo para el próximo turno. El veterinario se conserva: es
        la agenda que se está mirando y donde acaba de aparecer el turno."""
        self.selector.limpiar()
        self.inicio.poner_ahora()
        self.duracion.value = DURACION_POR_DEFECTO

    @manejador
    def cancelar(self, turno_id: int) -> None:
        if self.ejecutar(lambda: svc.cancelar_turno(turno_id), "Turno cancelado."):
            self.cargar_agenda()

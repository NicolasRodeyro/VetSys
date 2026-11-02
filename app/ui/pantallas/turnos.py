"""Pantalla de turnos: la agenda de cada veterinario (no se superponen) y la reserva."""

from __future__ import annotations

import flet as ft

from app.servicios import catalogos
from app.servicios import turnos as svc
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import a_fecha_hora, ahora_texto, en_texto
from app.ui.pantalla import Pantalla, manejador
from app.ui.selectores import SelectorMascota


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
        self.inicio = c.campo("Inicio", ancho=210, sugerencia="AAAA-MM-DD HH:MM")
        self.duracion = c.campo("Duración (minutos)", "30", ancho=170)

    def build(self) -> ft.Control:
        agenda = tema.seccion(
            "Agenda del veterinario",
            tema.fila(self.veterinario, self.ver_cancelados), self.tabla.vista)
        reserva = tema.seccion(
            "Reservar un turno",
            tema.texto_tenue("Se reserva en la agenda del veterinario elegido arriba. Dos turnos del mismo veterinario no pueden superponerse."),
            self.selector.vista,
            tema.fila(self.inicio, self.duracion, c.boton("Reservar turno", ft.Icons.EVENT_AVAILABLE, self.reservar)))
        return tema.pagina(tema.titulo_pantalla("Turnos", "Agenda de cada veterinario."), agenda, reserva)

    @manejador
    def al_mostrar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.veterinario, (
                (str(v.id), f"{v.apellido}, {v.nombre} · {v.clinica.nombre}") for v in catalogos.listar_veterinarios()),
                conservar=True)
            if not (self.inicio.value or "").strip():
                self.inicio.value = ahora_texto()
        self.ejecutar(accion)
        self.cargar_agenda()

    @manejador
    def cargar_agenda(self) -> None:
        def accion() -> None:
            veterinario_id = c.clave_de(self.veterinario)
            turnos = svc.listar_turnos(veterinario_id, bool(self.ver_cancelados.value)) if veterinario_id else []
            self.tabla.cargar((t.id, [
                en_texto(t.inicio), f"{t.duracion_minutos} min", t.mascota.nombre,
                f"{t.mascota.responsable.apellido}, {t.mascota.responsable.nombre}",
                "Programado" if t.estado.value == "PROGRAMADO" else "Cancelado"]) for t in turnos)
        self.ejecutar(accion)

    @manejador
    def reservar(self) -> None:
        def accion() -> None:
            veterinario_id = c.clave_de(self.veterinario)
            if veterinario_id is None:
                raise EntradaInvalida("Elegí el veterinario para reservar el turno.")
            if self.selector.mascota_id is None:
                raise EntradaInvalida("Elegí la mascota (buscá primero a su cliente).")
            svc.reservar_turno(veterinario_id, self.selector.mascota_id,
                               a_fecha_hora(self.inicio.value, "El inicio"), self.duracion.value)
        if self.ejecutar(accion, "Turno reservado."):
            self.cargar_agenda()

    @manejador
    def cancelar(self, turno_id: int) -> None:
        if self.ejecutar(lambda: svc.cancelar_turno(turno_id), "Turno cancelado."):
            self.cargar_agenda()

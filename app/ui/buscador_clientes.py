"""Búsqueda de clientes en vivo: un campo de texto y, debajo, la lista de coincidencias.

Al tocar el campo vacío aparecen todos los clientes; al escribir, la lista se acota (por DNI,
apellido o nombre). Al tocar un cliente queda elegido. Lo usan todas las pantallas que
buscan un cliente por texto (el selector compartido y la pantalla de mascotas).
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import flet as ft

from app.servicios import clientes as svc
from app.ui import componentes as c
from app.ui import tema
from app.ui.pantalla import Pantalla, manejador

MAXIMO_VISIBLE = 30
ALTO_RENGLON = 60
ALTO_MAXIMO_LISTA = 280


def descripcion(cliente) -> str:
    """El texto que queda en el campo al elegir un cliente."""
    return f"{cliente.apellido}, {cliente.nombre} ({cliente.dni})"


def _mascotas_de(cliente) -> str:
    nombres = [m.nombre for m in cliente.mascotas if m.activa]
    return ", ".join(nombres) if nombres else "sin mascotas"


class BuscadorClientes:
    """`al_elegir(cliente)` se llama al tocar un cliente de la lista. `al_escribir()` se llama
    cuando el usuario sigue escribiendo: lo elegido (y lo que dependa de eso) ya no vale.
    `al_buscar()` se llama con Enter o el botón «Buscar», después de armar la lista."""

    def __init__(self, pantalla: Pantalla, al_elegir: Callable[[object], None] | None = None,
                 al_escribir: Callable[[], None] | None = None, al_buscar: Callable[[], None] | None = None,
                 etiqueta: str = "Buscar cliente (DNI, apellido o nombre)",
                 incluir_inactivos: bool = False) -> None:
        self._pantalla = pantalla
        self._al_elegir = al_elegir
        self._al_escribir = al_escribir
        self._al_buscar = al_buscar
        self._incluir_inactivos = incluir_inactivos
        self.cliente = None  # el cliente elegido (objeto de los servicios), o None
        self.coincidencias: list = []  # los clientes que se muestran en la lista

        self.campo = c.campo(etiqueta, expandir=True, al_enviar=self.buscar)
        self.campo.on_change = self.escribir
        self.campo.on_focus = self.abrir
        self.boton = c.boton("Buscar", ft.Icons.SEARCH, self.buscar, "secundario")

        self._resumen = tema.texto_tenue("", 12)
        self._renglones = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)
        self._panel = ft.Container(
            ft.Column([
                ft.Row([self._resumen, ft.Container(expand=True),
                        ft.IconButton(ft.Icons.CLOSE, tooltip="Cerrar la lista", icon_size=18, on_click=self.cerrar)],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self._renglones,
            ], spacing=0),
            border=ft.Border.all(1, tema.BORDE), border_radius=ft.BorderRadius.all(10), bgcolor=tema.SUPERFICIE,
            padding=ft.Padding.symmetric(vertical=4, horizontal=8), visible=False)
        self.vista = ft.Column([tema.fila(self.campo, self.boton), self._panel], spacing=4)

    # ----------------------------------------------------------- estado

    @property
    def texto(self) -> str:
        return self.campo.value or ""

    @property
    def abierta(self) -> bool:
        return bool(self._panel.visible)

    # ----------------------------------------------------------- eventos

    @manejador
    def abrir(self) -> None:
        """Al tocar el campo: muestra la lista (todos los clientes si está vacío)."""
        self._mostrar_coincidencias()

    @manejador
    def escribir(self) -> None:
        """El usuario escribió: se acota la lista y se descarta lo que había elegido."""
        self.cliente = None
        if self._al_escribir:
            self._al_escribir()
        self._mostrar_coincidencias()

    @manejador
    def buscar(self) -> None:
        """Enter o el botón «Buscar»."""
        self._mostrar_coincidencias()
        if self._al_buscar:
            self._al_buscar()

    @manejador
    def cerrar(self) -> None:
        self._panel.visible = False

    @manejador
    def elegir(self, cliente_id: int) -> None:
        cliente = next((x for x in self.coincidencias if x.id == cliente_id), None)
        if cliente is None:
            return
        self.cliente = cliente
        self.campo.value = descripcion(cliente)
        self._panel.visible = False
        if self._al_elegir:
            self._al_elegir(cliente)

    # ----------------------------------------------------------- lista

    def buscar_ahora(self) -> list:
        """Lee los clientes que coinciden con el texto, sin tocar la lista que se ve."""
        return svc.buscar_clientes(self.texto, self._incluir_inactivos)

    def _mostrar_coincidencias(self) -> None:
        def accion() -> None:
            todos = self.buscar_ahora()
            self.coincidencias = todos[:MAXIMO_VISIBLE]
            self._renglones.controls = [self._renglon(x) for x in self.coincidencias]
            self._renglones.height = min(len(self.coincidencias) * ALTO_RENGLON, ALTO_MAXIMO_LISTA) or None
            if not todos:
                self._resumen.value = "No hay clientes que coincidan."
            elif len(todos) > MAXIMO_VISIBLE:
                self._resumen.value = (f"Mostrando {MAXIMO_VISIBLE} de {len(todos)} clientes: "
                                       "seguí escribiendo para acotar.")
            else:
                self._resumen.value = f"{len(todos)} cliente(s)"
            self._panel.visible = True
        self._pantalla.ejecutar(accion)

    @staticmethod
    def _renglon_texto(cliente) -> tuple[str, str]:
        return f"{cliente.apellido}, {cliente.nombre}", f"DNI {cliente.dni} · Mascotas: {_mascotas_de(cliente)}"

    def _renglon(self, cliente) -> ft.Control:
        titulo, detalle = self._renglon_texto(cliente)
        # partial (y no un lambda): Flet le pasaría el evento a un lambda.
        return ft.ListTile(
            title=ft.Text(titulo, weight=ft.FontWeight.W_600, color=tema.TEXTO),
            subtitle=ft.Text(detalle, size=12, color=tema.TEXTO_TENUE), dense=True,
            hover_color=tema.PRIMARIO_SUAVE, on_click=partial(self.elegir, cliente.id))

    def textos_de_la_lista(self) -> list[tuple[str, str]]:
        """Lo que muestra cada renglón (título, detalle), para leer la lista sin mirar los controles."""
        return [self._renglon_texto(x) for x in self.coincidencias]

    def limpiar(self) -> None:
        self.campo.value = ""
        self.campo.error = None
        self.cliente = None
        self.coincidencias = []
        self._renglones.controls = []
        self._panel.visible = False

"""Búsqueda de clientes con la lista de coincidencias en vivo.

Mientras se escribe (DNI, apellido o nombre), debajo del campo aparece la lista de clientes que
coinciden; con el campo vacío, tocarlo muestra todos. Al tocar uno se avisa a quien lo usa con
`al_elegir(cliente)`. Lo usan el selector de mascota (Turnos, Consultas, Comprobantes, Muestras)
y la pantalla de Mascotas, para que busquen todos igual.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

import flet as ft

from app.servicios import clientes as svc_clientes
from app.ui import componentes as c
from app.ui import tema
from app.ui.pantalla import Pantalla, manejador

MAX_SUGERENCIAS = 30      # clientes que se muestran a la vez (el resto se alcanza escribiendo más)
_ALTO_SUGERENCIA = 58     # alto de cada renglón de la lista
_ALTO_MAXIMO_LISTA = 232


class BuscadorClientes:
    def __init__(self, pantalla: Pantalla, etiqueta: str, al_elegir: Callable[[Any], None], *,
                 al_escribir: Callable[[], None] | None = None,
                 al_enviar: Callable[[], None] | None = None) -> None:
        """`al_elegir(cliente)`: se toca un cliente de la lista. `al_escribir()`: el usuario cambió
        el texto (lo que se había elegido ya no corresponde). `al_enviar()`: se apretó Enter."""
        self._pantalla = pantalla
        self._al_elegir = al_elegir
        self._al_escribir_afuera = al_escribir
        self.sugeridos: dict[int, Any] = {}   # id -> cliente, de la lista que se está mostrando
        self.busqueda = c.campo(etiqueta, expandir=True, al_enviar=al_enviar)
        self.busqueda.on_change = self._al_escribir
        self.busqueda.on_focus = self._al_enfocar
        self._titulo = tema.texto_tenue("", 12)
        self.filas = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)
        self.panel = ft.Container(
            ft.Column([
                ft.Row([self._titulo, ft.Container(expand=True),
                        ft.IconButton(ft.Icons.CLOSE, icon_size=16, tooltip="Cerrar la lista", on_click=self.cerrar)],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.filas,
            ], spacing=0),
            visible=False, bgcolor=tema.SUPERFICIE, border=ft.Border.all(1, tema.BORDE),
            border_radius=ft.BorderRadius.all(8), padding=ft.Padding.only(left=12, right=4, top=4, bottom=4))

    @property
    def titulo(self) -> str:
        return self._titulo.value or ""

    # ------------------------------------------------------------ eventos

    @manejador
    def _al_escribir(self) -> None:
        if self._al_escribir_afuera:
            self._al_escribir_afuera()
        self.sugerir()

    @manejador
    def _al_enfocar(self) -> None:
        # Con el campo vacío, tocarlo muestra todos los clientes para elegir sin escribir.
        if not (self.busqueda.value or "").strip():
            self.sugerir()

    @manejador
    def sugerir(self) -> None:
        """Muestra, debajo del campo, los clientes que coinciden con lo escrito."""
        def accion() -> None:
            texto = (self.busqueda.value or "").strip()
            self._mostrar(svc_clientes.buscar_clientes(texto), texto)
        self._pantalla.ejecutar(accion)

    def _mostrar(self, clientes: list, texto: str) -> None:
        self.sugeridos = {cliente.id: cliente for cliente in clientes}
        visibles = clientes[:MAX_SUGERENCIAS]
        filas: list[ft.Control] = []
        for cliente in visibles:
            mascotas = ", ".join(m.nombre for m in cliente.mascotas if m.activa) or "sin mascotas activas"
            filas.append(ft.ListTile(
                title=ft.Text(f"{cliente.apellido}, {cliente.nombre}", color=tema.TEXTO),
                subtitle=tema.texto_tenue(f"DNI {cliente.dni} · {mascotas}", 12),
                dense=True, hover_color=tema.PRIMARIO_SUAVE, on_click=partial(self._elegir, cliente.id)))
        if not clientes:
            self._titulo.value = f"No hay clientes que coincidan con «{texto}»."
        elif len(clientes) > len(visibles):
            self._titulo.value = f"{len(clientes)} clientes: se muestran {len(visibles)}. Seguí escribiendo para acotar."
        else:
            self._titulo.value = f"{len(clientes)} cliente(s): tocá uno para elegirlo."
        self.filas.controls = filas
        self.filas.height = min(len(filas) * _ALTO_SUGERENCIA, _ALTO_MAXIMO_LISTA) if filas else None
        self.panel.visible = True

    @manejador
    def _elegir(self, cliente_id: int) -> None:
        def accion() -> None:
            cliente = self.sugeridos[cliente_id]
            self.busqueda.value = f"{cliente.apellido}, {cliente.nombre}"
            self.ocultar()
            self._al_elegir(cliente)
        self._pantalla.ejecutar(accion)

    @manejador
    def cerrar(self) -> None:
        self.ocultar()

    # ------------------------------------------------------------ para quien lo usa

    def ocultar(self) -> None:
        self.panel.visible = False
        self.filas.controls = []
        self.sugeridos = {}

    def limpiar(self) -> None:
        self.busqueda.value = ""
        self.ocultar()

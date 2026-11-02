"""La ventana principal: menú lateral, campo de operador y el área donde se muestra cada pantalla."""

from __future__ import annotations

from functools import partial

import flet as ft

from app.servicios import arranque
from app.ui import componentes as c
from app.ui import tema
from app.ui.mensajero import MensajeroFlet
from app.ui.pantalla import Pantalla
from app.ui.pantallas import PANTALLAS
from app.ui.sesion import Sesion


class Aplicacion:
    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self.operador = c.campo("Operador", ancho=230, sugerencia="Quién opera el sistema")
        self.sesion = Sesion(MensajeroFlet(page), lambda: self.operador.value, page.update)
        self._pantallas: dict[str, Pantalla] = {clase.clave: clase(self.sesion) for clase in PANTALLAS}
        self._vistas: dict[str, ft.Control] = {}
        self._actual: str = PANTALLAS[0].clave

        self.area = ft.Container(expand=True, padding=ft.Padding.all(24))
        self.menu = ft.ListView(spacing=2, width=230, padding=ft.Padding.symmetric(vertical=8, horizontal=8))
        self.aviso_base_vacia = ft.Container(visible=False)

    # ----------------------------------------------------------- armado

    def build(self) -> ft.Control:
        encabezado = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PETS, color=ft.Colors.TEAL_700, size=28),
                ft.Column([ft.Text("VetSys", size=20, weight=ft.FontWeight.BOLD),
                           tema.texto_tenue("Red de clínicas veterinarias y laboratorio")], spacing=0),
                ft.Container(expand=True),
                self.operador,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=10, horizontal=16),
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        )
        cuerpo = ft.Row(
            [self.menu, ft.VerticalDivider(width=1), ft.Column([self.aviso_base_vacia, self.area], expand=True, spacing=0)],
            expand=True, spacing=0)
        return ft.Column([encabezado, cuerpo], expand=True, spacing=0)

    def _armar_menu(self) -> None:
        controles: list[ft.Control] = []
        grupo_actual = ""
        for clave, pantalla in self._pantallas.items():
            if pantalla.grupo != grupo_actual:
                grupo_actual = pantalla.grupo
                controles.append(ft.Container(
                    tema.texto_tenue(grupo_actual.upper(), 11), padding=ft.Padding.only(left=12, top=12, bottom=2)))
            controles.append(ft.ListTile(
                leading=ft.Icon(pantalla.icono), title=ft.Text(pantalla.titulo), dense=True,
                selected=clave == self._actual, on_click=partial(self.ir_a, clave),
                selected_tile_color=ft.Colors.TEAL_50, shape=ft.RoundedRectangleBorder(radius=8)))
        self.menu.controls = controles

    # ----------------------------------------------------------- navegación

    def ir_a(self, clave: str) -> None:
        try:
            self._ir_a(clave)
        finally:
            self._page.update()

    def _ir_a(self, clave: str) -> None:
        self._actual = clave
        pantalla = self._pantallas[clave]
        if clave not in self._vistas:
            self._vistas[clave] = pantalla.build()
        self.area.content = self._vistas[clave]
        self._armar_menu()
        pantalla.al_mostrar()

    # ----------------------------------------------------------- base vacía

    def _revisar_base(self) -> None:
        """Sin clínicas no se puede operar: se ofrece cargar los datos de prueba."""
        vacia = arranque.base_vacia()
        self.aviso_base_vacia.visible = vacia
        if vacia:
            self.aviso_base_vacia.content = ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.AMBER_800),
                ft.Text("La base de datos está vacía: faltan clínicas, veterinarios y análisis.", expand=True),
                c.boton("Cargar datos de prueba", ft.Icons.DOWNLOAD_OUTLINED, self._cargar_datos_de_prueba, "secundario"),
            ])
            self.aviso_base_vacia.bgcolor = ft.Colors.AMBER_50
            self.aviso_base_vacia.padding = ft.Padding.symmetric(vertical=8, horizontal=16)

    def _cargar_datos_de_prueba(self) -> None:
        arranque.cargar_datos_de_prueba()
        self.aviso_base_vacia.visible = False
        self.ir_a(self._actual)
        self.sesion.mensajero.exito("Datos de prueba cargados.")
        self._page.update()

    def iniciar(self) -> None:
        arranque.preparar_base()  # crea la base la primera vez
        self._revisar_base()
        self.ir_a(self._actual)
        self._page.update()


def main(page: ft.Page) -> None:
    tema.aplicar_tema(page, "VetSys")
    page.window.width = 1280
    page.window.height = 800
    aplicacion = Aplicacion(page)
    page.add(aplicacion.build())
    aplicacion.iniciar()

"""La ventana principal: menú lateral con la marca, barra superior (ubicación y operador)
y el área donde se muestra cada pantalla."""

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

        self.area = ft.Container(expand=True, padding=ft.Padding.symmetric(vertical=24, horizontal=32))
        self.menu = ft.ListView(spacing=2, expand=True, padding=ft.Padding.symmetric(vertical=4, horizontal=12))
        self.aviso_base_vacia = ft.Container(visible=False)
        self.ubicacion = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.icono_modo = ft.Icon(ft.Icons.LIGHT_MODE_OUTLINED, color=tema.TEXTO_TENUE, size=20)
        self.modo_oscuro = ft.Switch(value=False, tooltip="Modo oscuro", active_color=tema.PRIMARIO,
                                     on_change=self._al_cambiar_modo)

    # ----------------------------------------------------------- armado

    def build(self) -> ft.Control:
        marca = ft.Container(
            content=ft.Row([
                ft.Container(ft.Icon(ft.Icons.PETS, color=tema.LATERAL, size=22), width=40, height=40,
                             bgcolor="#7FD1C3", border_radius=ft.BorderRadius.all(10), alignment=ft.Alignment.CENTER),
                ft.Column([ft.Text("VetSys", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                           ft.Text("Clínicas y laboratorio", size=11, color=tema.LATERAL_TEXTO)], spacing=0),
            ], spacing=12),
            padding=ft.Padding.only(left=20, right=20, top=22, bottom=14),
        )
        lateral = ft.Container(
            content=ft.Column([marca, self.menu], spacing=0, expand=True),
            width=250, bgcolor=tema.LATERAL,
        )
        self.operador.prefix_icon = ft.Icons.BADGE_OUTLINED
        barra = ft.Container(
            content=ft.Row([self.ubicacion, ft.Container(expand=True), self.operador,
                            ft.Row([self.icono_modo, self.modo_oscuro], spacing=4)],
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=10, horizontal=32), bgcolor=tema.SUPERFICIE,
            border=ft.Border(bottom=ft.BorderSide(1, tema.BORDE)),
        )
        principal = ft.Column([barra, self.aviso_base_vacia, self.area], expand=True, spacing=0)
        return ft.Row([lateral, principal], expand=True, spacing=0)

    def _armar_menu(self) -> None:
        controles: list[ft.Control] = []
        grupo_actual = ""
        for clave, pantalla in self._pantallas.items():
            if pantalla.grupo != grupo_actual:
                grupo_actual = pantalla.grupo
                controles.append(ft.Container(
                    ft.Text(grupo_actual.upper(), size=11, weight=ft.FontWeight.W_600, color="#6FA39B"),
                    padding=ft.Padding.only(left=12, top=16, bottom=4)))
            elegida = clave == self._actual
            color = ft.Colors.WHITE if elegida else tema.LATERAL_TEXTO
            controles.append(ft.ListTile(
                leading=ft.Icon(pantalla.icono, color="#7FD1C3" if elegida else tema.LATERAL_TEXTO, size=20),
                title=ft.Text(pantalla.titulo, color=color,
                              weight=ft.FontWeight.W_600 if elegida else ft.FontWeight.NORMAL),
                dense=True, selected=elegida, on_click=partial(self.ir_a, clave),
                selected_tile_color=tema.LATERAL_ACTIVO, hover_color="#0F4A46",
                shape=ft.RoundedRectangleBorder(radius=8)))
        self.menu.controls = controles

    def _armar_ubicacion(self, pantalla: Pantalla) -> None:
        """La «miga de pan» de la barra superior: grupo › pantalla."""
        self.ubicacion.controls = [
            ft.Icon(pantalla.icono, color=tema.PRIMARIO, size=20),
            tema.texto_tenue(pantalla.grupo, 14),
            tema.texto_tenue("›", 14),
            ft.Text(pantalla.titulo, size=14, weight=ft.FontWeight.W_600, color=tema.TEXTO),
        ]

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
        self._armar_ubicacion(pantalla)
        pantalla.al_mostrar()

    # ----------------------------------------------------------- modo claro / oscuro

    def _al_cambiar_modo(self) -> None:
        oscuro = bool(self.modo_oscuro.value)
        tema.cambiar_modo(self._page, oscuro)
        self.icono_modo.icon = ft.Icons.DARK_MODE_OUTLINED if oscuro else ft.Icons.LIGHT_MODE_OUTLINED
        self._page.update()

    # ----------------------------------------------------------- base vacía

    def _revisar_base(self) -> None:
        """Sin clínicas no se puede operar: se ofrece cargar los datos de prueba."""
        vacia = arranque.base_vacia()
        self.aviso_base_vacia.visible = vacia
        if vacia:
            fondo, color = tema.TONOS["progreso"]
            self.aviso_base_vacia.content = ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=color),
                ft.Text("La base de datos está vacía: faltan clínicas, veterinarios y análisis.", color=color,
                        weight=ft.FontWeight.W_500, expand=True),
                c.boton("Cargar datos de prueba", ft.Icons.DOWNLOAD_OUTLINED, self._cargar_datos_de_prueba, "secundario"),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
            self.aviso_base_vacia.bgcolor = fondo
            self.aviso_base_vacia.padding = ft.Padding.symmetric(vertical=10, horizontal=32)

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

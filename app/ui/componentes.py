"""Controles reutilizables: campos de texto, listas desplegables, botones y tablas."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

import flet as ft

from app.ui import entradas, etiquetas, tema

Opcion = tuple[str, str]  # (clave, texto que se muestra)

# Mismo aspecto para campos de texto y listas desplegables.
_ESTILO_CAMPO: dict[str, Any] = dict(border_radius=8, border_color=tema.BORDE, focused_border_color=tema.PRIMARIO,
                                     filled=True, fill_color=tema.SUPERFICIE)
_FORMA_BOTON = ft.RoundedRectangleBorder(radius=8)
_RELLENO_BOTON = ft.Padding.symmetric(vertical=14, horizontal=18)


def campo(etiqueta: str, valor: str = "", *, ancho: int | None = None, expandir: bool = False,
          sugerencia: str | None = None, multilinea: bool = False, solo_lectura: bool = False,
          al_enviar: Callable[[], None] | None = None) -> ft.TextField:
    return ft.TextField(
        label=etiqueta, value=valor, width=ancho, expand=expandir, hint_text=sugerencia,
        multiline=multilinea, min_lines=2 if multilinea else None, max_lines=4 if multilinea else None,
        read_only=solo_lectura, on_submit=al_enviar, dense=True, **_ESTILO_CAMPO,
    )


def desplegable(etiqueta: str, *, ancho: int | None = None, expandir: bool = False,
                al_elegir: Callable[[], None] | None = None) -> ft.Dropdown:
    return ft.Dropdown(label=etiqueta, options=[], width=ancho, expand=expandir, on_select=al_elegir, dense=True,
                       **_ESTILO_CAMPO)


def poner_opciones(lista: ft.Dropdown, opciones: Iterable[Opcion], conservar: bool = False) -> None:
    """Reemplaza las opciones de una lista desplegable. Con `conservar`, mantiene la selección
    si sigue existiendo; si no, la deja sin elegir."""
    pares = list(opciones)
    anterior = lista.value
    lista.options = [ft.DropdownOption(key=clave, text=texto) for clave, texto in pares]
    lista.value = anterior if conservar and any(clave == anterior for clave, _ in pares) else None


def clave_de(lista: ft.Dropdown) -> int | None:
    """El id elegido en una lista desplegable (las claves son ids como texto), o None."""
    return int(lista.value) if lista.value else None


def texto_elegido(lista: ft.Dropdown) -> str | None:
    return lista.value or None


def boton(texto: str, icono: ft.IconData | None, al_hacer_clic: Callable[[], None],
          estilo: str = "primario", visible: bool = True) -> ft.Control:
    """Botones de la aplicación. `estilo`: primario, secundario, peligro o texto."""
    if estilo == "secundario":
        return ft.OutlinedButton(texto, icon=icono, on_click=al_hacer_clic, visible=visible, style=ft.ButtonStyle(
            shape=_FORMA_BOTON, padding=_RELLENO_BOTON, color=tema.PRIMARIO, icon_color=tema.PRIMARIO,
            side=ft.BorderSide(1, tema.PRIMARIO)))
    if estilo == "peligro":
        color = tema.TONOS["peligro"][1]
        return ft.OutlinedButton(texto, icon=icono, on_click=al_hacer_clic, visible=visible, style=ft.ButtonStyle(
            shape=_FORMA_BOTON, padding=_RELLENO_BOTON, color=color, icon_color=color, side=ft.BorderSide(1, color)))
    if estilo == "texto":
        return ft.TextButton(texto, icon=icono, on_click=al_hacer_clic, visible=visible,
                             style=ft.ButtonStyle(shape=_FORMA_BOTON, color=tema.PRIMARIO, icon_color=tema.PRIMARIO))
    return ft.Button(texto, icon=icono, on_click=al_hacer_clic, visible=visible, style=ft.ButtonStyle(
        shape=_FORMA_BOTON, padding=_RELLENO_BOTON, bgcolor=tema.PRIMARIO, color=tema.SOBRE_PRIMARIO,
        icon_color=tema.SOBRE_PRIMARIO, elevation=0))


class Tabla:
    """Una tabla de solo lectura. Cada fila tiene una clave (normalmente un id) y, si se pasa
    `al_elegir`, un botón que llama a esa función con la clave de la fila.

    Las celdas cuyo texto es un estado conocido (etiquetas.TONO_DE_ESTADO) se dibujan como
    insignias de color; así el estado se lee de un vistazo en todas las pantallas."""

    def __init__(self, columnas: list[str], al_elegir: Callable[[Any], None] | None = None,
                 texto_boton: str = "Elegir", icono: ft.IconData = ft.Icons.EDIT_OUTLINED,
                 vacia: str = "No hay resultados.", altura_maxima: int = 260) -> None:
        self._al_elegir = al_elegir
        self._altura_maxima = altura_maxima
        self._texto_boton = texto_boton
        self._icono = icono
        self._textos: list[list[str]] = []
        encabezados = [ft.DataColumn(ft.Text(c.upper(), size=12, weight=ft.FontWeight.W_600, color=tema.TEXTO_TENUE))
                       for c in columnas]
        if al_elegir:
            encabezados.append(ft.DataColumn(ft.Text("")))
        self._tabla = ft.DataTable(
            columns=encabezados, rows=[], column_spacing=24, heading_row_height=40, data_row_min_height=44,
            divider_thickness=0.5, heading_row_color=tema.CABECERA_TABLA,
            data_row_color={ft.ControlState.HOVERED: tema.PRIMARIO_SUAVE}, visible=False)
        # La tabla scrollea por dentro cuando tiene muchas filas, para no empujar el resto de la pantalla.
        # Si la tabla es más ancha que la pantalla, scrollea hacia los costados en lugar de apretar las columnas.
        self._marco = ft.Column([ft.Row([self._tabla], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO, spacing=0)
        self._borde = ft.Container(self._marco, border=ft.Border.all(1, tema.BORDE), visible=False,
                                   border_radius=ft.BorderRadius.all(10), clip_behavior=ft.ClipBehavior.ANTI_ALIAS)
        self._hay_texto_vacia = bool(vacia)
        self._vacia = ft.Container(
            ft.Row([ft.Icon(ft.Icons.INBOX_OUTLINED, size=18, color=tema.TEXTO_TENUE), tema.texto_tenue(vacia, 13)]),
            padding=ft.Padding.symmetric(vertical=10, horizontal=12), bgcolor=tema.CABECERA_TABLA,
            border_radius=ft.BorderRadius.all(10), visible=self._hay_texto_vacia)
        self.vista = ft.Column([self._borde, self._vacia], spacing=4)

    def cargar(self, filas: Iterable[tuple[Any, list[str]]]) -> None:
        """`filas`: pares (clave, textos de las celdas)."""
        filas = list(filas)
        self._textos = [list(textos) for _, textos in filas]
        self._tabla.rows = [self._fila(clave, textos) for clave, textos in filas]
        self._tabla.visible = self._borde.visible = bool(filas)
        self._vacia.visible = not filas and self._hay_texto_vacia
        self._marco.height = min(len(filas) * 48 + 44, self._altura_maxima) if filas else None

    def _fila(self, clave: Any, textos: list[str]) -> ft.DataRow:
        celdas = [ft.DataCell(self._celda(texto)) for texto in textos]
        if self._al_elegir:
            # partial (y no un lambda con valor por defecto): Flet le pasaría el evento al lambda.
            celdas.append(ft.DataCell(ft.IconButton(
                self._icono, tooltip=self._texto_boton, icon_color=tema.PRIMARIO,
                on_click=partial(self._al_elegir, clave))))
        return ft.DataRow(cells=celdas)

    @staticmethod
    def _celda(texto: str) -> ft.Control:
        tono = etiquetas.TONO_DE_ESTADO.get(texto)
        return tema.insignia(texto, tono) if tono else ft.Text(texto, color=tema.TEXTO)

    @property
    def cantidad(self) -> int:
        return len(self._tabla.rows)

    def textos(self) -> list[list[str]]:
        """Los textos de cada fila tal como se cargaron (para leer la tabla sin mirar los controles)."""
        return [list(t) for t in self._textos]


def linea_de_tiempo(cambios) -> ft.Column:
    """La trazabilidad de una muestra: un renglón por cada cambio de estado, del más viejo al
    más nuevo, unidos por una línea vertical. `cambios` son los CambioEstado que devuelven los servicios."""
    cambios = list(cambios)
    renglones: list[ft.Control] = []
    for i, cambio in enumerate(cambios):
        rechazo = cambio.nuevo == "RECHAZADA"
        ultimo = i == len(cambios) - 1
        detalle = [f"{entradas.en_texto(cambio.fecha_hora)} · {cambio.responsable}"
                   + (f" · {cambio.ubicacion}" if cambio.ubicacion else "")]
        if cambio.motivos:
            detalle.append("Motivo: " + etiquetas.motivos(m.value for m in cambio.motivos))
        if cambio.observacion:
            detalle.append(cambio.observacion)
        nombre = "Extracción" if cambio.anterior is None else etiquetas.estado_muestra(cambio.nuevo)
        fondo, color = tema.TONOS["peligro" if rechazo else ("ok" if ultimo else "info")]
        punto = ft.Container(
            ft.Icon(ft.Icons.CLOSE if rechazo else ft.Icons.CHECK, size=14, color=color),
            width=26, height=26, bgcolor=fondo, border=ft.Border.all(2, color),
            border_radius=ft.BorderRadius.all(13), alignment=ft.Alignment.CENTER)
        # La línea baja hasta el próximo cambio; su alto acompaña las líneas de detalle.
        conector = ft.Container(width=2, height=18 * len(detalle) + 6, bgcolor=tema.BORDE, visible=not ultimo)
        renglones.append(ft.Row([
            ft.Column([punto, conector], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column([
                ft.Text(nombre, weight=ft.FontWeight.W_600, color=tema.TEXTO),
                *[tema.texto_tenue(linea, 12) for linea in detalle],
            ], spacing=1),
        ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=12))
    return ft.Column(renglones, spacing=2)

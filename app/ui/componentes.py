"""Controles reutilizables: campos de texto, listas desplegables, botones y tablas."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

import flet as ft

from app.ui import entradas, etiquetas, tema

Opcion = tuple[str, str]  # (clave, texto que se muestra)


def campo(etiqueta: str, valor: str = "", *, ancho: int | None = None, expandir: bool = False,
          sugerencia: str | None = None, multilinea: bool = False, solo_lectura: bool = False,
          al_enviar: Callable[[], None] | None = None) -> ft.TextField:
    return ft.TextField(
        label=etiqueta, value=valor, width=ancho, expand=expandir, hint_text=sugerencia,
        multiline=multilinea, min_lines=2 if multilinea else None, max_lines=4 if multilinea else None,
        read_only=solo_lectura, on_submit=al_enviar, dense=True,
    )


def desplegable(etiqueta: str, *, ancho: int | None = None, expandir: bool = False,
                al_elegir: Callable[[], None] | None = None) -> ft.Dropdown:
    return ft.Dropdown(label=etiqueta, options=[], width=ancho, expand=expandir, on_select=al_elegir, dense=True)


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
        return ft.OutlinedButton(texto, icon=icono, on_click=al_hacer_clic, visible=visible)
    if estilo == "peligro":
        color = ft.Colors.RED_700
        return ft.OutlinedButton(
            texto, icon=icono, on_click=al_hacer_clic, visible=visible,
            style=ft.ButtonStyle(color=color, icon_color=color, side=ft.BorderSide(1, color)))
    if estilo == "texto":
        return ft.TextButton(texto, icon=icono, on_click=al_hacer_clic, visible=visible)
    return ft.Button(texto, icon=icono, on_click=al_hacer_clic, visible=visible)


class Tabla:
    """Una tabla de solo lectura. Cada fila tiene una clave (normalmente un id) y, si se pasa
    `al_elegir`, un botón que llama a esa función con la clave de la fila."""

    def __init__(self, columnas: list[str], al_elegir: Callable[[Any], None] | None = None,
                 texto_boton: str = "Elegir", icono: ft.IconData = ft.Icons.EDIT_OUTLINED,
                 vacia: str = "No hay resultados.", altura_maxima: int = 230) -> None:
        self._al_elegir = al_elegir
        self._altura_maxima = altura_maxima
        self._texto_boton = texto_boton
        self._icono = icono
        encabezados = [ft.DataColumn(ft.Text(c, weight=ft.FontWeight.W_600)) for c in columnas]
        if al_elegir:
            encabezados.append(ft.DataColumn(ft.Text("")))
        self._tabla = ft.DataTable(
            columns=encabezados, rows=[], column_spacing=22, heading_row_height=40,
            data_row_min_height=40, divider_thickness=0.5, visible=False)
        self._vacia = tema.texto_tenue(vacia, 13)
        # La tabla scrollea por dentro cuando tiene muchas filas, para no empujar el resto de la pantalla.
        self._marco = ft.Column([self._tabla], scroll=ft.ScrollMode.AUTO, spacing=0)
        self.vista = ft.Column([self._marco, self._vacia], spacing=4)

    def cargar(self, filas: Iterable[tuple[Any, list[str]]]) -> None:
        """`filas`: pares (clave, textos de las celdas)."""
        filas = list(filas)
        self._tabla.rows = [self._fila(clave, textos) for clave, textos in filas]
        self._tabla.visible = bool(filas)
        self._vacia.visible = not filas
        self._marco.height = min(len(filas) * 48 + 44, self._altura_maxima) if filas else None

    def _fila(self, clave: Any, textos: list[str]) -> ft.DataRow:
        celdas = [ft.DataCell(ft.Text(texto)) for texto in textos]
        if self._al_elegir:
            # partial (y no un lambda con valor por defecto): Flet le pasaría el evento al lambda.
            celdas.append(ft.DataCell(ft.IconButton(
                self._icono, tooltip=self._texto_boton, on_click=partial(self._al_elegir, clave))))
        return ft.DataRow(cells=celdas)

    @property
    def cantidad(self) -> int:
        return len(self._tabla.rows)


def linea_de_tiempo(cambios) -> ft.Column:
    """La trazabilidad de una muestra: un renglón por cada cambio de estado, del más viejo al
    más nuevo. `cambios` son los CambioEstado que devuelven los servicios."""
    renglones: list[ft.Control] = []
    for cambio in cambios:
        rechazo = cambio.nuevo == "RECHAZADA"
        detalle = [f"{entradas.en_texto(cambio.fecha_hora)} · {cambio.responsable}"
                   + (f" · {cambio.ubicacion}" if cambio.ubicacion else "")]
        if cambio.motivos:
            detalle.append("Motivo: " + etiquetas.motivos(m.value for m in cambio.motivos))
        if cambio.observacion:
            detalle.append(cambio.observacion)
        renglones.append(ft.Row([
            ft.Icon(ft.Icons.ERROR_OUTLINE if rechazo else ft.Icons.CHECK_CIRCLE_OUTLINE, size=20,
                    color=ft.Colors.RED_700 if rechazo else ft.Colors.TEAL_700),
            ft.Column([
                ft.Text("Extracción" if cambio.anterior is None else etiquetas.estado_muestra(cambio.nuevo),
                        weight=ft.FontWeight.W_600),
                *[tema.texto_tenue(linea, 12) for linea in detalle],
            ], spacing=1),
        ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=10))
    return ft.Column(renglones, spacing=10)

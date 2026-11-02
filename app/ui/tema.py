"""Apariencia común de las pantallas: espaciados, títulos y tarjetas."""

from __future__ import annotations

import flet as ft

ESPACIO = 12
ESPACIO_GRANDE = 20


def aplicar_tema(page: ft.Page, titulo: str) -> None:
    page.title = titulo
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    page.padding = 0


def texto_tenue(texto: str, size: int = 12) -> ft.Text:
    return ft.Text(texto, size=size, color=ft.Colors.ON_SURFACE_VARIANT)


def titulo_pantalla(titulo: str, subtitulo: str = "") -> ft.Column:
    controles: list[ft.Control] = [ft.Text(titulo, size=26, weight=ft.FontWeight.BOLD)]
    if subtitulo:
        controles.append(texto_tenue(subtitulo, 13))
    return ft.Column(controles, spacing=2)


def seccion(titulo: ft.Text | str, *controles: ft.Control) -> ft.Container:
    """Una tarjeta con borde y un título, que agrupa controles relacionados."""
    encabezado = titulo if isinstance(titulo, ft.Text) else ft.Text(titulo, size=15, weight=ft.FontWeight.W_600)
    return ft.Container(
        content=ft.Column([encabezado, *controles], spacing=ESPACIO),
        padding=ft.Padding.all(16),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=ft.BorderRadius.all(8),
    )


def fila(*controles: ft.Control) -> ft.Row:
    """Controles uno al lado del otro; los que tienen `expand` se reparten el ancho."""
    return ft.Row(list(controles), spacing=ESPACIO, vertical_alignment=ft.CrossAxisAlignment.START)


def pagina(*controles: ft.Control) -> ft.Column:
    """La columna principal de una pantalla, con scroll por si el contenido no entra."""
    return ft.Column(list(controles), spacing=ESPACIO_GRANDE, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

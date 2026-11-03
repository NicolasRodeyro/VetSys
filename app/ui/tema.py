"""Apariencia común de las pantallas: paleta, espaciados, títulos, tarjetas e insignias.

Todos los colores salen de acá: si se quiere cambiar el aspecto de la aplicación, se cambia
este módulo y no cada pantalla.
"""

from __future__ import annotations

import flet as ft

ESPACIO = 12
ESPACIO_GRANDE = 20
RADIO = 12

# --- Paleta -----------------------------------------------------------------
# Las pantallas usan colores *del tema* (nombres como "primary" o "surface"), no valores fijos:
# Flet los resuelve al dibujar según el modo activo. Así, cambiar entre modo claro y oscuro es
# solo cambiar `page.theme_mode`, sin reconstruir ninguna pantalla.
PRIMARIO = ft.Colors.PRIMARY                    # botones, foco, selección
SOBRE_PRIMARIO = ft.Colors.ON_PRIMARY           # texto sobre un botón primario
PRIMARIO_SUAVE = ft.Colors.PRIMARY_CONTAINER    # fondo de lo seleccionado
FONDO = ft.Colors.SURFACE_CONTAINER_LOW         # fondo de la ventana (las tarjetas van encima)
SUPERFICIE = ft.Colors.SURFACE                  # tarjetas, barra superior, campos
BORDE = ft.Colors.OUTLINE_VARIANT
TEXTO = ft.Colors.ON_SURFACE
TEXTO_TENUE = ft.Colors.ON_SURFACE_VARIANT
CABECERA_TABLA = ft.Colors.SURFACE_CONTAINER

# El menú lateral es oscuro en los dos modos.
LATERAL = "#0B3B38"
LATERAL_TEXTO = "#B8D4CF"
LATERAL_ACTIVO = "#14524D"

# Valores concretos de cada modo: (claro, oscuro)
_PALETAS: dict[str, tuple[str, str]] = {
    "primary": ("#0F766E", "#5EC4B6"),
    "on_primary": ("#FFFFFF", "#00302B"),
    "primary_container": ("#E6F4F1", "#163F3B"),
    "on_primary_container": ("#0B3B38", "#C8EDE7"),
    "surface_container_low": ("#F3F6F5", "#101615"),
    "surface": ("#FFFFFF", "#18201F"),
    "outline_variant": ("#DDE5E3", "#2F3B39"),
    "on_surface": ("#1E2A28", "#E2EAE8"),
    "on_surface_variant": ("#5F6F6C", "#9DB0AC"),
    "surface_container": ("#F6F9F8", "#1F2927"),
}

# Tonos de las insignias de estado: (fondo, texto)
TONOS: dict[str, tuple[str, str]] = {
    "neutro": ("#EEF1F0", "#4B5A57"),
    "info": ("#E3EEFB", "#1D4F91"),
    "progreso": ("#FDF1DC", "#8A5300"),
    "ok": ("#E1F3E8", "#1B6B3A"),
    "peligro": ("#FBE4E2", "#A1261B"),
}


def _tema(oscuro: bool) -> ft.Theme:
    colores = {nombre: valores[1 if oscuro else 0] for nombre, valores in _PALETAS.items()}
    return ft.Theme(
        color_scheme_seed=_PALETAS["primary"][0],
        color_scheme=ft.ColorScheme(**colores),
        scaffold_bgcolor=colores["surface_container_low"],
        divider_color=colores["outline_variant"],
    )


def aplicar_tema(page: ft.Page, titulo: str) -> None:
    page.title = titulo
    page.theme = _tema(oscuro=False)
    page.dark_theme = _tema(oscuro=True)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = FONDO
    page.padding = 0


def es_oscuro(page: ft.Page) -> bool:
    return page.theme_mode == ft.ThemeMode.DARK


def cambiar_modo(page: ft.Page, oscuro: bool) -> None:
    """Pasa de modo claro a oscuro (o al revés). Las pantallas no se reconstruyen: sus colores
    son del tema y se vuelven a resolver al redibujar."""
    page.theme_mode = ft.ThemeMode.DARK if oscuro else ft.ThemeMode.LIGHT


def texto_tenue(texto: str, size: int = 12) -> ft.Text:
    return ft.Text(texto, size=size, color=TEXTO_TENUE)


def insignia(texto: str, tono: str = "neutro") -> ft.Container:
    """Una etiqueta redondeada de color, para mostrar un estado de un vistazo."""
    fondo, color = TONOS.get(tono, TONOS["neutro"])
    return ft.Container(
        content=ft.Text(texto, size=12, weight=ft.FontWeight.W_600, color=color),
        bgcolor=fondo, border_radius=ft.BorderRadius.all(20),
        padding=ft.Padding.symmetric(vertical=3, horizontal=10),
    )


def titulo_pantalla(titulo: str, subtitulo: str = "") -> ft.Column:
    controles: list[ft.Control] = [ft.Text(titulo, size=26, weight=ft.FontWeight.BOLD, color=TEXTO)]
    if subtitulo:
        controles.append(texto_tenue(subtitulo, 14))
    return ft.Column(controles, spacing=4)


def seccion(titulo: ft.Text | str, *controles: ft.Control) -> ft.Container:
    """Una tarjeta con un título, que agrupa controles relacionados."""
    encabezado = titulo if isinstance(titulo, ft.Text) else ft.Text(titulo)
    encabezado.size = encabezado.size or 16
    encabezado.weight = ft.FontWeight.W_600
    encabezado.color = TEXTO
    return ft.Container(
        content=ft.Column([encabezado, *controles], spacing=ESPACIO),
        padding=ft.Padding.all(20),
        bgcolor=SUPERFICIE,
        border=ft.Border.all(1, BORDE),
        border_radius=ft.BorderRadius.all(RADIO),
        shadow=ft.BoxShadow(blur_radius=12, spread_radius=0, color="#0F2E2B0D", offset=ft.Offset(0, 2)),
    )


def subtitulo(texto: str) -> ft.Text:
    """El título de un bloque dentro de una tarjeta (p. ej. «Trazabilidad»)."""
    return ft.Text(texto, size=14, weight=ft.FontWeight.W_600, color=TEXTO)


def fila(*controles: ft.Control) -> ft.Row:
    """Controles uno al lado del otro; los que tienen `expand` se reparten el ancho."""
    return ft.Row(list(controles), spacing=ESPACIO, vertical_alignment=ft.CrossAxisAlignment.START)


def pagina(*controles: ft.Control) -> ft.Column:
    """La columna principal de una pantalla, con scroll por si el contenido no entra."""
    return ft.Column(list(controles), spacing=ESPACIO_GRANDE, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

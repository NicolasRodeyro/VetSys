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
PRIMARIO = "#0F766E"         # verde azulado clínico: botones, foco, selección
PRIMARIO_SUAVE = "#E6F4F1"   # fondo de lo seleccionado
LATERAL = "#0B3B38"          # menú lateral
LATERAL_TEXTO = "#B8D4CF"
LATERAL_ACTIVO = "#14524D"
FONDO = "#F3F6F5"            # fondo de la ventana (las tarjetas van en blanco encima)
SUPERFICIE = "#FFFFFF"
BORDE = "#DDE5E3"
TEXTO = "#1E2A28"
TEXTO_TENUE = "#5F6F6C"
CABECERA_TABLA = "#F6F9F8"

# Tonos de las insignias de estado: (fondo, texto)
TONOS: dict[str, tuple[str, str]] = {
    "neutro": ("#EEF1F0", "#4B5A57"),
    "info": ("#E3EEFB", "#1D4F91"),
    "progreso": ("#FDF1DC", "#8A5300"),
    "ok": ("#E1F3E8", "#1B6B3A"),
    "peligro": ("#FBE4E2", "#A1261B"),
}


def aplicar_tema(page: ft.Page, titulo: str) -> None:
    page.title = titulo
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARIO,
        color_scheme=ft.ColorScheme(primary=PRIMARIO, on_surface=TEXTO, on_surface_variant=TEXTO_TENUE,
                                    outline_variant=BORDE, surface=SUPERFICIE),
        scaffold_bgcolor=FONDO,
        divider_color=BORDE,
    )
    page.bgcolor = FONDO
    page.padding = 0


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
    """Una tarjeta blanca con un título, que agrupa controles relacionados."""
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

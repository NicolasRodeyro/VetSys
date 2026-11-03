"""Mensajes al usuario: éxito y error en una barra flotante, avisos importantes en un diálogo."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

import flet as ft


class Mensajero(Protocol):
    """Lo que las pantallas necesitan para hablarle al usuario. En la aplicación lo implementa
    MensajeroFlet; en los tests, un objeto que guarda los mensajes."""

    def exito(self, texto: str) -> None: ...
    def error(self, texto: str) -> None: ...
    def aviso(self, titulo: str, lineas: Iterable[str]) -> None: ...


class MensajeroFlet:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

    def _barra(self, texto: str, icono: ft.IconData, color: str, segundos: int) -> None:
        self._page.show_dialog(ft.SnackBar(
            ft.Row([ft.Icon(icono, color=ft.Colors.WHITE, size=20),
                    ft.Text(texto, color=ft.Colors.WHITE, expand=True)], spacing=10),
            bgcolor=color, duration=segundos * 1000, show_close_icon=True, close_icon_color=ft.Colors.WHITE,
            behavior=ft.SnackBarBehavior.FLOATING, width=560,
            shape=ft.RoundedRectangleBorder(radius=10)))

    def exito(self, texto: str) -> None:
        self._barra(texto, ft.Icons.CHECK_CIRCLE_OUTLINE, "#1B6B3A", 4)

    def error(self, texto: str) -> None:
        self._barra(texto, ft.Icons.ERROR_OUTLINE, "#A1261B", 9)

    def aviso(self, titulo: str, lineas: Iterable[str]) -> None:
        """Un diálogo que hay que aceptar: para lo que no se puede pasar por alto
        (vacunas pendientes, muestras rechazadas)."""
        self._page.show_dialog(ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=14),
            title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_800), ft.Text(titulo, size=18)]),
            content=ft.Column([ft.Row([ft.Text("•"), ft.Text(linea, expand=True)], vertical_alignment=ft.CrossAxisAlignment.START)
                               for linea in lineas], tight=True, spacing=8, width=460),
            actions=[ft.Button("Entendido", on_click=self._page.pop_dialog)],
        ))

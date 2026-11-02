"""Mensajes al usuario: éxito y error en una barra inferior, avisos importantes en un diálogo."""

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

    def _barra(self, texto: str, color: str, segundos: int) -> None:
        self._page.show_dialog(ft.SnackBar(
            ft.Text(texto, color=ft.Colors.WHITE), bgcolor=color, duration=segundos * 1000, show_close_icon=True))

    def exito(self, texto: str) -> None:
        self._barra(texto, ft.Colors.GREEN_700, 4)

    def error(self, texto: str) -> None:
        self._barra(texto, ft.Colors.RED_700, 9)

    def aviso(self, titulo: str, lineas: Iterable[str]) -> None:
        """Un diálogo que hay que aceptar: para lo que no se puede pasar por alto
        (vacunas pendientes, muestras rechazadas)."""
        self._page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_800), ft.Text(titulo)]),
            content=ft.Column([ft.Text(linea) for linea in lineas], tight=True, spacing=8),
            actions=[ft.Button("Entendido", on_click=self._page.pop_dialog)],
        ))

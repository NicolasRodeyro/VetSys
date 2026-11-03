"""Selector de fecha y hora: un calendario y, al lado, un reloj.

Reemplaza al campo donde se escribía «AAAA-MM-DD HH:MM»: no se puede escribir un formato mal,
se elige. Los dos campos son de solo lectura; al tocarlos se abre el calendario o el selector de
hora de Flet. El valor se guarda como `date` y `time` (no como texto) y se junta en `valor`.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import flet as ft

from app.servicios import tiempo
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c

_ANIOS_HACIA_ADELANTE = 3


def a_fecha_local(valor: date | datetime) -> date:
    """La fecha que devuelve el calendario de Flet, como `date` del día elegido.

    Si trae zona horaria (UTC), se pasa a la hora local antes de quedarse con el día: si no, en
    algunos husos el día elegido se corre en uno.
    """
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone()
        return valor.date()
    return valor


class SelectorFechaHora:
    """Dos campos pegados: «Fecha» (calendario) y «Hora» (reloj de 24 horas)."""

    def __init__(self, etiqueta_fecha: str = "Fecha", etiqueta_hora: str = "Hora", *,
                 desde_hoy: bool = True, paso_minutos: int = 5) -> None:
        self._desde_hoy = desde_hoy
        self._paso_minutos = paso_minutos
        self._fecha: date | None = None
        self._hora: time | None = None
        self.campo_fecha = c.campo(etiqueta_fecha, ancho=170, solo_lectura=True, sugerencia="Elegir fecha")
        self.campo_hora = c.campo(etiqueta_hora, ancho=130, solo_lectura=True, sugerencia="Elegir hora")
        self.campo_fecha.suffix_icon = ft.Icons.CALENDAR_MONTH_OUTLINED
        self.campo_hora.suffix_icon = ft.Icons.ACCESS_TIME
        # En Flet un campo de solo lectura igual avisa los clics: así se abre al tocar en cualquier parte.
        self.campo_fecha.on_click = self.elegir_fecha
        self.campo_hora.on_click = self.elegir_hora
        self.vista = ft.Row([self.campo_fecha, self.campo_hora], spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.START, tight=True)

    # ------------------------------------------------------------ valor

    @property
    def fecha(self) -> date | None:
        return self._fecha

    @property
    def hora(self) -> time | None:
        return self._hora

    def poner(self, valor: datetime | None) -> None:
        """Deja elegidos fecha y hora (sin segundos). Con None, los limpia."""
        self.poner_fecha(valor.date() if valor else None)
        self.poner_hora(valor.time().replace(second=0, microsecond=0) if valor else None)

    def poner_fecha(self, fecha: date | None) -> None:
        self._fecha = fecha
        self.campo_fecha.value = f"{fecha:%d/%m/%Y}" if fecha else ""
        self.campo_fecha.error_text = None

    def poner_hora(self, hora: time | None) -> None:
        self._hora = hora
        self.campo_hora.value = f"{hora:%H:%M}" if hora else ""
        self.campo_hora.error_text = None

    def marcar_faltantes(self) -> list[str]:
        """Pone en rojo, junto al campo, lo que todavía no se eligió. Devuelve qué falta
        («la fecha», «la hora») para armar el mensaje."""
        faltan = []
        if self._fecha is None:
            self.campo_fecha.error_text = "Elegí la fecha"
            faltan.append("la fecha")
        if self._hora is None:
            self.campo_hora.error_text = "Elegí la hora"
            faltan.append("la hora")
        return faltan

    def valor(self, campo: str) -> datetime:
        """La fecha y hora elegidas juntas. `campo` ("El inicio") arma el mensaje si falta algo."""
        if self._fecha is None:
            raise EntradaInvalida(f"{campo}: elegí la fecha en el calendario.")
        if self._hora is None:
            raise EntradaInvalida(f"{campo}: elegí la hora.")
        return datetime.combine(self._fecha, self._hora)

    def poner_ahora(self) -> None:
        """Propone el momento actual, redondeado hacia adelante al próximo múltiplo del paso."""
        ahora = tiempo.ahora().replace(second=0, microsecond=0)
        resto = ahora.minute % self._paso_minutos
        if resto:
            ahora += timedelta(minutes=self._paso_minutos - resto)
        self.poner(ahora)

    # ------------------------------------------------------------ ventanas de Flet

    def elegir_fecha(self) -> None:
        hoy = tiempo.hoy()
        elegida = self._fecha or hoy
        primera = min(hoy, elegida) if self._desde_hoy else date(hoy.year - 10, 1, 1)
        calendario = ft.DatePicker(
            value=datetime.combine(elegida, time()), first_date=datetime.combine(primera, time()),
            last_date=datetime(hoy.year + _ANIOS_HACIA_ADELANTE, 12, 31),
            help_text="Elegí la fecha", cancel_text="Cancelar", confirm_text="Aceptar",
            entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY)

        def al_cambiar() -> None:
            if calendario.value is not None:
                self.poner_fecha(a_fecha_local(calendario.value))
                self.campo_fecha.update()

        calendario.on_change = al_cambiar
        self.campo_fecha.page.show_dialog(calendario)

    def elegir_hora(self) -> None:
        reloj = ft.TimePicker(
            value=self._hora or time(9, 0), hour_format=ft.TimePickerHourFormat.H24,
            help_text="Elegí la hora", cancel_text="Cancelar", confirm_text="Aceptar",
            hour_label_text="Hora", minute_label_text="Minutos", error_invalid_text="Hora no válida",
            entry_mode=ft.TimePickerEntryMode.DIAL)

        def al_cambiar() -> None:
            if reloj.value is not None:
                self.poner_hora(reloj.value.replace(second=0, microsecond=0))
                self.campo_hora.update()

        reloj.on_change = al_cambiar
        self.campo_hora.page.show_dialog(reloj)

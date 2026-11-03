"""Selector de fecha y hora: dos campos pegados que abren un calendario y un reloj.

Los campos son de solo lectura (no se puede escribir un formato mal). El valor no es texto:
se guarda como `date` y `time` y se junta con `datetime.combine`, así no hay nada que parsear.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import flet as ft

from app.servicios import tiempo
from app.ui import componentes as c
from app.ui.pantalla import Pantalla, manejador

ES = ft.Locale("es")
MINUTOS_REDONDEO = 5
ANIOS_HACIA_ADELANTE = 3

AVISO_FECHA = "Elegí la fecha"
AVISO_HORA = "Elegí la hora"


def redondear_adelante(momento: datetime, minutos: int = MINUTOS_REDONDEO) -> datetime:
    """El próximo múltiplo de `minutos` (el mismo momento si ya lo es). Sin segundos."""
    base = momento.replace(second=0, microsecond=0)
    resto = base.minute % minutos
    if resto == 0 and base == momento:
        return base
    return base + timedelta(minutes=(minutos - resto) if resto else minutos)


def _en_tres_anios(desde: date) -> date:
    try:
        return desde.replace(year=desde.year + ANIOS_HACIA_ADELANTE)
    except ValueError:  # 29 de febrero
        return desde.replace(year=desde.year + ANIOS_HACIA_ADELANTE, day=28)


def dia_local(valor: datetime | date) -> date:
    """El día que eligió el usuario. Si Flet devuelve una fecha con huso horario, se pasa
    primero a hora local: así el día no se corre según el huso."""
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone()
        return valor.date()
    return valor


class SelectorFechaHora:
    """«Fecha del turno» (calendario) y «Hora» (reloj de 24 horas), uno al lado del otro."""

    def __init__(self, pantalla: Pantalla, etiqueta_fecha: str = "Fecha del turno",
                 al_cambiar=None) -> None:
        self._pantalla = pantalla
        self._al_cambiar = al_cambiar
        self._fecha: date | None = None
        self._hora: time | None = None
        self.fecha = c.campo(etiqueta_fecha, ancho=190, solo_lectura=True, sugerencia="Tocá para elegir")
        self.hora = c.campo("Hora", ancho=120, solo_lectura=True, sugerencia="HH:MM")
        self.fecha.suffix_icon = ft.Icons.CALENDAR_MONTH_OUTLINED
        self.hora.suffix_icon = ft.Icons.SCHEDULE
        self.fecha.on_click = self.abrir_calendario
        self.hora.on_click = self.abrir_reloj
        self.vista = ft.Row([self.fecha, self.hora], spacing=4, vertical_alignment=ft.CrossAxisAlignment.START)

    # ----------------------------------------------------------- valor

    @property
    def fecha_elegida(self) -> date | None:
        return self._fecha

    @property
    def hora_elegida(self) -> time | None:
        return self._hora

    @property
    def valor(self) -> datetime | None:
        """La fecha y la hora juntas, o None si falta alguna."""
        if self._fecha is None or self._hora is None:
            return None
        return datetime.combine(self._fecha, self._hora)

    def poner_fecha(self, fecha: date | None) -> None:
        self._fecha = fecha
        self.fecha.value = f"{fecha:%d/%m/%Y}" if fecha else ""
        if fecha:
            self.fecha.error = None

    def poner_hora(self, hora: time | None) -> None:
        self._hora = hora.replace(second=0, microsecond=0) if hora else None
        self.hora.value = f"{self._hora:%H:%M}" if self._hora else ""
        if hora:
            self.hora.error = None

    def poner(self, momento: datetime) -> None:
        self.poner_fecha(momento.date())
        self.poner_hora(momento.time())

    def poner_ahora(self) -> None:
        """Propone el momento actual, redondeado hacia adelante a múltiplos de 5 minutos."""
        self.poner(redondear_adelante(tiempo.ahora()))

    def vacio(self) -> bool:
        return self._fecha is None and self._hora is None

    # ----------------------------------------------------------- avisos

    def faltantes(self) -> list[str]:
        faltan = []
        if self._fecha is None:
            faltan.append("la fecha")
        if self._hora is None:
            faltan.append("la hora")
        return faltan

    def marcar_faltantes(self) -> None:
        """Pinta de rojo el campo que no se eligió."""
        self.fecha.error = AVISO_FECHA if self._fecha is None else None
        self.hora.error = AVISO_HORA if self._hora is None else None

    def limpiar_avisos(self) -> None:
        self.fecha.error = self.hora.error = None

    # ----------------------------------------------------------- calendario y reloj

    def _mostrar(self, dialogo: ft.DialogControl) -> None:
        ft.context.page.show_dialog(dialogo)

    @manejador
    def abrir_calendario(self) -> None:
        hoy = tiempo.hoy()
        inicial = self._fecha if self._fecha and self._fecha >= hoy else hoy
        calendario = ft.DatePicker(
            value=datetime.combine(inicial, time()), first_date=datetime.combine(hoy, time()),
            last_date=datetime.combine(_en_tres_anios(hoy), time()), locale=ES,
            help_text="Fecha del turno", cancel_text="Cancelar", confirm_text="Aceptar")
        calendario.on_change = lambda: self.elegir_fecha(calendario.value)
        self._mostrar(calendario)

    @manejador
    def abrir_reloj(self) -> None:
        reloj = ft.TimePicker(
            value=self._hora or tiempo.ahora().time().replace(second=0, microsecond=0), locale=ES,
            hour_format=ft.TimePickerHourFormat.H24, help_text="Hora del turno",
            cancel_text="Cancelar", confirm_text="Aceptar", hour_label_text="Hora", minute_label_text="Minutos")
        reloj.on_change = lambda: self.elegir_hora(reloj.value)
        self._mostrar(reloj)

    @manejador
    def elegir_fecha(self, valor: datetime | date | None) -> None:
        if valor is not None:
            self.poner_fecha(dia_local(valor))
            self._avisar_cambio()

    @manejador
    def elegir_hora(self, valor: time | None) -> None:
        if valor is not None:
            self.poner_hora(valor)
            self._avisar_cambio()

    def _avisar_cambio(self) -> None:
        if self._al_cambiar:
            self._al_cambiar()

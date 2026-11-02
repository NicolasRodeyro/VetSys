"""Pantalla de recepción en el laboratorio (proceso 6): por cada conservadora se registra el estado
del precinto y la temperatura de llegada; el sistema decide si se acepta o se rechaza."""

from __future__ import annotations

import flet as ft

from app.servicios import remitos as svc
from app.servicios.excepciones import EntradaInvalida
from app.servicios.remitos import DetalleDeRecepcion
from app.ui import componentes as c
from app.ui import etiquetas, tema
from app.ui.pantalla import Pantalla, manejador

PRECINTOS = [("INTACTO", "Intacto"), ("ROTO", "Roto")]


class _FilaDeConservadora:
    """Los controles que se completan para UNA conservadora del remito."""

    def __init__(self, conservadora) -> None:
        self.conservadora_id = conservadora.id
        self.titulo = f"{conservadora.codigo} · {len(conservadora.muestras)} muestra(s) · debe llegar entre {conservadora.temp_min:g} y {conservadora.temp_max:g} °C"
        self.precinto = c.desplegable("Precinto", ancho=160)
        c.poner_opciones(self.precinto, PRECINTOS)
        self.precinto.value = "INTACTO"
        self.temperatura = c.campo("Temperatura (°C)", ancho=200)
        self.observacion = c.campo("Observación", expandir=True)

    def vista(self) -> ft.Control:
        return ft.Container(
            ft.Column([ft.Text(self.titulo, weight=ft.FontWeight.W_600),
                       tema.fila(self.precinto, self.temperatura, self.observacion)], spacing=8),
            padding=ft.Padding.all(12), border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.BorderRadius.all(8))

    def detalle(self) -> DetalleDeRecepcion:
        return DetalleDeRecepcion(self.conservadora_id, self.precinto.value or "", self.temperatura.value or "",
                                  self.observacion.value or "")


class PantallaRecepcion(Pantalla):
    clave = "recepcion"
    titulo = "Recepción"
    icono = ft.Icons.MOVE_TO_INBOX_OUTLINED
    grupo = "Laboratorio"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._filas: list[_FilaDeConservadora] = []
        self.remito = c.desplegable("Remito en tránsito", expandir=True, al_elegir=self.elegir)
        self.filas = ft.Column(spacing=tema.ESPACIO)
        self.boton = c.boton("Registrar recepción", ft.Icons.FACT_CHECK_OUTLINED, self.registrar)
        self.formulario = tema.seccion("Constatación por conservadora", self.filas, self.boton)
        self.formulario.visible = False

    def build(self) -> ft.Control:
        return tema.pagina(
            tema.titulo_pantalla(
                "Recepción en el laboratorio",
                "Si el precinto llegó roto o la temperatura salió del rango, las muestras de esa conservadora se rechazan "
                "y se avisa a la clínica para la re-extracción."),
            tema.seccion("Remito", self.remito), self.formulario)

    @manejador
    def al_mostrar(self) -> None:
        self.cargar()

    @manejador
    def cargar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.remito, ((str(r.id), f"{r.numero} · {r.origen.nombre} → {r.destino.nombre} · "
                                           f"{len(r.conservadoras)} conservadora(s)") for r in svc.listar_remitos("EN_TRANSITO")))
            self.elegir()
        self.ejecutar(accion)

    @manejador
    def elegir(self) -> None:
        def accion() -> None:
            remito_id = c.clave_de(self.remito)
            self._filas = [_FilaDeConservadora(x) for x in svc.obtener_remito(remito_id).conservadoras] if remito_id else []
            self.filas.controls = [f.vista() for f in self._filas]
            self.formulario.visible = bool(self._filas)
        self.ejecutar(accion)

    @manejador
    def registrar(self) -> None:
        def accion() -> None:
            remito_id = c.clave_de(self.remito)
            if remito_id is None:
                raise EntradaInvalida("Elegí el remito que llegó al laboratorio.")
            self._resultado = svc.registrar_recepcion(remito_id, self.sesion.operador(), [f.detalle() for f in self._filas])
        if not self.ejecutar(accion):
            return
        recibida = self._resultado
        estado = etiquetas.estado_remito(recibida.remito.estado.nombre)
        self.cargar()
        if recibida.alertas:  # hay muestras rechazadas: la clínica tiene que coordinar la re-extracción
            self.avisar(f"Remito {recibida.remito.numero}: {estado}", recibida.alertas)
        else:
            self.sesion.mensajero.exito(f"Remito {recibida.remito.numero} recibido: todas las muestras aceptadas.")

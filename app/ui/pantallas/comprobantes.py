"""Pantalla de comprobantes (proceso 7): cerrar la consulta y emitir su único comprobante."""

from __future__ import annotations

import flet as ft

from app.servicios import consultas as svc
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import en_pesos, en_texto
from app.ui.pantalla import Pantalla, manejador
from app.ui.selectores import SelectorConsulta


class PantallaComprobantes(Pantalla):
    clave = "comprobantes"
    titulo = "Comprobantes"
    icono = ft.Icons.RECEIPT_LONG_OUTLINED
    grupo = "Atención"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self.selector = SelectorConsulta(self, self.mostrar)
        self.resumen = ft.Column(spacing=tema.ESPACIO)
        self.honorarios = c.campo("Honorarios ($)", ancho=220, sugerencia="Ej. 3000,50")
        self.tabla_items = c.Tabla(["Concepto", "Servicio", "Importe"], vacia="")
        self.total = ft.Text("", size=18, weight=ft.FontWeight.BOLD)
        self.cierre = tema.fila(self.honorarios, c.boton("Cerrar consulta y emitir comprobante", ft.Icons.TASK_ALT, self.cerrar))
        self.comprobante = tema.seccion("Comprobante", self.tabla_items.vista, self.total)
        self.comprobante.visible = False
        self.pendiente = tema.seccion("Para cerrar la consulta", self.resumen, self.cierre)
        self.pendiente.visible = False

    def build(self) -> ft.Control:
        return tema.pagina(
            tema.titulo_pantalla(
                "Comprobantes",
                "Al cerrar la consulta se emite un solo comprobante: la consulta más un ítem por cada orden de derivación. "
                "Se cobra por orden, no por muestra: una re-extracción no genera un cargo nuevo."),
            tema.seccion("Consulta", self.selector.vista), self.pendiente, self.comprobante)

    @manejador
    def mostrar(self) -> None:
        def accion() -> None:
            self.pendiente.visible = self.comprobante.visible = False
            if self.selector.consulta_id is None:
                return
            x = svc.obtener_consulta(self.selector.consulta_id)
            if x.cerrada:
                comp = x.comprobante
                self.tabla_items.cargar((i, [it.descripcion, "Laboratorio" if it.es_laboratorio else "Clínica", en_pesos(it.monto)])
                                        for i, it in enumerate(comp.items))
                self.total.value = (f"Total {en_pesos(comp.total)}  ·  emitido el {en_texto(comp.fecha_hora)}"
                                    f" a nombre de {comp.cliente.apellido}, {comp.cliente.nombre}")
                self.comprobante.visible = True
            else:
                lineas = [ft.Text(f"• {o.tipo_analisis.nombre}: {en_pesos(o.tipo_analisis.precio)}") for o in x.ordenes]
                self.resumen.controls = lineas or [tema.texto_tenue("La consulta no tiene órdenes de derivación: solo se cobra la consulta.")]
                self.honorarios.value = ""
                self.pendiente.visible = True
        self.ejecutar(accion)

    @manejador
    def cerrar(self) -> None:
        def accion() -> None:
            if self.selector.consulta_id is None:
                raise EntradaInvalida("Elegí la consulta que se va a cerrar.")
            svc.cerrar_consulta(self.selector.consulta_id, self.honorarios.value)
        if self.ejecutar(accion, "Consulta cerrada: comprobante emitido."):
            self.selector.recargar_consultas()
            self.mostrar()

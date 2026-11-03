"""Pantalla de reportes: se elige el reporte, se completan los filtros y se ve la tabla y el gráfico.

Es una sola pantalla para todos los reportes porque solo cambia la función que se llama: cada
reporte de `app.reportes.REPORTES` devuelve un ResultadoReporte con sus columnas, filas y gráfico.
"""

from __future__ import annotations

import flet as ft

from app.reportes import REPORTES, graficos
from app.reportes.filtros import FiltroReporte, rango_por_defecto
from app.servicios import catalogos, tiempo
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import a_fecha
from app.ui.pantalla import Pantalla, manejador

TODAS = "todas"


class PantallaReportes(Pantalla):
    clave = "reportes"
    titulo = "Reportes"
    icono = ft.Icons.INSIGHTS
    grupo = "Reportes"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self.reporte = c.desplegable("Reporte", ancho=360, al_elegir=self.elegir_reporte)
        c.poner_opciones(self.reporte, [(clave, modulo.TITULO) for clave, modulo in REPORTES.items()])
        self.reporte.value = next(iter(REPORTES))
        self.descripcion = tema.texto_tenue("", 13)
        desde, hasta = rango_por_defecto(tiempo.hoy())
        self.desde = c.campo("Desde", desde.isoformat(), ancho=160, sugerencia="AAAA-MM-DD")
        self.hasta = c.campo("Hasta", hasta.isoformat(), ancho=160, sugerencia="AAAA-MM-DD")
        self.clinica = c.desplegable("Clínica", ancho=260)

        # Resultado: la tabla se arma de nuevo en cada reporte porque cambian las columnas.
        self.titulo_resultado = ft.Text("", size=16, weight=ft.FontWeight.W_600)
        self.notas = ft.Column(spacing=2)
        self.tabla: c.Tabla | None = None
        self.lugar_tabla = ft.Container()
        self.lugar_grafico = ft.Container()
        self.lugar_detalle = ft.Container()  # una segunda tabla, cuando el reporte la trae
        self.detalle: c.Tabla | None = None
        self.resultado = tema.seccion(self.titulo_resultado, self.notas, self.lugar_tabla, self.lugar_grafico,
                                      self.lugar_detalle)
        self.resultado.visible = False
        self._mostrar_descripcion()

    def build(self) -> ft.Control:
        filtros = tema.seccion(
            "Filtros",
            tema.fila(self.reporte, self.clinica),
            self.descripcion,
            tema.fila(self.desde, self.hasta, c.boton("Generar", ft.Icons.PLAY_ARROW, self.generar)))
        return tema.pagina(
            tema.titulo_pantalla("Reportes", "Cálculos sobre la operación de la red: no se guardan, se calculan al pedirlos."),
            filtros, self.resultado)

    def al_mostrar(self) -> None:
        def accion() -> None:
            opciones = [(TODAS, "Todas")] + [(str(x.id), x.nombre) for x in catalogos.listar_clinicas()]
            c.poner_opciones(self.clinica, opciones, conservar=True)
            self.clinica.value = self.clinica.value or TODAS
        self.ejecutar(accion)

    def _mostrar_descripcion(self) -> None:
        self.descripcion.value = REPORTES[self.reporte.value].DESCRIPCION

    def _clinica_id(self) -> int | None:
        return None if self.clinica.value in (None, TODAS) else int(self.clinica.value)

    @manejador
    def elegir_reporte(self) -> None:
        self._mostrar_descripcion()
        self.resultado.visible = False

    @manejador
    def generar(self) -> None:
        def accion() -> None:
            filtro = FiltroReporte(a_fecha(self.desde.value, "Desde"), a_fecha(self.hasta.value, "Hasta"),
                                   self._clinica_id())
            resultado = REPORTES[self.reporte.value].generar(filtro)
            self.titulo_resultado.value = resultado.titulo
            self.notas.controls = [tema.texto_tenue(nota, 13) for nota in resultado.notas]
            self.tabla = c.Tabla(resultado.columnas, vacia="No hay datos para los filtros elegidos.", altura_maxima=420)
            self.tabla.cargar(enumerate(resultado.filas))
            self.lugar_tabla.content = self.tabla.vista
            self.lugar_grafico.content = (ft.Image(src=graficos.a_png(resultado.grafico), width=800)
                                          if resultado.grafico else None)
            if resultado.detalle_filas:
                self.detalle = c.Tabla(resultado.detalle_columnas, altura_maxima=320)
                self.detalle.cargar(enumerate(resultado.detalle_filas))
                self.lugar_detalle.content = ft.Column(
                    [ft.Text(resultado.detalle_titulo, size=15, weight=ft.FontWeight.W_600), self.detalle.vista], spacing=tema.ESPACIO)
            else:
                self.detalle = None
                self.lugar_detalle.content = None
            self.resultado.visible = True
        self.ejecutar(accion)

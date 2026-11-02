"""Pantalla de muestras (proceso 4, primera parte): extracción, re-extracción y trazabilidad."""

from __future__ import annotations

import flet as ft

from app.servicios import muestras as svc
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import etiquetas, tema
from app.ui.pantalla import Pantalla, manejador
from app.ui.selectores import SelectorOrden

EN_CURSO = "EN_CURSO"


class PantallaMuestras(Pantalla):
    clave = "muestras"
    titulo = "Muestras"
    icono = ft.Icons.SCIENCE_OUTLINED
    grupo = "Laboratorio"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._muestra_id: int | None = None

        # Extracción
        self.selector = SelectorOrden(self)
        self.ubicacion = c.campo("Ubicación", ancho=260, sugerencia="Dónde se extrae")
        self.observacion = c.campo("Observación", expandir=True)

        # Listado
        self.filtro = c.desplegable("Mostrar", ancho=240, al_elegir=self.cargar)
        c.poner_opciones(self.filtro, [(EN_CURSO, "En curso")] + list(etiquetas.ESTADOS_MUESTRA.items()))
        self.filtro.value = EN_CURSO
        self.tabla = c.Tabla(["N°", "Análisis", "Mascota", "Cliente", "Estado", "Motivo"], al_elegir=self.elegir,
                             texto_boton="Ver trazabilidad", icono=ft.Icons.TIMELINE, vacia="No hay muestras en este estado.")

        # Detalle y trazabilidad
        self.titulo_detalle = ft.Text("", size=15, weight=ft.FontWeight.W_600)
        self.proximo_paso = tema.texto_tenue("", 13)
        self.boton_reextraer = c.boton("Re-extracción sin cargo", ft.Icons.REPLAY, self.re_extraer, "secundario", visible=False)
        self.tiempo = ft.Column()
        self.detalle = tema.seccion(self.titulo_detalle, ft.Container())
        self.detalle.visible = False

    def build(self) -> ft.Control:
        extraccion = tema.seccion(
            "Registrar una extracción",
            tema.texto_tenue("Elegí la mascota, su consulta y la orden de derivación. Una orden tiene una sola muestra activa a la vez."),
            self.selector.vista,
            tema.fila(self.ubicacion, self.observacion),
            c.boton("Registrar extracción", ft.Icons.COLORIZE, self.registrar_extraccion))
        listado = tema.seccion("Muestras", self.filtro, self.tabla.vista)
        self.detalle.content = ft.Column([
            self.titulo_detalle, self.proximo_paso, self.boton_reextraer, ft.Divider(),
            ft.Text("Trazabilidad", weight=ft.FontWeight.W_600), self.tiempo], spacing=tema.ESPACIO)
        return tema.pagina(
            tema.titulo_pantalla("Muestras", "Cada muestra guarda su historial completo de estados; no se puede modificar."),
            extraccion, listado, self.detalle)

    @manejador
    def al_mostrar(self) -> None:
        self.cargar()

    @manejador
    def cargar(self) -> None:
        def accion() -> None:
            estado = None if self.filtro.value in (None, EN_CURSO) else self.filtro.value
            self.tabla.cargar((m.id, [
                str(m.id), m.analisis, m.mascota, m.cliente, etiquetas.estado_muestra(m.estado), etiquetas.motivos(m.motivos)])
                for m in svc.listar_resumenes_de_muestras(estado))
        self.ejecutar(accion)

    @manejador
    def registrar_extraccion(self) -> None:
        def accion() -> None:
            if self.selector.orden_id is None:
                raise EntradaInvalida("Elegí la orden de derivación de la que se extrae la muestra.")
            self._nueva = svc.registrar_extraccion(
                self.selector.orden_id, self.sesion.operador(), self.ubicacion.value, self.observacion.value)
        if self.ejecutar(accion, "Extracción registrada."):
            self.observacion.value = ""
            self.selector.recargar_ordenes()
            self.cargar()
            self.elegir(self._nueva.id)

    @manejador
    def elegir(self, muestra_id: int) -> None:
        def accion() -> None:
            m = svc.obtener_muestra(muestra_id)
            r = svc.resumen_de_muestra(muestra_id)
            self._muestra_id = m.id
            self.titulo_detalle.value = f"Muestra #{m.id} · {r.analisis} · {r.mascota} ({r.cliente}) · {etiquetas.estado_muestra(r.estado)}"
            permitidas = m.estado.operaciones_permitidas
            self.proximo_paso.value = ("Próximo paso: " + " / ".join(etiquetas.OPERACIONES_MUESTRA[o] for o in permitidas)
                                       if permitidas else "No admite más cambios: es un estado final.")
            self.boton_reextraer.visible = not m.esta_activa()
            self.tiempo.controls = [c.linea_de_tiempo(svc.trazabilidad_de_muestra(m.id))]
            self.detalle.visible = True
        self.ejecutar(accion)

    @manejador
    def re_extraer(self) -> None:
        def accion() -> None:
            self._nueva = svc.registrar_reextraccion(self._muestra_id, self.sesion.operador(), self.ubicacion.value)
        if self.ejecutar(accion, "Re-extracción registrada: es una muestra nueva de la misma orden, sin cargo."):
            self.selector.recargar_ordenes()
            self.cargar()
            self.elegir(self._nueva.id)

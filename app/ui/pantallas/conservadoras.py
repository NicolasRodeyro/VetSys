"""Pantalla de conservadoras (proceso 4): crearlas, empaquetar muestras y colocar el precinto."""

from __future__ import annotations

import flet as ft

from app.servicios import muestras as svc
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import etiquetas, tema
from app.ui.entradas import en_texto
from app.ui.pantalla import Pantalla, manejador


class PantallaConservadoras(Pantalla):
    clave = "conservadoras"
    titulo = "Conservadoras"
    icono = ft.Icons.INVENTORY_2_OUTLINED
    grupo = "Laboratorio"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._conservadora_id: int | None = None

        self.codigo = c.campo("Código", ancho=170, sugerencia="Por ejemplo C-001")
        self.capacidad = c.campo("Capacidad (muestras)", "5", ancho=190)
        self.temp_min = c.campo("Temperatura mínima (°C)", "2", ancho=210)
        self.temp_max = c.campo("Temperatura máxima (°C)", "8", ancho=210)
        self.tabla = c.Tabla(["Código", "Capacidad", "Rango", "Muestras", "Precinto", "Remito"], al_elegir=self.elegir,
                             texto_boton="Elegir", vacia="Todavía no hay conservadoras.")

        self.titulo_detalle = ft.Text("", size=15, weight=ft.FontWeight.W_600)
        self.tabla_muestras = c.Tabla(["N°", "Análisis", "Estado"], vacia="No lleva muestras todavía.")
        self.muestra = c.desplegable("Muestra extraída para empaquetar", expandir=True)
        self.numero_precinto = c.campo("N° de precinto", ancho=200)
        self.bloque_empaquetar = tema.fila(
            self.muestra, c.boton("Empaquetar", ft.Icons.MOVE_TO_INBOX_OUTLINED, self.empaquetar))
        self.bloque_precinto = tema.fila(
            self.numero_precinto, c.boton("Colocar precinto", ft.Icons.LOCK_OUTLINE, self.precintar, "secundario"))
        self.nota = tema.texto_tenue("")
        self.detalle = tema.seccion(self.titulo_detalle, ft.Container())
        self.detalle.visible = False

    def build(self) -> ft.Control:
        nueva = tema.seccion(
            "Nueva conservadora",
            tema.fila(self.codigo, self.capacidad, self.temp_min, self.temp_max),
            c.boton("Crear conservadora", ft.Icons.ADD, self.crear))
        self.detalle.content = ft.Column([
            self.titulo_detalle, self.nota, self.tabla_muestras.vista, self.bloque_empaquetar, self.bloque_precinto,
        ], spacing=tema.ESPACIO)
        return tema.pagina(
            tema.titulo_pantalla("Conservadoras isotérmicas",
                                 "Mantienen la temperatura de las muestras. Una vez precintada, no admite más muestras."),
            nueva, tema.seccion("Conservadoras", self.tabla.vista), self.detalle)

    @manejador
    def al_mostrar(self) -> None:
        self.cargar()

    @manejador
    def cargar(self) -> None:
        def accion() -> None:
            libres = {x.id for x in svc.listar_conservadoras(solo_sin_remito=True)}
            self.tabla.cargar((x.id, [
                x.codigo, str(x.capacidad), f"{x.temp_min:g} a {x.temp_max:g} °C", f"{len(x.muestras)} de {x.capacidad}",
                x.precinto.numero if x.precinto else "Sin precinto", "Libre" if x.id in libres else "En un remito"])
                for x in svc.listar_conservadoras())
        self.ejecutar(accion)

    @manejador
    def crear(self) -> None:
        def accion() -> None:
            self._nueva = svc.crear_conservadora(self.codigo.value, self.capacidad.value, self.temp_min.value, self.temp_max.value)
        if self.ejecutar(accion, "Conservadora creada."):
            self.codigo.value = ""
            self.cargar()
            self.elegir(self._nueva.id)

    @manejador
    def elegir(self, conservadora_id: int) -> None:
        def accion() -> None:
            x = svc.obtener_conservadora(conservadora_id)
            self._conservadora_id = x.id
            self.titulo_detalle.value = f"Conservadora {x.codigo} · {x.temp_min:g} a {x.temp_max:g} °C"
            self.tabla_muestras.cargar((m.id, [str(m.id), m.tipo_analisis.nombre, etiquetas.estado_muestra(m.estado.nombre)])
                                       for m in x.muestras)
            precintada = x.precinto is not None
            self.nota.value = (f"Precintada con el N° {x.precinto.numero} el {en_texto(x.precinto.fecha_colocacion)} "
                               f"por {x.precinto.responsable}." if precintada else "")
            self.nota.visible = precintada
            self.bloque_empaquetar.visible = self.bloque_precinto.visible = not precintada
            c.poner_opciones(self.muestra, ((str(m.id), m.etiqueta) for m in svc.listar_resumenes_de_muestras("EXTRAIDA")))
            self.detalle.visible = True
        self.ejecutar(accion)

    @manejador
    def empaquetar(self) -> None:
        def accion() -> None:
            muestra_id = c.clave_de(self.muestra)
            if muestra_id is None:
                raise EntradaInvalida("Elegí la muestra que se va a empaquetar.")
            svc.empaquetar_muestra(muestra_id, self._conservadora_id, self.sesion.operador())
        if self.ejecutar(accion, "Muestra empaquetada."):
            self.cargar()
            self.elegir(self._conservadora_id)

    @manejador
    def precintar(self) -> None:
        if self.ejecutar(lambda: svc.precintar_conservadora(self._conservadora_id, self.numero_precinto.value, self.sesion.operador()),
                         "Conservadora precintada."):
            self.numero_precinto.value = ""
            self.cargar()
            self.elegir(self._conservadora_id)

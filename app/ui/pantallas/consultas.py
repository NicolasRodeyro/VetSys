"""Pantalla de consultas (proceso 3): registrar la consulta (con el control de vacunas),
y emitir las órdenes de derivación a laboratorio."""

from __future__ import annotations

import flet as ft

from app.servicios import catalogos
from app.servicios import consultas as svc
from app.servicios import turnos as svc_turnos
from app.servicios.consultas import Prioridad, TipoConsulta
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import en_pesos, en_texto
from app.ui.pantalla import Pantalla, manejador
from app.ui.selectores import SelectorMascota

SIN_TURNO = "0"


class PantallaConsultas(Pantalla):
    clave = "consultas"
    titulo = "Consultas"
    icono = ft.Icons.MEDICAL_SERVICES_OUTLINED
    grupo = "Atención"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._consulta_id: int | None = None

        # Nueva consulta
        self.selector = SelectorMascota(self, self._recargar)
        self.veterinario = c.desplegable("Veterinario", expandir=True, al_elegir=self._cargar_turnos)
        self.tipo = c.desplegable("Tipo", ancho=190)
        c.poner_opciones(self.tipo, ((t.value, t.value.title()) for t in TipoConsulta))
        self.turno = c.desplegable("Turno (opcional)", ancho=260)
        self.diagnostico = c.campo("Diagnóstico", multilinea=True, expandir=True)
        self.tratamiento = c.campo("Tratamiento", multilinea=True, expandir=True)

        # Consultas de la mascota
        self.tabla = c.Tabla(["Fecha", "Tipo", "Veterinario", "Diagnóstico", "Órdenes", "Estado"], al_elegir=self.elegir,
                             texto_boton="Ver", icono=ft.Icons.CHEVRON_RIGHT, vacia="La mascota no tiene consultas.")

        # Detalle de la consulta elegida
        self.titulo_detalle = ft.Text("", size=15, weight=ft.FontWeight.W_600)
        self.advertencias = ft.Column(spacing=4)
        self.diagnostico_detalle = c.campo("Diagnóstico", multilinea=True, expandir=True)
        self.tratamiento_detalle = c.campo("Tratamiento", multilinea=True, expandir=True)
        self.boton_guardar = c.boton("Guardar cambios", ft.Icons.SAVE_OUTLINED, self.guardar_cambios, "secundario")
        self.tabla_ordenes = c.Tabla(["Análisis", "Prioridad", "Muestras", "Precio"], vacia="Todavía no se emitió ninguna orden.")
        self.analisis = c.desplegable("Análisis", expandir=True)
        self.prioridad = c.desplegable("Prioridad", ancho=170)
        c.poner_opciones(self.prioridad, ((p.value, p.value.title()) for p in Prioridad))
        self.prioridad.value = Prioridad.NORMAL.value
        self.formulario_orden = tema.fila(
            self.analisis, self.prioridad, c.boton("Emitir orden", ft.Icons.SCIENCE_OUTLINED, self.emitir_orden))
        self.detalle = tema.seccion(self.titulo_detalle, ft.Container())
        self.detalle.visible = False

    def build(self) -> ft.Control:
        nueva = tema.seccion(
            "Registrar una consulta",
            self.selector.vista,
            tema.fila(self.veterinario, self.tipo, self.turno),
            tema.fila(self.diagnostico, self.tratamiento),
            c.boton("Registrar consulta", ft.Icons.ADD_TASK, self.registrar))
        historial = tema.seccion("Consultas de la mascota", self.tabla.vista)
        self.detalle.content = ft.Column([
            self.titulo_detalle, self.advertencias,
            tema.fila(self.diagnostico_detalle, self.tratamiento_detalle), self.boton_guardar,
            ft.Divider(), ft.Text("Órdenes de derivación a laboratorio", weight=ft.FontWeight.W_600),
            self.tabla_ordenes.vista, self.formulario_orden,
        ], spacing=tema.ESPACIO)
        return tema.pagina(
            tema.titulo_pantalla("Consultas", "Si la mascota tiene vacunas pendientes se avisa, pero la consulta se registra igual."),
            nueva, historial, self.detalle)

    @manejador
    def al_mostrar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.veterinario, (
                (str(v.id), f"{v.apellido}, {v.nombre} · {v.clinica.nombre}") for v in catalogos.listar_veterinarios()),
                conservar=True)
            c.poner_opciones(self.analisis, (
                (t.nombre, f"{t.nombre} · {en_pesos(t.precio)} ({t.tipo_muestra}, {t.temp_min:g} a {t.temp_max:g} °C)")
                for t in catalogos.listar_tipos_analisis()), conservar=True)
        self.ejecutar(accion)

    # ----------------------------------------------------------- nueva consulta

    @manejador
    def _cargar_turnos(self) -> None:
        """Los turnos programados de la mascota con el veterinario elegido (para atender uno)."""
        def accion() -> None:
            veterinario_id, mascota_id = c.clave_de(self.veterinario), self.selector.mascota_id
            turnos = svc_turnos.listar_turnos(veterinario_id) if veterinario_id and mascota_id else []
            opciones = [(SIN_TURNO, "Sin turno")] + [
                (str(t.id), en_texto(t.inicio)) for t in turnos if t.mascota.id == mascota_id]
            c.poner_opciones(self.turno, opciones)
        self.ejecutar(accion)

    @manejador
    def _recargar(self) -> None:
        self._cargar_turnos()
        self._cargar_consultas()

    def _cargar_consultas(self) -> None:
        def accion() -> None:
            consultas = svc.listar_consultas_de_mascota(self.selector.mascota_id) if self.selector.mascota_id else []
            self.tabla.cargar((x.id, [
                en_texto(x.fecha_hora), x.tipo.value.title(), f"{x.veterinario.apellido}",
                x.diagnostico[:40] + ("…" if len(x.diagnostico) > 40 else ""), str(len(x.ordenes)),
                "Cerrada" if x.cerrada else "Abierta"]) for x in consultas)
            self.detalle.visible = False
            self._consulta_id = None
        self.ejecutar(accion)

    @manejador
    def registrar(self) -> None:
        def accion() -> None:
            if self.selector.mascota_id is None:
                raise EntradaInvalida("Elegí la mascota (buscá primero a su cliente).")
            if c.clave_de(self.veterinario) is None:
                raise EntradaInvalida("Elegí el veterinario que atiende.")
            turno_id = c.clave_de(self.turno) or None  # "Sin turno" tiene clave 0
            consulta = svc.registrar_consulta(
                self.selector.mascota_id, c.clave_de(self.veterinario), self.tipo.value or "", None, turno_id,
                self.diagnostico.value, self.tratamiento.value)
            self._registrada = consulta
        if not self.ejecutar(accion):
            return
        consulta = self._registrada
        self.diagnostico.value = self.tratamiento.value = ""
        self._recargar()
        self.elegir(consulta.id)
        if consulta.advertencias:  # el control de vacunas advierte, no bloquea: la consulta ya está registrada
            self.avisar("Consulta registrada, con vacunas pendientes", consulta.advertencias)
        else:
            self.sesion.mensajero.exito("Consulta registrada.")

    # ----------------------------------------------------------- detalle

    @manejador
    def elegir(self, consulta_id: int) -> None:
        def accion() -> None:
            x = svc.obtener_consulta(consulta_id)
            self._consulta_id = x.id
            self.titulo_detalle.value = f"Consulta del {en_texto(x.fecha_hora)} · {x.tipo.value.title()}" + (
                f" · CERRADA ({en_pesos(x.comprobante.total)})" if x.cerrada else "")
            self.advertencias.controls = [
                ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_800, size=18), ft.Text(a)])
                for a in x.advertencias]
            self.diagnostico_detalle.value, self.tratamiento_detalle.value = x.diagnostico, x.tratamiento
            self.diagnostico_detalle.disabled = self.tratamiento_detalle.disabled = x.cerrada
            self.boton_guardar.visible = self.formulario_orden.visible = not x.cerrada
            self.tabla_ordenes.cargar((o.id, [
                o.tipo_analisis.nombre, o.prioridad.value.title(), str(len(o.muestras)), en_pesos(o.tipo_analisis.precio)])
                for o in x.ordenes)
            self.detalle.visible = True
        self.ejecutar(accion)

    @manejador
    def guardar_cambios(self) -> None:
        self.ejecutar(lambda: svc.actualizar_consulta(
            self._consulta_id, self.diagnostico_detalle.value, self.tratamiento_detalle.value), "Consulta actualizada.")
        self._cargar_consultas_manteniendo()

    def _cargar_consultas_manteniendo(self) -> None:
        elegida = self._consulta_id
        self._cargar_consultas()
        if elegida:
            self.elegir(elegida)

    @manejador
    def emitir_orden(self) -> None:
        def accion() -> None:
            if not self.analisis.value:
                raise EntradaInvalida("Elegí el análisis que se pide al laboratorio.")
            svc.emitir_orden(self._consulta_id, self.analisis.value, self.prioridad.value or "")
        if self.ejecutar(accion, "Orden de derivación emitida."):
            self._cargar_consultas_manteniendo()

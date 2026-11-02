"""Selectores encadenados que usan varias pantallas: buscar un cliente, elegir su mascota,
una consulta suya y una orden de derivación."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.servicios import clientes as svc_clientes
from app.servicios import consultas as svc_consultas
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import en_texto
from app.ui.pantalla import Pantalla, manejador


class SelectorMascota:
    """Se busca un cliente (por DNI, apellido o nombre) y se elige una de sus mascotas activas."""

    def __init__(self, pantalla: Pantalla, al_elegir: Callable[[], None] | None = None) -> None:
        self._pantalla = pantalla
        self._al_elegir = al_elegir
        self.busqueda = c.campo("Buscar cliente (DNI, apellido o nombre)", expandir=True, al_enviar=self.buscar)
        self.lista = c.desplegable("Mascota", expandir=True, al_elegir=self._elegida)
        self.vista = ft.Column([
            tema.fila(self.busqueda, c.boton("Buscar", ft.Icons.SEARCH, self.buscar, "secundario")),
            self.lista,
        ], spacing=tema.ESPACIO)

    @property
    def mascota_id(self) -> int | None:
        return c.clave_de(self.lista)

    @manejador
    def buscar(self) -> None:
        def accion() -> None:
            opciones = []
            for cliente in svc_clientes.buscar_clientes(self.busqueda.value or ""):
                for m in cliente.mascotas:
                    if m.activa:
                        opciones.append((str(m.id), f"{m.nombre} ({m.especie.nombre}) · {cliente.apellido}, {cliente.nombre}"))
            c.poner_opciones(self.lista, opciones)
            if not opciones:
                self._pantalla.sesion.mensajero.error("No se encontró ninguna mascota con ese cliente.")
            self._elegida()
        self._pantalla.ejecutar(accion)

    @manejador
    def _elegida(self) -> None:
        if self._al_elegir:
            self._al_elegir()

    def limpiar(self) -> None:
        self.busqueda.value = ""
        c.poner_opciones(self.lista, [])


class SelectorConsulta(SelectorMascota):
    """Además de la mascota, elige una de sus consultas."""

    def __init__(self, pantalla: Pantalla, al_elegir: Callable[[], None] | None = None) -> None:
        self._al_elegir_consulta = al_elegir
        super().__init__(pantalla, self._mascota_elegida)
        self.lista_consultas = c.desplegable("Consulta", expandir=True, al_elegir=self._consulta_elegida)
        self.vista.controls.append(self.lista_consultas)

    @property
    def consulta_id(self) -> int | None:
        return c.clave_de(self.lista_consultas)

    @manejador
    def _mascota_elegida(self) -> None:
        def accion() -> None:
            consultas = svc_consultas.listar_consultas_de_mascota(self.mascota_id) if self.mascota_id else []
            c.poner_opciones(self.lista_consultas, (
                (str(x.id), f"{en_texto(x.fecha_hora)} · {x.tipo.value.title()}{' · cerrada' if x.cerrada else ''}")
                for x in consultas))
            self._consulta_elegida()
        self._pantalla.ejecutar(accion)

    @manejador
    def _consulta_elegida(self) -> None:
        if self._al_elegir_consulta:
            self._al_elegir_consulta()

    def recargar_consultas(self) -> None:
        """Vuelve a leer las consultas de la mascota (por ejemplo, después de cerrar una)."""
        elegida = self.lista_consultas.value
        self._mascota_elegida()
        if elegida:
            self.lista_consultas.value = elegida
            self._consulta_elegida()

    def limpiar(self) -> None:
        super().limpiar()
        c.poner_opciones(self.lista_consultas, [])


class SelectorOrden(SelectorConsulta):
    """Además de la consulta, elige una de sus órdenes de derivación."""

    def __init__(self, pantalla: Pantalla, al_elegir: Callable[[], None] | None = None) -> None:
        self._al_elegir_orden = al_elegir
        super().__init__(pantalla, self._cargar_ordenes)
        self.lista_ordenes = c.desplegable("Orden de derivación", expandir=True, al_elegir=self._orden_elegida)
        self.vista.controls.append(self.lista_ordenes)

    @property
    def orden_id(self) -> int | None:
        return c.clave_de(self.lista_ordenes)

    @manejador
    def _cargar_ordenes(self) -> None:
        def accion() -> None:
            ordenes = svc_consultas.obtener_consulta(self.consulta_id).ordenes if self.consulta_id else ()
            c.poner_opciones(self.lista_ordenes, (
                (str(o.id), f"{o.tipo_analisis.nombre} ({o.prioridad.value.title()}) · {len(o.muestras)} muestra(s)")
                for o in ordenes))
            self._orden_elegida()
        self._pantalla.ejecutar(accion)

    @manejador
    def _orden_elegida(self) -> None:
        if self._al_elegir_orden:
            self._al_elegir_orden()

    def recargar_ordenes(self) -> None:
        elegida = self.lista_ordenes.value
        self._cargar_ordenes()
        if elegida:
            self.lista_ordenes.value = elegida
            self._orden_elegida()

    def limpiar(self) -> None:
        super().limpiar()
        c.poner_opciones(self.lista_ordenes, [])


"""Pantalla de clientes (proceso 1): alta, búsqueda, modificación y baja lógica."""

from __future__ import annotations

import flet as ft

from app.servicios import clientes as svc
from app.ui import componentes as c
from app.ui import tema
from app.ui.pantalla import Pantalla, manejador


class PantallaClientes(Pantalla):
    clave = "clientes"
    titulo = "Clientes"
    icono = ft.Icons.PEOPLE_OUTLINE
    grupo = "Atención"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._cliente_id: int | None = None

        # Búsqueda
        # La tabla se actualiza mientras se escribe y al tildar «incluir bajas»: no hace falta apretar «Buscar».
        self.busqueda = c.campo("DNI, apellido o nombre", expandir=True, al_enviar=self.buscar)
        self.busqueda.on_change = self.buscar
        self.incluir_bajas = ft.Checkbox(label="Incluir clientes de baja", value=False, on_change=self.buscar)
        self.tabla = c.Tabla(
            ["DNI", "Apellido", "Nombre", "Teléfono", "Email", "Estado"], al_elegir=self.elegir,
            texto_boton="Editar", vacia="No hay clientes que coincidan con la búsqueda.")

        # Formulario
        self.titulo_formulario = ft.Text("Nuevo cliente", size=15, weight=ft.FontWeight.W_600)
        self.dni = c.campo("DNI", ancho=180)
        self.nombre = c.campo("Nombre", expandir=True)
        self.apellido = c.campo("Apellido", expandir=True)
        self.telefono = c.campo("Teléfono", ancho=220)
        self.email = c.campo("Email", expandir=True)
        self.direccion = c.campo("Dirección", expandir=True)
        self.estado = tema.texto_tenue("")
        self.estado.visible = False
        self.boton_baja = c.boton("Dar de baja", ft.Icons.PERSON_OFF_OUTLINED, self.dar_de_baja, "peligro", visible=False)
        self.boton_reactivar = c.boton("Reactivar", ft.Icons.PERSON_ADD_ALT_1, self.reactivar, "secundario", visible=False)

    def build(self) -> ft.Control:
        busqueda = tema.seccion(
            "Buscar clientes",
            tema.fila(self.busqueda, self.incluir_bajas, c.boton("Buscar", ft.Icons.SEARCH, self.buscar, "secundario")),
            self.tabla.vista)
        formulario = tema.seccion(
            self.titulo_formulario,
            tema.fila(self.dni, self.nombre, self.apellido),
            tema.fila(self.telefono, self.email, self.direccion),
            self.estado,
            tema.fila(
                c.boton("Guardar", ft.Icons.SAVE_OUTLINED, self.guardar),
                c.boton("Nuevo cliente", ft.Icons.ADD, self.nuevo, "secundario"),
                self.boton_baja, self.boton_reactivar))
        return tema.pagina(
            tema.titulo_pantalla("Clientes", "Alta, búsqueda, modificación y baja lógica. Las mascotas se administran en su pantalla."),
            busqueda, formulario)

    def al_mostrar(self) -> None:
        self.buscar()

    # ----------------------------------------------------------- acciones

    @manejador
    def buscar(self) -> None:
        def accion() -> None:
            lista = svc.buscar_clientes(self.busqueda.value or "", bool(self.incluir_bajas.value))
            self.tabla.cargar(
                (x.id, [x.dni, x.apellido, x.nombre, x.telefono, x.email, "Activo" if x.activo else "De baja"])
                for x in lista)
        self.ejecutar(accion)

    @manejador
    def elegir(self, cliente_id: int) -> None:
        def accion() -> None:
            cliente = svc.obtener_cliente(cliente_id)
            self._cliente_id = cliente.id
            self.dni.value, self.nombre.value, self.apellido.value = cliente.dni, cliente.nombre, cliente.apellido
            self.telefono.value, self.email.value, self.direccion.value = cliente.telefono, cliente.email, cliente.direccion
            self.titulo_formulario.value = f"Editando a {cliente.apellido}, {cliente.nombre}"
            self.estado.value = (f"{len(cliente.mascotas)} mascota(s) · " + ("cliente activo" if cliente.activo else "cliente DADO DE BAJA"))
            self.estado.visible = True
            self.boton_baja.visible = cliente.activo
            self.boton_reactivar.visible = not cliente.activo
        self.ejecutar(accion)

    @manejador
    def nuevo(self) -> None:
        self._cliente_id = None
        for control in (self.dni, self.nombre, self.apellido, self.telefono, self.email, self.direccion):
            control.value = ""
        self.titulo_formulario.value = "Nuevo cliente"
        self.estado.value, self.estado.visible = "", False
        self.boton_baja.visible = self.boton_reactivar.visible = False

    @manejador
    def guardar(self) -> None:
        def accion() -> None:
            if self._cliente_id is None:
                cliente = svc.alta_cliente(self.dni.value, self.nombre.value, self.apellido.value,
                                           self.telefono.value, self.email.value, self.direccion.value)
            else:
                cliente = svc.modificar_cliente(
                    self._cliente_id, dni=self.dni.value, nombre=self.nombre.value, apellido=self.apellido.value,
                    telefono=self.telefono.value, email=self.email.value, direccion=self.direccion.value)
            self._guardado = cliente.id
        if self.ejecutar(accion, "Cliente guardado."):
            self.buscar()
            self.elegir(self._guardado)

    @manejador
    def dar_de_baja(self) -> None:
        if self._cliente_id is not None and self.ejecutar(lambda: svc.dar_de_baja_cliente(self._cliente_id), "Cliente dado de baja."):
            self.buscar()
            self.elegir(self._cliente_id)

    @manejador
    def reactivar(self) -> None:
        if self._cliente_id is not None and self.ejecutar(lambda: svc.reactivar_cliente(self._cliente_id), "Cliente reactivado."):
            self.buscar()
            self.elegir(self._cliente_id)

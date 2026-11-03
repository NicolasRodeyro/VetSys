"""Pantalla de mascotas e historias clínicas (proceso 2): alta, modificación, baja lógica,
alergias y antecedentes, vacunas aplicadas y vacunas pendientes."""

from __future__ import annotations

import flet as ft

from app.servicios import catalogos
from app.servicios import clientes as svc
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import tema
from app.ui.buscador_clientes import BuscadorClientes
from app.ui.entradas import a_fecha, en_texto, hoy_texto
from app.ui.pantalla import Pantalla, manejador

SEXOS = [("MACHO", "Macho"), ("HEMBRA", "Hembra")]


class PantallaMascotas(Pantalla):
    clave = "mascotas"
    titulo = "Mascotas"
    icono = ft.Icons.PETS_OUTLINED
    grupo = "Atención"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._cliente_id: int | None = None
        self._mascota_id: int | None = None

        # 1. Cliente y sus mascotas
        self.buscador = BuscadorClientes(self, self.elegir_cliente, self._cliente_descartado)
        self.tabla = c.Tabla(["Nombre", "Especie", "Sexo", "Nacimiento", "Estado"], al_elegir=self.elegir_mascota,
                             texto_boton="Elegir", vacia="Este cliente todavía no tiene mascotas.")

        # 2. Datos de la mascota
        self.titulo_formulario = ft.Text("Nueva mascota", size=15, weight=ft.FontWeight.W_600)
        self.nombre = c.campo("Nombre", expandir=True)
        self.especie = c.desplegable("Especie", ancho=200)
        self.sexo = c.desplegable("Sexo", ancho=150)
        c.poner_opciones(self.sexo, SEXOS)
        self.nacimiento = c.campo("Nacimiento", ancho=180, sugerencia="AAAA-MM-DD")
        self.estado = tema.texto_tenue("")
        self.estado.visible = False
        self.boton_baja = c.boton("Dar de baja", ft.Icons.BLOCK, self.dar_de_baja, "peligro", visible=False)
        self.boton_reactivar = c.boton("Reactivar", ft.Icons.RESTORE, self.reactivar, "secundario", visible=False)

        # 3. Historia clínica
        self.alergias = c.campo("Alergias", multilinea=True, expandir=True)
        self.antecedentes = c.campo("Antecedentes", multilinea=True, expandir=True)
        self.tabla_vacunas = c.Tabla(["Vacuna", "Fecha de aplicación"], vacia="Todavía no se aplicó ninguna vacuna.")
        self.pendientes = ft.Column(spacing=4)
        self.vacuna = c.desplegable("Vacuna del esquema", ancho=260)
        self.fecha_vacuna = c.campo("Fecha de aplicación", ancho=200, sugerencia="AAAA-MM-DD")
        self.historia = tema.seccion("Historia clínica", ft.Container())
        self.historia.visible = False

    # ----------------------------------------------------------- armado

    def build(self) -> ft.Control:
        cliente = tema.seccion(
            "Cliente y mascotas",
            self.buscador.vista, self.tabla.vista)
        formulario = tema.seccion(
            self.titulo_formulario,
            tema.fila(self.nombre, self.especie, self.sexo, self.nacimiento),
            self.estado,
            tema.fila(
                c.boton("Guardar", ft.Icons.SAVE_OUTLINED, self.guardar),
                c.boton("Nueva mascota", ft.Icons.ADD, self.nueva, "secundario"),
                self.boton_baja, self.boton_reactivar))
        self.historia.content = ft.Column([
            ft.Text("Historia clínica", size=15, weight=ft.FontWeight.W_600),
            tema.fila(self.alergias, self.antecedentes),
            c.boton("Guardar historia", ft.Icons.SAVE_OUTLINED, self.guardar_historia, "secundario"),
            ft.Divider(),
            ft.Text("Vacunas pendientes", weight=ft.FontWeight.W_600), self.pendientes,
            ft.Text("Vacunas aplicadas", weight=ft.FontWeight.W_600), self.tabla_vacunas.vista,
            tema.fila(self.vacuna, self.fecha_vacuna, c.boton("Aplicar vacuna", ft.Icons.VACCINES_OUTLINED, self.aplicar_vacuna)),
        ], spacing=tema.ESPACIO)
        return tema.pagina(
            tema.titulo_pantalla("Mascotas e historias clínicas",
                                 "Elegí un cliente para ver sus mascotas. Cada mascota tiene siempre un responsable."),
            cliente, formulario, self.historia)

    @property
    def busqueda(self):
        return self.buscador.campo

    @manejador
    def al_mostrar(self) -> None:
        self.ejecutar(lambda: c.poner_opciones(self.especie, ((e.nombre, e.nombre) for e in catalogos.listar_especies()), conservar=True))

    # ----------------------------------------------------------- cliente

    @manejador
    def elegir_cliente(self, cliente) -> None:
        """Se tocó un cliente en la lista de coincidencias: quedan a la vista sus mascotas."""
        self._cliente_id = cliente.id
        self.nueva()
        self._recargar_mascotas()

    @manejador
    def _cliente_descartado(self) -> None:
        """El usuario siguió escribiendo: el cliente elegido ya no corresponde."""
        if self._cliente_id is not None:
            self._cliente_id = None
            self.nueva()
            self._recargar_mascotas()

    def _recargar_mascotas(self) -> None:
        def accion() -> None:
            mascotas = svc.obtener_cliente(self._cliente_id).mascotas if self._cliente_id else ()
            self.tabla.cargar((m.id, [m.nombre, m.especie.nombre, m.sexo.value.title(), en_texto(m.fecha_nacimiento),
                                      "Activa" if m.activa else "De baja"]) for m in mascotas)
        self.ejecutar(accion)

    # ----------------------------------------------------------- mascota

    @manejador
    def nueva(self) -> None:
        self._mascota_id = None
        self.nombre.value, self.nacimiento.value = "", ""
        self.especie.value = self.sexo.value = None
        self.especie.disabled = self.nacimiento.disabled = False
        self.titulo_formulario.value = "Nueva mascota"
        self.estado.value, self.estado.visible = "", False
        self.boton_baja.visible = self.boton_reactivar.visible = False
        self.historia.visible = False

    @manejador
    def elegir_mascota(self, mascota_id: int) -> None:
        def accion() -> None:
            m = svc.obtener_mascota(mascota_id)
            self._mascota_id = m.id
            self.nombre.value, self.sexo.value = m.nombre, m.sexo.value
            self.especie.value, self.nacimiento.value = m.especie.nombre, m.fecha_nacimiento.isoformat()
            # La especie y la fecha de nacimiento no se corrigen: solo el nombre y el sexo.
            self.especie.disabled = self.nacimiento.disabled = True
            self.titulo_formulario.value = f"Editando a {m.nombre}"
            self.estado.value, self.estado.visible = ("Mascota activa" if m.activa else "Mascota DADA DE BAJA"), True
            self.boton_baja.visible, self.boton_reactivar.visible = m.activa, not m.activa
            self.historia.visible = True
            self.alergias.value, self.antecedentes.value = m.historia_clinica.alergias, m.historia_clinica.antecedentes
            c.poner_opciones(self.vacuna, ((v.nombre, v.nombre) for v in m.especie.esquema_vacunas))
            self.fecha_vacuna.value = hoy_texto()
            self._recargar_vacunas()
        self.ejecutar(accion)

    def _recargar_vacunas(self) -> None:
        m = svc.obtener_mascota(self._mascota_id)
        self.tabla_vacunas.cargar(
            (i, [a.vacuna.nombre, en_texto(a.fecha)]) for i, a in enumerate(m.historia_clinica.vacunas_aplicadas))
        pendientes = svc.vacunas_pendientes(self._mascota_id)
        self.pendientes.controls = [
            ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_800, size=18),
                    ft.Text(f"{v.nombre} (corresponde desde los {v.edad_aplicacion_meses} meses"
                            + (f", refuerzo cada {v.refuerzo_cada_meses})" if v.refuerzo_cada_meses else ")"))])
            for v in pendientes
        ] or [ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_700, size=18), ft.Text("Al día")])]

    @manejador
    def guardar(self) -> None:
        def accion() -> None:
            if self._mascota_id is None:
                if self._cliente_id is None:
                    raise EntradaInvalida("Primero elegí el cliente al que pertenece la mascota.")
                m = svc.alta_mascota(self._cliente_id, self.nombre.value, self.especie.value or "",
                                     self.sexo.value or "", a_fecha(self.nacimiento.value, "La fecha de nacimiento"))
            else:
                m = svc.modificar_mascota(self._mascota_id, nombre=self.nombre.value, sexo=self.sexo.value)
            self._guardada = m.id
        if self.ejecutar(accion, "Mascota guardada."):
            self._recargar_mascotas()
            self.elegir_mascota(self._guardada)

    @manejador
    def dar_de_baja(self) -> None:
        if self._mascota_id and self.ejecutar(lambda: svc.dar_de_baja_mascota(self._mascota_id), "Mascota dada de baja."):
            self._recargar_mascotas()
            self.elegir_mascota(self._mascota_id)

    @manejador
    def reactivar(self) -> None:
        if self._mascota_id and self.ejecutar(lambda: svc.reactivar_mascota(self._mascota_id), "Mascota reactivada."):
            self._recargar_mascotas()
            self.elegir_mascota(self._mascota_id)

    # ----------------------------------------------------------- historia clínica

    @manejador
    def guardar_historia(self) -> None:
        self.ejecutar(lambda: svc.actualizar_historia_clinica(
            self._mascota_id, alergias=self.alergias.value, antecedentes=self.antecedentes.value), "Historia clínica guardada.")

    @manejador
    def aplicar_vacuna(self) -> None:
        def accion() -> None:
            fecha = a_fecha(self.fecha_vacuna.value, "La fecha de aplicación") if (self.fecha_vacuna.value or "").strip() else None
            svc.aplicar_vacuna(self._mascota_id, self.vacuna.value or "", fecha)
        if self.ejecutar(accion, "Vacuna registrada."):
            self.ejecutar(self._recargar_vacunas)


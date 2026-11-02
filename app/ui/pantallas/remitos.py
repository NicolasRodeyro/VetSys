"""Pantalla de remitos (procesos 4 y 5): armar el remito, cerrarlo, despacharlo y registrar la
cadena de envío. Solo se ofrecen las operaciones que el estado actual del remito permite."""

from __future__ import annotations

from functools import partial

import flet as ft

from app.servicios import catalogos, muestras
from app.servicios import remitos as svc
from app.servicios.excepciones import EntradaInvalida
from app.ui import componentes as c
from app.ui import etiquetas, tema
from app.ui.entradas import a_fecha_hora, en_texto
from app.ui.pantalla import Pantalla, manejador

AYUDA = {
    "agregar_conservadora": "agregar conservadoras",
    "quitar_conservadora": "quitar conservadoras",
    "cerrar": "cerrarlo",
    "despachar": "despacharlo",
    "registrar_tramo": "registrar los tramos del envío",
    "registrar_recepcion": "registrar la recepción (en la pantalla Recepción)",
}


class PantallaRemitos(Pantalla):
    clave = "remitos"
    titulo = "Remitos"
    icono = ft.Icons.LOCAL_SHIPPING_OUTLINED
    grupo = "Laboratorio"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._remito_id: int | None = None

        self.clinica = c.desplegable("Clínica de origen", expandir=True)
        self.laboratorio = c.desplegable("Laboratorio de destino", expandir=True)
        self.tabla = c.Tabla(["Número", "Clínica", "Laboratorio", "Estado", "Conservadoras", "Tramos"], al_elegir=self.elegir,
                             texto_boton="Elegir", vacia="Todavía no hay remitos.")

        # Detalle
        self.titulo_detalle = ft.Text("", size=15, weight=ft.FontWeight.W_600)
        self.permitido = tema.texto_tenue("", 13)
        self.conservadoras = ft.Column()
        self.tabla_tramos = c.Tabla(["N°", "Origen", "Destino", "Transportista", "Salida", "Llegada", "Temperatura"],
                                    vacia="Todavía no se registraron tramos.")
        self.recepcion = ft.Column(spacing=4)

        # Un bloque por operación; solo se muestran los que el estado permite
        self.libres = c.desplegable("Conservadora disponible", expandir=True)
        self.bloque_agregar = tema.fila(self.libres, c.boton("Agregar al remito", ft.Icons.ADD, self.agregar))
        self.bloque_cerrar = tema.fila(c.boton("Cerrar remito", ft.Icons.LOCK_OUTLINE, self.cerrar))
        self.ubicacion = c.campo("Ubicación de salida", expandir=True)
        self.bloque_despachar = tema.fila(self.ubicacion, c.boton("Despachar", ft.Icons.SEND_OUTLINED, self.despachar))
        self.origen = c.campo("Origen", expandir=True)
        self.destino = c.campo("Destino", expandir=True)
        self.transportista = c.campo("Transportista", expandir=True)
        self.salida = c.campo("Salida", ancho=200, sugerencia="AAAA-MM-DD HH:MM")
        self.llegada = c.campo("Llegada (opcional)", ancho=200, sugerencia="AAAA-MM-DD HH:MM")
        self.temperatura = c.campo("Temp. °C (opcional)", ancho=200)
        self.bloque_tramo = ft.Column([
            ft.Text("Registrar un tramo", weight=ft.FontWeight.W_600),
            tema.fila(self.origen, self.destino, self.transportista),
            tema.fila(self.salida, self.llegada, self.temperatura, c.boton("Registrar tramo", ft.Icons.ADD_ROAD, self.registrar_tramo))],
            spacing=tema.ESPACIO)
        self.detalle = tema.seccion(self.titulo_detalle, ft.Container())
        self.detalle.visible = False

    def build(self) -> ft.Control:
        nuevo = tema.seccion(
            "Nuevo remito",
            tema.texto_tenue("El número se asigna solo (R-00001, R-00002...)."),
            tema.fila(self.clinica, self.laboratorio, c.boton("Crear remito", ft.Icons.ADD, self.crear)))
        self.detalle.content = ft.Column([
            self.titulo_detalle, self.permitido,
            ft.Text("Conservadoras", weight=ft.FontWeight.W_600), self.conservadoras,
            self.bloque_agregar, self.bloque_cerrar, self.bloque_despachar,
            ft.Divider(), ft.Text("Cadena de envío", weight=ft.FontWeight.W_600), self.tabla_tramos.vista, self.bloque_tramo,
            self.recepcion], spacing=tema.ESPACIO)
        return tema.pagina(
            tema.titulo_pantalla("Remitos biológicos", "Acompañan a las conservadoras de la clínica al laboratorio."),
            nuevo, tema.seccion("Remitos", self.tabla.vista), self.detalle)

    @manejador
    def al_mostrar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.clinica, ((str(x.id), x.nombre) for x in catalogos.listar_clinicas()), conservar=True)
            c.poner_opciones(self.laboratorio, ((str(x.id), x.nombre) for x in catalogos.listar_laboratorios()), conservar=True)
        self.ejecutar(accion)
        self.cargar()

    @manejador
    def cargar(self) -> None:
        def accion() -> None:
            self.tabla.cargar((r.id, [
                r.numero, r.origen.nombre, r.destino.nombre, etiquetas.estado_remito(r.estado.nombre),
                str(len(r.conservadoras)), str(len(r.tramos))]) for r in svc.listar_remitos())
        self.ejecutar(accion)

    @manejador
    def crear(self) -> None:
        def accion() -> None:
            if c.clave_de(self.clinica) is None or c.clave_de(self.laboratorio) is None:
                raise EntradaInvalida("Elegí la clínica de origen y el laboratorio de destino.")
            self._nuevo = svc.crear_remito(c.clave_de(self.clinica), c.clave_de(self.laboratorio))
        if self.ejecutar(accion, "Remito creado."):
            self.cargar()
            self.elegir(self._nuevo.id)

    # ----------------------------------------------------------- detalle

    @manejador
    def elegir(self, remito_id: int) -> None:
        def accion() -> None:
            r = svc.obtener_remito(remito_id)
            self._remito_id = r.id
            permitidas = r.estado.operaciones_permitidas  # lo dice el estado: la interfaz no repite las reglas
            self.titulo_detalle.value = f"Remito {r.numero} · {etiquetas.estado_remito(r.estado.nombre)}"
            self.permitido.value = (("Ahora se puede: " + ", ".join(AYUDA[o] for o in permitidas) + ".") if permitidas
                                    else "El remito ya está recibido: no admite más cambios.")

            # Las conservadoras, con «Quitar» solo si el estado lo permite
            quitar = "quitar_conservadora" in permitidas
            self.conservadoras.controls = [
                ft.Row([ft.Text(f"{x.codigo} · precinto {x.precinto.numero if x.precinto else '—'} · {len(x.muestras)} muestra(s)", expand=True)]
                       + ([ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, tooltip="Quitar del remito",
                                         on_click=partial(self.quitar, x.id))] if quitar else []))
                for x in r.conservadoras] or [tema.texto_tenue("El remito todavía no tiene conservadoras.")]
            if "agregar_conservadora" in permitidas:
                c.poner_opciones(self.libres, ((str(x.id), f"{x.codigo} ({len(x.muestras)} muestras, "
                                                f"{'precintada' if x.precinto else 'sin precinto'})")
                                               for x in muestras.listar_conservadoras(solo_sin_remito=True)))

            self.bloque_agregar.visible = "agregar_conservadora" in permitidas
            self.bloque_cerrar.visible = "cerrar" in permitidas
            self.bloque_despachar.visible = "despachar" in permitidas
            self.bloque_tramo.visible = "registrar_tramo" in permitidas

            self.tabla_tramos.cargar((t.orden, [
                str(t.orden), t.origen, t.destino, t.transportista, en_texto(t.salida), en_texto(t.llegada) or "—",
                f"{t.temperatura:g} °C" if t.temperatura is not None else "—"]) for t in r.tramos)
            self.recepcion.controls = self._resumen_recepcion(r)
            self.detalle.visible = True
        self.ejecutar(accion)

    @staticmethod
    def _resumen_recepcion(r) -> list[ft.Control]:
        if r.recepcion is None:
            return []
        rec = r.recepcion
        lineas: list[ft.Control] = [
            ft.Divider(), ft.Text("Recepción", weight=ft.FontWeight.W_600),
            tema.texto_tenue(f"{en_texto(rec.fecha_hora)} · {rec.responsable} · {rec.laboratorio.nombre}", 13)]
        for d in rec.detalles:
            ok = d.aceptada
            lineas.append(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE if ok else ft.Icons.ERROR_OUTLINE, size=18,
                        color=ft.Colors.TEAL_700 if ok else ft.Colors.RED_700),
                ft.Text(f"{d.conservadora.codigo}: " + ("aceptada" if ok else "rechazada (" + etiquetas.motivos(m.value for m in d.motivos) + ")")
                        + f" · llegó a {d.temperatura_llegada:g} °C")]))
        return lineas

    def _despues_de(self, accion, ok: str) -> None:
        if self.ejecutar(accion, ok):
            self.cargar()
            self.elegir(self._remito_id)

    @manejador
    def agregar(self) -> None:
        def accion() -> None:
            conservadora_id = c.clave_de(self.libres)
            if conservadora_id is None:
                raise EntradaInvalida("Elegí la conservadora que se agrega.")
            svc.agregar_conservadora_a_remito(self._remito_id, conservadora_id)
        self._despues_de(accion, "Conservadora agregada.")

    @manejador
    def quitar(self, conservadora_id: int) -> None:
        self._despues_de(lambda: svc.quitar_conservadora_de_remito(self._remito_id, conservadora_id),
                         "Conservadora quitada (sus muestras siguen empaquetadas).")

    @manejador
    def cerrar(self) -> None:
        self._despues_de(lambda: svc.cerrar_remito(self._remito_id), "Remito cerrado.")

    @manejador
    def despachar(self) -> None:
        self._despues_de(lambda: svc.despachar_remito(self._remito_id, self.sesion.operador(), self.ubicacion.value),
                         "Remito despachado: sus muestras están en tránsito.")

    @manejador
    def registrar_tramo(self) -> None:
        def accion() -> None:
            llegada = a_fecha_hora(self.llegada.value, "La llegada") if (self.llegada.value or "").strip() else None
            svc.registrar_tramo(self._remito_id, self.origen.value, self.destino.value, self.transportista.value,
                                a_fecha_hora(self.salida.value, "La salida"), llegada, self.temperatura.value)
        if self.ejecutar(accion, "Tramo registrado."):
            for control in (self.origen, self.destino, self.salida, self.llegada, self.temperatura):
                control.value = ""
            self.cargar()
            self.elegir(self._remito_id)

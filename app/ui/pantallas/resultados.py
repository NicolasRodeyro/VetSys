"""Pantalla de resultados de análisis (proceso 7): registrar el resultado de una muestra recibida
y consultar los resultados ya registrados."""

from __future__ import annotations

import flet as ft

from app.servicios import muestras as svc_muestras
from app.servicios import resultados as svc
from app.servicios.excepciones import EntradaInvalida
from app.servicios.resultados import ValorIngresado
from app.ui import componentes as c
from app.ui import tema
from app.ui.entradas import en_texto
from app.ui.pantalla import Pantalla, manejador


def _referencia(minimo, maximo) -> str:
    if minimo is None and maximo is None:
        return "—"
    return f"{'' if minimo is None else f'{minimo:g}'} a {'' if maximo is None else f'{maximo:g}'}"


class PantallaResultados(Pantalla):
    clave = "resultados"
    titulo = "Resultados"
    icono = ft.Icons.ASSIGNMENT_TURNED_IN_OUTLINED
    grupo = "Laboratorio"

    def __init__(self, sesion) -> None:
        super().__init__(sesion)
        self._valores: list[ValorIngresado] = []

        # Registrar
        self.muestra = c.desplegable("Muestra recibida", expandir=True)
        self.parametro = c.campo("Parámetro", expandir=True, sugerencia="Por ejemplo Hematocrito")
        self.valor = c.campo("Valor", ancho=120)
        self.unidad = c.campo("Unidad", ancho=120, sugerencia="%")
        self.ref_min = c.campo("Ref. mín.", ancho=130)
        self.ref_max = c.campo("Ref. máx.", ancho=130)
        self.tabla_valores = c.Tabla(["Parámetro", "Valor", "Unidad", "Referencia"], al_elegir=self.quitar_valor,
                                     texto_boton="Quitar", icono=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                     vacia="Todavía no agregaste valores.")
        self.observaciones = c.campo("Observaciones", multilinea=True, expandir=True)

        # Consultar
        self.analizada = c.desplegable("Muestra analizada", expandir=True, al_elegir=self.ver)
        self.titulo_resultado = ft.Text("", weight=ft.FontWeight.W_600)
        self.tabla_resultado = c.Tabla(["Parámetro", "Valor", "Unidad", "Referencia", "Situación"], vacia="")
        self.nota_resultado = tema.texto_tenue("")
        self.resultado = tema.seccion("Resultado", self.titulo_resultado, self.tabla_resultado.vista, self.nota_resultado)
        self.resultado.visible = False

    def build(self) -> ft.Control:
        registrar = tema.seccion(
            "Registrar un resultado",
            self.muestra,
            tema.fila(self.parametro, self.valor, self.unidad, self.ref_min, self.ref_max,
                      c.boton("Agregar valor", ft.Icons.ADD, self.agregar_valor, "secundario")),
            self.tabla_valores.vista, self.observaciones,
            c.boton("Registrar resultado", ft.Icons.TASK_ALT, self.registrar))
        consultar = tema.seccion("Resultados registrados", self.analizada, self.resultado)
        return tema.pagina(
            tema.titulo_pantalla("Resultados de análisis",
                                 "Al registrar el resultado la muestra pasa a Analizada y se avisa al responsable de la mascota."),
            registrar, consultar)

    @manejador
    def al_mostrar(self) -> None:
        self.cargar()

    @manejador
    def cargar(self) -> None:
        def accion() -> None:
            c.poner_opciones(self.muestra, ((str(m.id), m.etiqueta) for m in svc_muestras.listar_resumenes_de_muestras("RECIBIDA")))
            c.poner_opciones(self.analizada, ((str(m.id), m.etiqueta) for m in svc_muestras.listar_resumenes_de_muestras("ANALIZADA")))
            self.resultado.visible = False
        self.ejecutar(accion)

    # ----------------------------------------------------------- valores del resultado

    def _mostrar_valores(self) -> None:
        convertidos = [v.a_dominio() for v in self._valores]  # números ya sanitizados, para mostrarlos prolijos
        self.tabla_valores.cargar((i, [d.parametro, f"{d.valor:g}", d.unidad, _referencia(d.ref_min, d.ref_max)])
                                  for i, d in enumerate(convertidos))

    @manejador
    def agregar_valor(self) -> None:
        def accion() -> None:
            valor = ValorIngresado(self.parametro.value or "", self.valor.value or "", self.unidad.value or "",
                                   self.ref_min.value, self.ref_max.value)
            valor.a_dominio()  # valida ahora, así el error aparece al agregar y no al registrar
            self._valores.append(valor)
        if self.ejecutar(accion):
            for control in (self.parametro, self.valor, self.ref_min, self.ref_max):
                control.value = ""
            self._mostrar_valores()

    @manejador
    def quitar_valor(self, posicion: int) -> None:
        del self._valores[posicion]
        self._mostrar_valores()

    @manejador
    def registrar(self) -> None:
        def accion() -> None:
            muestra_id = c.clave_de(self.muestra)
            if muestra_id is None:
                raise EntradaInvalida("Elegí la muestra cuyo resultado se registra.")
            self._registrado = svc.registrar_resultado(
                muestra_id, self.sesion.operador(), list(self._valores), self.observaciones.value or "")
        if not self.ejecutar(accion):
            return
        self._valores.clear()
        self._mostrar_valores()
        self.observaciones.value = ""
        self.cargar()
        self.avisar("Resultado registrado", self._registrado.avisos or ["Resultado registrado."])

    # ----------------------------------------------------------- consulta

    @manejador
    def ver(self) -> None:
        def accion() -> None:
            muestra_id = c.clave_de(self.analizada)
            if muestra_id is None:
                self.resultado.visible = False
                return
            r = svc.obtener_resultado(muestra_id)
            fuera = {id(x) for x in r.valores_fuera_de_rango()}
            self.titulo_resultado.value = f"Muestra #{muestra_id} · {en_texto(r.fecha_hora)} · {r.responsable}"
            self.tabla_resultado.cargar((i, [
                x.parametro, f"{x.valor:g}", x.unidad, _referencia(x.ref_min, x.ref_max),
                "⚠ Fuera de rango" if id(x) in fuera else "Normal"]) for i, x in enumerate(r.valores))
            self.nota_resultado.value = r.observaciones
            self.nota_resultado.visible = bool(r.observaciones)
            self.resultado.visible = True
        self.ejecutar(accion)


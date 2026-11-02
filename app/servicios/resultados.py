"""Casos de uso: resultados de análisis (proceso 7, primera parte)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.dominio.observadores_muestra import NotificadorCliente
from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado
from app.servicios import tiempo, validaciones as v
from app.servicios._comun import caso_de_uso, guardar_muestras, requerir, suscribir_trazabilidad
from app.servicios.excepciones import NoEncontrado


@dataclass(frozen=True)
class ValorIngresado:
    """Un valor tal como lo carga el usuario (todo puede venir como texto). El servicio lo
    sanitiza y lo convierte en un ValorResultado del dominio."""

    parametro: str
    valor: float | str
    unidad: str
    ref_min: float | str | None = None
    ref_max: float | str | None = None

    def a_dominio(self) -> ValorResultado:
        def opcional(dato, campo):
            return None if dato is None or str(dato).strip() == "" else v.numero(dato, campo)

        return ValorResultado(
            v.texto_obligatorio(self.parametro, "El parámetro", 80), v.numero(self.valor, "El valor"),
            v.texto_obligatorio(self.unidad, "La unidad", 30),
            opcional(self.ref_min, "El mínimo de referencia"), opcional(self.ref_max, "El máximo de referencia"))


@dataclass(frozen=True)
class ResultadoRegistrado:
    resultado: ResultadoAnalisis
    avisos: tuple[str, ...]  # aviso al responsable de la mascota: el resultado ya está


def registrar_resultado(muestra_id: int, responsable: str, valores: Iterable[ValorResultado | ValorIngresado],
                        observaciones: str = "", ubicacion: str = "Laboratorio") -> ResultadoRegistrado:
    """Registra el resultado del análisis: la muestra pasa a Analizada y se avisa al responsable."""
    valores = [x.a_dominio() if isinstance(x, ValorIngresado) else x for x in valores]
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    observaciones = v.texto_opcional(observaciones, "Las observaciones", 1000)
    ubicacion = v.texto_opcional(ubicacion, "La ubicación", 100)
    with caso_de_uso() as ctx:
        muestra = requerir(ctx.muestras.obtener(muestra_id), "la muestra", muestra_id)
        suscribir_trazabilidad(muestra)

        consulta = requerir(ctx.consultas.de_orden(muestra.orden), "la consulta de la orden", muestra_id)
        notificador = NotificadorCliente(consulta.mascota.responsable)
        muestra.suscribir(notificador)

        resultado = ResultadoAnalisis(muestra, responsable, tiempo.ahora(), valores, observaciones, ubicacion)
        guardar_muestras(ctx, [muestra])
        ctx.resultados.guardar(resultado)
    return ResultadoRegistrado(resultado, notificador.avisos)


def obtener_resultado(muestra_id: int) -> ResultadoAnalisis:
    with caso_de_uso() as ctx:
        muestra = requerir(ctx.muestras.obtener(muestra_id), "la muestra", muestra_id)
        resultado = ctx.resultados.obtener_de_muestra(muestra)
        if resultado is None:
            raise NoEncontrado(f"La muestra {muestra_id} todavía no tiene resultado")
        return resultado

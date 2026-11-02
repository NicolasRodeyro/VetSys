"""Casos de uso: remito biológico, cadena de envío y recepción en el laboratorio
(proceso 4 segunda parte, y procesos 5 y 6)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from app.dominio.enums import EstadoPrecinto
from app.dominio.excepciones import ReglaNegocio
from app.dominio.observadores_muestra import AlertaRechazo
from app.dominio.recepcion import DetalleRecepcion, Recepcion
from app.dominio.remito_biologico import RemitoBiologico
from app.persistencia.contexto import Contexto
from app.servicios import tiempo, validaciones as v
from app.servicios._comun import caso_de_uso, guardar_muestras, muestras_de, requerir, suscribir_trazabilidad


@dataclass(frozen=True)
class DetalleDeRecepcion:
    """Lo que el laboratorio constató de UNA conservadora al recibirla."""

    conservadora_id: int
    estado_precinto: EstadoPrecinto | str
    temperatura_llegada: float | str
    observacion: str = ""


@dataclass(frozen=True)
class RecepcionRegistrada:
    remito: RemitoBiologico
    alertas: tuple[str, ...]  # avisos para la clínica por las muestras rechazadas (re-extracción)


def _cargar(ctx: Contexto, remito_id: int) -> RemitoBiologico:
    """Carga el remito y deja suscripta la trazabilidad en todas sus muestras."""
    remito = requerir(ctx.remitos.obtener(remito_id), "el remito", remito_id)
    suscribir_trazabilidad(*muestras_de(remito))
    return remito


def _guardar(ctx: Contexto, remito: RemitoBiologico) -> None:
    """Guarda lo que pudo cambiar: las muestras (con su orden), las conservadoras y el remito."""
    guardar_muestras(ctx, muestras_de(remito))
    for conservadora in remito.conservadoras:
        ctx.conservadoras.guardar(conservadora)
    ctx.remitos.guardar(remito)


def crear_remito(clinica_id: int, laboratorio_id: int, numero: str | None = None) -> RemitoBiologico:
    with caso_de_uso() as ctx:
        clinica = requerir(ctx.clinicas.obtener(clinica_id), "la clínica", clinica_id)
        laboratorio = requerir(ctx.laboratorios.obtener(laboratorio_id), "el laboratorio", laboratorio_id)
        numero = v.texto_obligatorio(numero, "El número de remito", 30) if numero else ctx.remitos.proximo_numero()
        if ctx.remitos.obtener_por_numero(numero) is not None:
            raise ReglaNegocio(f"Ya existe el remito {numero}")
        remito = RemitoBiologico(numero, clinica, laboratorio)
        ctx.remitos.guardar(remito)
    return remito


def agregar_conservadora_a_remito(remito_id: int, conservadora_id: int) -> RemitoBiologico:
    with caso_de_uso() as ctx:
        remito = _cargar(ctx, remito_id)
        conservadora = requerir(ctx.conservadoras.obtener(conservadora_id), "la conservadora", conservadora_id)
        if conservadora not in remito.conservadoras and ctx.conservadoras.esta_en_remito(conservadora):
            raise ReglaNegocio(f"La conservadora {conservadora.codigo} ya viaja en otro remito")
        remito.agregar_conservadora(conservadora)
        _guardar(ctx, remito)
    return remito


def quitar_conservadora_de_remito(remito_id: int, conservadora_id: int) -> RemitoBiologico:
    """Solo con el remito abierto. Quitarla NO desempaqueta sus muestras."""
    with caso_de_uso() as ctx:
        remito = _cargar(ctx, remito_id)
        conservadora = requerir(ctx.conservadoras.obtener(conservadora_id), "la conservadora", conservadora_id)
        remito.quitar_conservadora(conservadora)
        _guardar(ctx, remito)
    return remito


def cerrar_remito(remito_id: int) -> RemitoBiologico:
    """Exige al menos una conservadora y que todas tengan precinto."""
    with caso_de_uso() as ctx:
        remito = _cargar(ctx, remito_id)
        remito.cerrar()
        _guardar(ctx, remito)
    return remito


def despachar_remito(remito_id: int, responsable: str, ubicacion: str = "") -> RemitoBiologico:
    """Despacha el remito: todas sus muestras pasan a En tránsito."""
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    ubicacion = v.texto_opcional(ubicacion, "La ubicación", 100)
    with caso_de_uso() as ctx:
        remito = _cargar(ctx, remito_id)
        remito.despachar(responsable, ubicacion)
        _guardar(ctx, remito)
    return remito


def registrar_tramo(remito_id: int, origen: str, destino: str, transportista: str, salida: datetime,
                    llegada: datetime | None = None, temperatura: float | str | None = None) -> RemitoBiologico:
    """Agrega un tramo a la cadena de envío (el remito tiene que estar en tránsito)."""
    origen = v.texto_obligatorio(origen, "El origen", 100)
    destino = v.texto_obligatorio(destino, "El destino", 100)
    transportista = v.texto_obligatorio(transportista, "El transportista", 100)
    salida = v.fecha_hora(salida, "La salida")
    llegada = None if llegada is None else v.fecha_hora(llegada, "La llegada")
    temperatura = None if temperatura in (None, "") else v.numero(temperatura, "La temperatura")
    with caso_de_uso() as ctx:
        remito = _cargar(ctx, remito_id)
        remito.registrar_tramo(origen, destino, transportista, salida, llegada, temperatura)
        _guardar(ctx, remito)
    return remito


def registrar_recepcion(remito_id: int, responsable: str, detalles: Iterable[DetalleDeRecepcion],
                        fecha_hora: datetime | None = None) -> RecepcionRegistrada:
    """El laboratorio registra la recepción: un detalle por conservadora, con el estado del
    precinto y la temperatura de llegada. Cada muestra queda Recibida o Rechazada según su
    conservadora, y el remito queda Recibido, Recibido parcial o Rechazado."""
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    fecha_hora = v.fecha_hora(fecha_hora if fecha_hora is not None else tiempo.ahora(), "La fecha y hora")
    with caso_de_uso() as ctx:
        remito = _cargar(ctx, remito_id)
        alerta = AlertaRechazo()
        for muestra in muestras_de(remito):
            muestra.suscribir(alerta)  # un solo observador junta los avisos de todas las muestras

        por_id = {c.id: c for c in remito.conservadoras}
        detalles_dominio = []
        for d in detalles:
            conservadora = por_id.get(d.conservadora_id)
            if conservadora is None:
                raise ReglaNegocio(f"La conservadora {d.conservadora_id} no está en el remito {remito.numero}")
            detalles_dominio.append(DetalleRecepcion(
                conservadora,
                v.opcion(d.estado_precinto, EstadoPrecinto, "El estado del precinto"),
                v.numero(d.temperatura_llegada, "La temperatura de llegada"),
                v.texto_opcional(d.observacion, "La observación", 300)))

        remito.registrar_recepcion(Recepcion(remito.destino, responsable, fecha_hora, detalles_dominio))
        _guardar(ctx, remito)
    return RecepcionRegistrada(remito, alerta.alertas)


def obtener_remito(remito_id: int) -> RemitoBiologico:
    with caso_de_uso() as ctx:
        return requerir(ctx.remitos.obtener(remito_id), "el remito", remito_id)


def listar_remitos(estado: str | None = None) -> list[RemitoBiologico]:
    with caso_de_uso() as ctx:
        if estado is None:
            return ctx.remitos.listar()
        return ctx.remitos.listar_por_estado(v.texto_obligatorio(estado, "El estado", 20).upper())

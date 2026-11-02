"""Casos de uso: extracción, empaquetado y precintado de muestras (proceso 4, primera parte).

Al cargar una muestra, cada caso de uso suscribe RegistroTrazabilidad (los observadores
no se persisten); sin eso el cambio de estado no quedaría en el historial.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.dominio.cambio_estado import CambioEstado
from app.dominio.conservadora import Conservadora
from app.dominio.excepciones import ReglaNegocio
from app.dominio.muestra import Muestra
from app.servicios import tiempo, validaciones as v
from app.servicios._comun import caso_de_uso, guardar_muestras, requerir, suscribir_trazabilidad


def registrar_extraccion(orden_id: int, responsable: str, ubicacion: str = "", observacion: str = "") -> Muestra:
    """Extrae una muestra para una orden de derivación. Una orden tiene una sola muestra activa a la vez."""
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    ubicacion = v.texto_opcional(ubicacion, "La ubicación", 100)
    observacion = v.texto_opcional(observacion, "La observación", 300)
    with caso_de_uso() as ctx:
        orden = requerir(ctx.ordenes.obtener(orden_id), "la orden de derivación", orden_id)
        muestra = Muestra(orden, responsable, ubicacion, observacion)  # ReglaNegocio si ya hay una activa
        suscribir_trazabilidad(muestra)
        ctx.ordenes.guardar(orden)
    return muestra


def registrar_reextraccion(muestra_id: int, responsable: str, ubicacion: str = "", observacion: str = "") -> Muestra:
    """Re-extracción sin cargo de una muestra rechazada: una muestra nueva en la MISMA orden.
    El comprobante no cambia, porque se cobra por orden."""
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    ubicacion = v.texto_opcional(ubicacion, "La ubicación", 100)
    observacion = v.texto_opcional(observacion, "La observación", 300)
    with caso_de_uso() as ctx:
        rechazada = requerir(ctx.muestras.obtener(muestra_id), "la muestra", muestra_id)
        if rechazada.esta_activa():
            raise ReglaNegocio("Solo se puede re-extraer una muestra que fue rechazada")
        orden = rechazada.orden
        nueva = Muestra(orden, responsable, ubicacion, observacion or f"Re-extracción de la muestra {muestra_id}")
        suscribir_trazabilidad(nueva)
        ctx.ordenes.guardar(orden)
    return nueva


def crear_conservadora(codigo: str, capacidad: int, temp_min: float, temp_max: float) -> Conservadora:
    codigo = v.texto_obligatorio(codigo, "El código", 30)
    capacidad = v.entero_positivo(capacidad, "La capacidad")
    temp_min, temp_max = v.numero(temp_min, "La temperatura mínima"), v.numero(temp_max, "La temperatura máxima")
    with caso_de_uso() as ctx:
        if ctx.conservadoras.obtener_por_codigo(codigo) is not None:
            raise ReglaNegocio(f"Ya existe una conservadora con el código {codigo}")
        conservadora = Conservadora(codigo, capacidad, temp_min, temp_max)
        ctx.conservadoras.guardar(conservadora)
    return conservadora


def empaquetar_muestra(muestra_id: int, conservadora_id: int, responsable: str, ubicacion: str = "") -> Conservadora:
    """Empaqueta la muestra en la conservadora: valida temperatura, capacidad y que siga abierta."""
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    ubicacion = v.texto_opcional(ubicacion, "La ubicación", 100)
    with caso_de_uso() as ctx:
        muestra = requerir(ctx.muestras.obtener(muestra_id), "la muestra", muestra_id)
        suscribir_trazabilidad(muestra)
        conservadora = requerir(ctx.conservadoras.obtener(conservadora_id), "la conservadora", conservadora_id)
        conservadora.agregar_muestra(muestra, responsable, ubicacion)
        guardar_muestras(ctx, [muestra])
        ctx.conservadoras.guardar(conservadora)
    return conservadora


def precintar_conservadora(conservadora_id: int, numero_precinto: str, responsable: str) -> Conservadora:
    """Coloca el precinto sanitario: desde ahí la conservadora queda cerrada."""
    numero_precinto = v.texto_obligatorio(numero_precinto, "El número de precinto", 30)
    responsable = v.texto_obligatorio(responsable, "El responsable", 80)
    with caso_de_uso() as ctx:
        conservadora = requerir(ctx.conservadoras.obtener(conservadora_id), "la conservadora", conservadora_id)
        conservadora.precintar(numero_precinto, responsable, tiempo.ahora())
        ctx.conservadoras.guardar(conservadora)
    return conservadora


# ---------------------------------------------------------------- consultas de lectura


@dataclass(frozen=True)
class ResumenMuestra:
    """Lo que necesita un listado de muestras: a qué mascota, cliente y análisis corresponde."""

    id: int
    orden_id: int
    analisis: str
    mascota: str
    cliente: str
    estado: str
    motivos: tuple[str, ...]

    @property
    def etiqueta(self) -> str:
        return f"#{self.id} · {self.analisis} · {self.mascota} ({self.cliente}) · {self.estado}"


def _resumir(ctx, muestra: Muestra) -> ResumenMuestra:
    consulta = requerir(ctx.consultas.de_orden(muestra.orden), "la consulta de la orden", muestra.id)
    responsable = consulta.mascota.responsable
    return ResumenMuestra(
        muestra.id, muestra.orden.id, muestra.tipo_analisis.nombre, consulta.mascota.nombre,
        f"{responsable.nombre} {responsable.apellido}", muestra.estado.nombre,
        tuple(motivo.value for motivo in muestra.estado.motivos))


def resumen_de_muestra(muestra_id: int) -> ResumenMuestra:
    with caso_de_uso() as ctx:
        return _resumir(ctx, requerir(ctx.muestras.obtener(muestra_id), "la muestra", muestra_id))


def listar_resumenes_de_muestras(estado: str | None = None) -> list[ResumenMuestra]:
    """Resumen de las muestras en un estado, o de todas las que están en curso si no se indica."""
    with caso_de_uso() as ctx:
        nombres = ([v.texto_obligatorio(estado, "El estado", 20).upper()] if estado is not None
                   else ["EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA"])
        return [_resumir(ctx, m) for nombre in nombres for m in ctx.muestras.listar_por_estado(nombre)]


def obtener_muestra(muestra_id: int) -> Muestra:
    with caso_de_uso() as ctx:
        return requerir(ctx.muestras.obtener(muestra_id), "la muestra", muestra_id)


def trazabilidad_de_muestra(muestra_id: int) -> tuple[CambioEstado, ...]:
    """El historial completo de la muestra, del más viejo al más nuevo."""
    return obtener_muestra(muestra_id).historial


def listar_muestras(estado: str | None = None) -> list[Muestra]:
    """Muestras en un estado (ej. 'EXTRAIDA'), o todas las que están en curso si no se indica."""
    with caso_de_uso() as ctx:
        if estado is not None:
            return ctx.muestras.listar_por_estado(v.texto_obligatorio(estado, "El estado", 20).upper())
        return [m for nombre in ("EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA")
                for m in ctx.muestras.listar_por_estado(nombre)]


def obtener_conservadora(conservadora_id: int) -> Conservadora:
    with caso_de_uso() as ctx:
        return requerir(ctx.conservadoras.obtener(conservadora_id), "la conservadora", conservadora_id)


def listar_conservadoras(solo_sin_remito: bool = False) -> list[Conservadora]:
    with caso_de_uso() as ctx:
        return ctx.conservadoras.listar_sin_remito() if solo_sin_remito else ctx.conservadoras.listar()

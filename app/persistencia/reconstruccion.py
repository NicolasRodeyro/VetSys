"""Reconstrucción de objetos del dominio a partir de lo guardado en la base.

Cargar un objeto de la base NO es crearlo de nuevo: no hay que repetir las reglas
de creación (una muestra no vuelve a registrarse en su orden, un comprobante no se
recalcula con precios nuevos, una consulta no recalcula sus advertencias).

Por eso las clases con esos efectos se reconstruyen acá, salteando su __init__ y
cargando directamente su estado. Este es el ÚNICO módulo que conoce cómo están
armados por dentro esos objetos: si cambia el dominio, se cambia acá, y los tests
de integración (guardar y volver a cargar) avisan si algo quedó desfasado.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime

from app.dominio.cambio_estado import CambioEstado
from app.dominio.comprobante import Comprobante
from app.dominio.consulta import Consulta
from app.dominio.conservadora import Conservadora
from app.dominio.estados_muestra import EstadoMuestra
from app.dominio.estados_remito import EstadoRemito
from app.dominio.historia_clinica import HistoriaClinica
from app.dominio.muestra import Muestra
from app.dominio.orden_derivacion import OrdenDerivacion
from app.dominio.precinto import Precinto
from app.dominio.recepcion import Recepcion
from app.dominio.remito_biologico import RemitoBiologico
from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado
from app.dominio.turno import Turno
from app.dominio.veterinario import Veterinario


def restaurar_muestra(
    orden: OrdenDerivacion,
    estado: EstadoMuestra,
    historial: Iterable[CambioEstado],
    reloj: Callable[[], datetime] = datetime.now,
) -> Muestra:
    muestra = Muestra.__new__(Muestra)
    muestra.id = None
    muestra._orden = orden
    muestra._reloj = reloj
    muestra._observadores = []
    muestra._estado = estado
    muestra._historial = list(historial)
    orden._muestras.append(muestra)
    return muestra


def restaurar_conservadora(
    conservadora: Conservadora, muestras: Iterable[Muestra], precinto: Precinto | None
) -> Conservadora:
    """`conservadora` se crea con su constructor; acá se le cargan muestras y precinto
    sin volver a empaquetar (las muestras ya están empaquetadas)."""
    conservadora._muestras = list(muestras)
    conservadora._precinto = precinto
    return conservadora


def restaurar_remito(
    remito: RemitoBiologico,
    estado: EstadoRemito,
    conservadoras: Iterable[Conservadora],
    tramos: Iterable,
    recepcion: Recepcion | None,
) -> RemitoBiologico:
    remito._estado = estado
    remito._conservadoras = list(conservadoras)
    remito._tramos = list(tramos)
    remito._recepcion = recepcion
    return remito


def restaurar_consulta(
    tipo, fecha_hora, mascota, veterinario, turno, diagnostico: str, tratamiento: str
) -> Consulta:
    """Salteando el __init__: no se vuelven a validar el turno ni la mascota, y las
    advertencias, órdenes y comprobante se cargan después con las funciones de abajo."""
    consulta = Consulta.__new__(Consulta)
    consulta.id = None
    consulta._tipo = tipo
    consulta._fecha_hora = fecha_hora
    consulta._mascota = mascota
    consulta._veterinario = veterinario
    consulta._turno = turno
    consulta.diagnostico = diagnostico
    consulta.tratamiento = tratamiento
    consulta._advertencias = []
    consulta._ordenes = []
    consulta._comprobante = None
    return consulta


def adjuntar_orden(consulta: Consulta, orden: OrdenDerivacion) -> None:
    """La orden ya existía: no se crea una nueva con emitir_orden()."""
    consulta._ordenes.append(orden)


def asignar_comprobante(consulta: Consulta, comprobante: Comprobante) -> None:
    """El comprobante ya estaba emitido: no se recalcula con los precios de hoy."""
    consulta._comprobante = comprobante


def fijar_activo(entidad, activo: bool) -> None:
    """Cliente y Mascota: restaura la baja lógica sin pasar por las reglas de dar_de_baja()
    (que dependen del orden en que se carguen las mascotas)."""
    if hasattr(entidad, "_activo"):
        entidad._activo = activo
    else:
        entidad._activa = activo


def adjuntar_consulta(historia: HistoriaClinica, consulta: Consulta) -> None:
    """La consulta ya estaba registrada en la historia: no se vuelven a calcular advertencias."""
    historia._consultas.append(consulta)


def cargar_agenda(veterinario: Veterinario, turnos: Iterable[Turno]) -> None:
    """Los turnos guardados ya fueron validados: no se vuelve a controlar la superposición."""
    veterinario._turnos = list(turnos)


def restaurar_resultado(
    muestra: Muestra,
    responsable: str,
    fecha_hora: datetime,
    valores: Iterable[ValorResultado],
    observaciones: str,
) -> ResultadoAnalisis:
    """La muestra ya está Analizada: no se vuelve a pedir `muestra.analizar()`."""
    resultado = ResultadoAnalisis.__new__(ResultadoAnalisis)
    resultado._muestra = muestra
    resultado.responsable = responsable
    resultado._fecha_hora = fecha_hora
    resultado._valores = tuple(valores)
    resultado.observaciones = observaciones
    return resultado

"""Casos de uso: consultas médicas, órdenes de derivación y comprobantes (proceso 3)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.dominio.comprobante import Comprobante
from app.dominio.consulta import Consulta
from app.dominio.enums import Prioridad, TipoConsulta
from app.dominio.excepciones import ReglaNegocio
from app.dominio.orden_derivacion import OrdenDerivacion
from app.servicios import tiempo, validaciones as v
from app.servicios._comun import caso_de_uso, requerir


def registrar_consulta(mascota_id: int, veterinario_id: int, tipo: TipoConsulta | str,
                       fecha_hora: datetime | None = None, turno_id: int | None = None,
                       diagnostico: str = "", tratamiento: str = "") -> Consulta:
    """Registra una consulta. Si la mascota tiene vacunas pendientes **se advierte pero no se
    bloquea**: la consulta se registra igual y queda con las advertencias (ver `consulta.advertencias`)."""
    tipo = v.opcion(tipo, TipoConsulta, "El tipo de consulta")
    fecha_hora = v.fecha_hora(fecha_hora if fecha_hora is not None else tiempo.ahora(), "La fecha y hora")
    diagnostico = v.texto_opcional(diagnostico, "El diagnóstico", 1000)
    tratamiento = v.texto_opcional(tratamiento, "El tratamiento", 1000)
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        if not mascota.activa:
            raise ReglaNegocio(f"{mascota.nombre} está dada de baja: no se la puede atender")
        veterinario = requerir(ctx.veterinarios.obtener(veterinario_id, con_agenda=False), "el veterinario", veterinario_id)
        turno = None
        if turno_id is not None:
            dueno = requerir(ctx.veterinarios.de_turno(turno_id), "el turno", turno_id)
            if dueno is not veterinario:
                raise ReglaNegocio("El turno es de otro veterinario")
            turno = ctx.veterinarios.turno_por_id(turno_id)
            if ctx.consultas.turno_tiene_consulta(turno):
                raise ReglaNegocio("El turno ya fue atendido")

        consulta = Consulta(tipo, fecha_hora, mascota, veterinario, turno, diagnostico, tratamiento)
        mascota.historia_clinica.registrar_consulta(consulta)  # control de vacunas: advierte, no bloquea
        ctx.consultas.guardar(consulta)
    return consulta


def actualizar_consulta(consulta_id: int, diagnostico: str | None = None, tratamiento: str | None = None) -> Consulta:
    with caso_de_uso() as ctx:
        consulta = requerir(ctx.consultas.obtener(consulta_id), "la consulta", consulta_id)
        if consulta.cerrada:
            raise ReglaNegocio("La consulta ya está cerrada: no se puede modificar")
        if diagnostico is not None:
            consulta.diagnostico = v.texto_opcional(diagnostico, "El diagnóstico", 1000)
        if tratamiento is not None:
            consulta.tratamiento = v.texto_opcional(tratamiento, "El tratamiento", 1000)
        ctx.consultas.guardar(consulta)
    return consulta


def emitir_orden(consulta_id: int, tipo_analisis: str, prioridad: Prioridad | str = Prioridad.NORMAL) -> OrdenDerivacion:
    """Emite una orden de derivación a laboratorio. `tipo_analisis` es el nombre del análisis del catálogo."""
    prioridad = v.opcion(prioridad, Prioridad, "La prioridad")
    nombre = v.texto_obligatorio(tipo_analisis, "El tipo de análisis", 80)
    with caso_de_uso() as ctx:
        consulta = requerir(ctx.consultas.obtener(consulta_id), "la consulta", consulta_id)
        analisis = requerir(ctx.tipos_analisis.obtener_por_nombre(nombre), "el tipo de análisis", nombre)
        orden = consulta.emitir_orden(analisis, prioridad)  # falla si la consulta ya está cerrada
        ctx.consultas.guardar(consulta)
    return orden


def cerrar_consulta(consulta_id: int, honorarios: Decimal | str | int) -> Comprobante:
    """Cierra la consulta y emite su único comprobante: la consulta más un ítem por cada orden
    de derivación (con el precio del análisis). Se cobra por orden, no por muestra."""
    honorarios = v.monto(honorarios, "Los honorarios")
    with caso_de_uso() as ctx:
        consulta = requerir(ctx.consultas.obtener(consulta_id), "la consulta", consulta_id)
        comprobante = consulta.cerrar(honorarios, tiempo.ahora())
        ctx.consultas.guardar(consulta)
    return comprobante


def obtener_consulta(consulta_id: int) -> Consulta:
    with caso_de_uso() as ctx:
        return requerir(ctx.consultas.obtener(consulta_id), "la consulta", consulta_id)


def listar_consultas_de_mascota(mascota_id: int) -> list[Consulta]:
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        return list(mascota.historia_clinica.consultas)

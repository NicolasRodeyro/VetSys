"""Consultas de los catálogos (solo lectura): para llenar listas desplegables en la interfaz."""

from __future__ import annotations

from app.dominio.clinica import Clinica
from app.dominio.especie import Especie
from app.dominio.laboratorio import Laboratorio
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.veterinario import Veterinario
from app.servicios._comun import caso_de_uso, requerir


def listar_especies() -> list[Especie]:
    with caso_de_uso() as ctx:
        return ctx.especies.listar()


def listar_clinicas() -> list[Clinica]:
    with caso_de_uso() as ctx:
        return ctx.clinicas.listar()


def listar_laboratorios() -> list[Laboratorio]:
    with caso_de_uso() as ctx:
        return ctx.laboratorios.listar()


def listar_tipos_analisis() -> list[TipoAnalisis]:
    with caso_de_uso() as ctx:
        return ctx.tipos_analisis.listar()


def listar_veterinarios(clinica_id: int | None = None) -> list[Veterinario]:
    """Los veterinarios de una clínica, o de todas si no se indica (sin sus agendas)."""
    with caso_de_uso() as ctx:
        clinicas = ([requerir(ctx.clinicas.obtener(clinica_id), "la clínica", clinica_id)]
                    if clinica_id is not None else ctx.clinicas.listar())
        return [vet for clinica in clinicas for vet in ctx.veterinarios.listar_de_clinica(clinica)]

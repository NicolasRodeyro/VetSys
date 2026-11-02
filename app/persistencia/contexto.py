"""Contexto de persistencia: los repositorios de un caso de uso.

Un contexto = una conexión (una transacción) + un mapa de identidad compartido por
todos los repositorios. Así, dentro de un caso de uso, cargar dos veces la misma fila
devuelve el mismo objeto, y los repositorios pueden pedirse unos a otros lo que
necesitan. Uso típico (lo hace la capa de servicios):

    with transaccion() as conexion:
        ctx = Contexto(conexion)
        cliente = ctx.clientes.obtener_por_dni("30111222")
        ...
        ctx.clientes.guardar(cliente)
"""

from __future__ import annotations

import sqlite3

from app.persistencia.identidad import MapaIdentidad
from app.persistencia.repositorios_atencion import (
    RepositorioClinicas,
    RepositorioComprobantes,
    RepositorioConsultas,
    RepositorioLaboratorios,
    RepositorioOrdenes,
    RepositorioTiposAnalisis,
    RepositorioVeterinarios,
)
from app.persistencia.repositorios_envio import (
    RepositorioConservadoras,
    RepositorioMuestras,
    RepositorioRemitos,
)
from app.persistencia.repositorios_personas import RepositorioClientes, RepositorioEspecies
from app.persistencia.repositorios_resultados import RepositorioResultados


class Contexto:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion
        self.mapa = MapaIdentidad()
        self.especies = RepositorioEspecies(self)
        self.clientes = RepositorioClientes(self)
        self.clinicas = RepositorioClinicas(self)
        self.laboratorios = RepositorioLaboratorios(self)
        self.veterinarios = RepositorioVeterinarios(self)
        self.tipos_analisis = RepositorioTiposAnalisis(self)
        self.consultas = RepositorioConsultas(self)
        self.ordenes = RepositorioOrdenes(self)
        self.comprobantes = RepositorioComprobantes(self)
        self.muestras = RepositorioMuestras(self)
        self.conservadoras = RepositorioConservadoras(self)
        self.remitos = RepositorioRemitos(self)
        self.resultados = RepositorioResultados(self)

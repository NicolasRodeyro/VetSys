"""Reporte: vacunas pendientes por mascota, con días de atraso y responsable de contacto.

Qué calcula (no está guardado): a una fecha de corte, qué vacunas del esquema de cada especie
le faltan a cada mascota activa, hace cuántos días venció cada una y a quién avisar.

A diferencia de los otros reportes, este NO arma el resultado con SQL: carga las mascotas con
su historia clínica (vía la persistencia) y le pregunta a cada una por sus vacunas pendientes.
Así la regla de qué vacuna está pendiente y cuándo venció vive en un solo lugar, el dominio
(`HistoriaClinica.vacunas_pendientes_con_vencimiento`), y el reporte no la repite.

La fecha de corte es el «hasta» del filtro (es una foto a ese día, no un rango). El filtro de
clínica no aplica: una mascota no pertenece a una clínica.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.persistencia.conexion import transaccion
from app.persistencia.contexto import Contexto
from app.reportes import formato
from app.reportes.filtros import FiltroReporte
from app.reportes.resultado import Grafico, ResultadoReporte

TITULO = "Vacunas pendientes por mascota"
DESCRIPCION = ("Foto al día «hasta»: vacunas del esquema de cada especie que le faltan a cada mascota "
               "activa, con los días de atraso y el contacto del responsable. El filtro de clínica no aplica.")


@dataclass(frozen=True)
class VacunaPendiente:
    mascota: str
    especie: str
    responsable: str
    contacto: str
    vacuna: str
    vencimiento: date

    def dias_de_atraso(self, corte: date) -> int:
        return (corte - self.vencimiento).days


# ---------------------------------------------------------------- lectura (dominio)

def _leer(corte: date) -> list[VacunaPendiente]:
    pendientes: list[VacunaPendiente] = []
    with transaccion() as conexion:
        ctx = Contexto(conexion)
        for cliente in ctx.clientes.listar():
            contacto = cliente.telefono or cliente.email or "sin contacto"
            responsable = f"{cliente.nombre} {cliente.apellido}"
            for mascota in cliente.mascotas:
                if not mascota.activa:
                    continue  # una mascota de baja ya no se atiende
                for vacuna, vencimiento in mascota.historia_clinica.vacunas_pendientes_con_vencimiento(corte):
                    pendientes.append(VacunaPendiente(
                        mascota.nombre, mascota.especie.nombre, responsable, contacto,
                        vacuna.nombre, vencimiento))
    return pendientes


# ---------------------------------------------------------------- cálculo (Python puro)

def ordenar(pendientes: list[VacunaPendiente], corte: date) -> list[VacunaPendiente]:
    """Las más atrasadas primero; a igual atraso, por mascota y vacuna (orden estable y legible)."""
    return sorted(pendientes, key=lambda p: (-p.dias_de_atraso(corte), p.mascota, p.vacuna))


def pendientes_por_especie(pendientes: list[VacunaPendiente]) -> dict[str, int]:
    conteo: dict[str, int] = {}
    for p in pendientes:
        conteo[p.especie] = conteo.get(p.especie, 0) + 1
    return dict(sorted(conteo.items()))


# ---------------------------------------------------------------- reporte completo

COLUMNAS = ["Mascota", "Especie", "Responsable", "Contacto", "Vacuna", "Venció", "Días de atraso"]


def generar(filtro: FiltroReporte) -> ResultadoReporte:
    corte = filtro.hasta
    pendientes = ordenar(_leer(corte), corte)

    filas = [[p.mascota, p.especie, p.responsable, p.contacto, p.vacuna,
              formato.fecha(p.vencimiento), formato.dias(p.dias_de_atraso(corte))]
             for p in pendientes]

    notas = [f"{len(pendientes)} vacuna(s) pendiente(s) al {formato.fecha(corte)}."]
    if filtro.clinica_id is not None:
        notas.append("El filtro de clínica no aplica a este reporte: se listan todas las mascotas.")
    if not pendientes:
        notas.append("Ninguna mascota tiene vacunas pendientes a esa fecha.")

    grafico = None
    por_especie = pendientes_por_especie(pendientes)
    if por_especie:
        grafico = Grafico(
            "Vacunas pendientes por especie",
            list(por_especie.keys()),
            {"Pendientes": [float(n) for n in por_especie.values()]},
            "Cantidad")
    return ResultadoReporte(TITULO, COLUMNAS, filas, notas, grafico)

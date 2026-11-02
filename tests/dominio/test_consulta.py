from datetime import date, datetime

import pytest

from app.dominio.consulta import Consulta
from app.dominio.enums import Sexo, TipoConsulta
from app.dominio.especie import Especie
from app.dominio.excepciones import ReglaNegocio
from app.dominio.mascota import Mascota
from app.dominio.turno import Turno
from tests.dominio.conftest import ANTIRRABICA, SEXTUPLE

# El perro de la fixture nació el 10/01/2026. A los 4 meses (10/05/2026)
# le corresponden las dos vacunas del esquema.
CUATRO_MESES = datetime(2026, 5, 10, 11, 0)


def nueva_consulta(perro, veterinario, **datos) -> Consulta:
    datos.setdefault("tipo", TipoConsulta.CONSULTA)
    datos.setdefault("fecha_hora", CUATRO_MESES)
    return Consulta(mascota=perro, veterinario=veterinario, **datos)


# --- Turno opcional ---

def test_urgencia_se_registra_sin_turno(perro, veterinario):
    consulta = nueva_consulta(perro, veterinario, tipo=TipoConsulta.URGENCIA)
    perro.historia_clinica.registrar_consulta(consulta)

    assert consulta.turno is None
    assert consulta in perro.historia_clinica.consultas


def test_consulta_con_turno_propio_es_valida(perro, veterinario):
    turno = Turno(CUATRO_MESES, 30, perro)
    consulta = nueva_consulta(perro, veterinario, turno=turno)
    assert consulta.turno is turno


def test_consulta_con_turno_de_otra_mascota_falla(perro, veterinario, cliente):
    otra = Mascota("Mimi", Especie("Gato"), Sexo.HEMBRA, date(2025, 1, 1), cliente)
    turno_ajeno = Turno(CUATRO_MESES, 30, otra)
    with pytest.raises(ReglaNegocio, match="otra mascota"):
        nueva_consulta(perro, veterinario, turno=turno_ajeno)


def test_consulta_con_turno_cancelado_falla(perro, veterinario):
    turno = Turno(CUATRO_MESES, 30, perro)
    turno.cancelar()
    with pytest.raises(ReglaNegocio, match="cancelado"):
        nueva_consulta(perro, veterinario, turno=turno)


# --- Advertencia de vacunas (se advierte, no se bloquea) ---

def test_consulta_con_vacunas_pendientes_se_registra_con_advertencias(perro, veterinario):
    consulta = nueva_consulta(perro, veterinario)

    perro.historia_clinica.registrar_consulta(consulta)  # no lanza

    assert consulta in perro.historia_clinica.consultas  # se registró igual
    assert consulta.advertencias == (
        f"Vacuna pendiente: {SEXTUPLE.nombre}",
        f"Vacuna pendiente: {ANTIRRABICA.nombre}",
    )


def test_consulta_con_vacunas_al_dia_no_tiene_advertencias(perro, veterinario):
    historia = perro.historia_clinica
    historia.registrar_vacuna(SEXTUPLE, date(2026, 3, 10))
    historia.registrar_vacuna(ANTIRRABICA, date(2026, 4, 10))

    consulta = nueva_consulta(perro, veterinario)
    historia.registrar_consulta(consulta)

    assert consulta.advertencias == ()
    assert consulta in historia.consultas


def test_las_advertencias_dependen_de_la_fecha_de_la_consulta(perro, veterinario):
    # A los 2 meses y medio solo corresponde la Sextuple (2 meses).
    consulta = nueva_consulta(perro, veterinario, fecha_hora=datetime(2026, 3, 25, 9, 0))
    perro.historia_clinica.registrar_consulta(consulta)
    assert consulta.advertencias == (f"Vacuna pendiente: {SEXTUPLE.nombre}",)


# --- Reglas de la historia ---

def test_historia_rechaza_consulta_de_otra_mascota(perro, veterinario, cliente):
    otra = Mascota("Mimi", Especie("Gato"), Sexo.HEMBRA, date(2025, 1, 1), cliente)
    consulta_ajena = nueva_consulta(otra, veterinario)
    with pytest.raises(ReglaNegocio, match="otra mascota"):
        perro.historia_clinica.registrar_consulta(consulta_ajena)


def test_historia_rechaza_registrar_dos_veces_la_misma_consulta(perro, veterinario):
    consulta = nueva_consulta(perro, veterinario)
    perro.historia_clinica.registrar_consulta(consulta)
    with pytest.raises(ReglaNegocio, match="ya está registrada"):
        perro.historia_clinica.registrar_consulta(consulta)
    assert len(perro.historia_clinica.consultas) == 1


def test_consultas_de_la_historia_no_se_modifican_desde_afuera(perro):
    with pytest.raises(AttributeError):
        perro.historia_clinica.consultas.append("x")  # es una tupla

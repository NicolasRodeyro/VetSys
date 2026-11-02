from datetime import date

from app.dominio.cliente import Cliente
from app.dominio.enums import Sexo
from app.dominio.especie import Especie, VacunaObligatoria
from app.dominio.mascota import Mascota

# Esquema de prueba para perros:
SEXTUPLE = VacunaObligatoria("Sextuple", edad_aplicacion_meses=2, refuerzo_cada_meses=12)
ANTIRRABICA = VacunaObligatoria("Antirrabica", edad_aplicacion_meses=3, refuerzo_cada_meses=12)
UNICA_DOSIS = VacunaObligatoria("Unica dosis", edad_aplicacion_meses=1)  # sin refuerzo
GIARDIA = VacunaObligatoria("Giardia", edad_aplicacion_meses=6, refuerzo_cada_meses=12)


def crear_perro(fecha_nacimiento: date) -> Mascota:
    especie = Especie("Perro")
    for vacuna in (SEXTUPLE, ANTIRRABICA, UNICA_DOSIS, GIARDIA):
        especie.agregar_vacuna_obligatoria(vacuna)
    cliente = Cliente("30111222", "Ana", "Paz", "351-555-0000", "ana@mail.com", "Calle 1")
    return Mascota("Toby", especie, Sexo.MACHO, fecha_nacimiento, cliente)


def test_cachorro_sin_vacunas_tiene_pendientes_las_que_le_corresponden_por_edad():
    perro = crear_perro(date(2026, 1, 10))

    # A los 4 meses: le corresponden Sextuple (2), Antirrabica (3) y Unica dosis (1),
    # pero todavía no Giardia (6).
    pendientes = perro.historia_clinica.vacunas_pendientes(date(2026, 5, 10))

    assert pendientes == [SEXTUPLE, ANTIRRABICA, UNICA_DOSIS]


def test_mascota_con_vacunas_al_dia_no_tiene_pendientes():
    perro = crear_perro(date(2026, 1, 10))
    historia = perro.historia_clinica
    historia.registrar_vacuna(UNICA_DOSIS, date(2026, 2, 10))
    historia.registrar_vacuna(SEXTUPLE, date(2026, 3, 10))
    historia.registrar_vacuna(ANTIRRABICA, date(2026, 4, 10))
    historia.registrar_vacuna(GIARDIA, date(2026, 7, 10))

    assert historia.vacunas_pendientes(date(2026, 10, 31)) == []


def test_refuerzo_vencido_vuelve_a_quedar_pendiente():
    perro = crear_perro(date(2024, 1, 10))
    historia = perro.historia_clinica
    historia.registrar_vacuna(UNICA_DOSIS, date(2024, 2, 10))
    historia.registrar_vacuna(SEXTUPLE, date(2025, 11, 1))  # refuerzo reciente
    historia.registrar_vacuna(ANTIRRABICA, date(2025, 1, 5))  # hace más de 12 meses
    historia.registrar_vacuna(GIARDIA, date(2025, 11, 1))

    pendientes = historia.vacunas_pendientes(date(2026, 10, 31))

    assert pendientes == [ANTIRRABICA]


def test_vacuna_sin_refuerzo_aplicada_una_vez_nunca_vence():
    perro = crear_perro(date(2020, 1, 10))
    historia = perro.historia_clinica
    historia.registrar_vacuna(UNICA_DOSIS, date(2020, 2, 10))

    assert UNICA_DOSIS not in historia.vacunas_pendientes(date(2026, 10, 31))


def test_se_toma_la_ultima_aplicacion_para_calcular_el_refuerzo():
    perro = crear_perro(date(2024, 1, 10))
    historia = perro.historia_clinica
    historia.registrar_vacuna(ANTIRRABICA, date(2024, 4, 10))  # vieja
    historia.registrar_vacuna(ANTIRRABICA, date(2026, 4, 10))  # refuerzo al día

    assert ANTIRRABICA not in historia.vacunas_pendientes(date(2026, 10, 31))


def test_vacuna_aplicada_despues_de_la_fecha_consultada_no_cuenta():
    perro = crear_perro(date(2026, 1, 10))
    historia = perro.historia_clinica
    historia.registrar_vacuna(ANTIRRABICA, date(2026, 6, 1))

    # Mirando la historia al 2026-05-10, esa aplicación todavía no ocurrió.
    assert ANTIRRABICA in historia.vacunas_pendientes(date(2026, 5, 10))

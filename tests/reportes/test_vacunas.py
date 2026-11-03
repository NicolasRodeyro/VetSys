"""Reporte de vacunas pendientes: el cálculo se prueba sin base; la lectura, con mascotas reales."""

from datetime import date, datetime

import pytest

from app.reportes import vacunas
from app.reportes.filtros import FiltroReporte
from app.reportes.vacunas import Pendiente, distribucion, ordenar
from app.servicios import catalogos, clientes, consultas
from tests.servicios.conftest import veterinario

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")

CORTE = date(2026, 11, 2)  # el reloj de los tests


def pendiente(mascota="Toby", vacuna="Sextuple", atraso=10):
    return Pendiente(mascota, "Perro", vacuna, date(2026, 1, 1), atraso, "Paz, Ana", "351 555-0101", "ana@mail.com")


# ---------------------------------------------------------------- cálculo (sin base)

def test_el_mayor_atraso_va_primero_y_a_igual_atraso_se_ordena_por_mascota_y_vacuna():
    ordenados = ordenar([pendiente("Toby", "Sextuple", 18), pendiente("Rex", "Antirrabica", 300),
                         pendiente("Nala", "Sextuple", 18), pendiente("Nala", "Antirrabica", 18)])
    assert [(p.mascota, p.vacuna) for p in ordenados] == [
        ("Rex", "Antirrabica"), ("Nala", "Antirrabica"), ("Nala", "Sextuple"), ("Toby", "Sextuple")]


@pytest.mark.parametrize("atraso, tramo", [(0, 0), (30, 0), (31, 1), (90, 1), (91, 2), (180, 2), (181, 3), (1819, 3)])
def test_los_tramos_de_atraso_incluyen_sus_dos_extremos(atraso, tramo):
    cantidades = distribucion([pendiente(atraso=atraso)])
    assert cantidades == [1 if i == tramo else 0 for i in range(4)]


def test_la_distribucion_suma_todas_las_vacunas():
    assert distribucion([pendiente(atraso=a) for a in (5, 40, 41, 100, 400, 500)]) == [1, 2, 1, 2]
    assert distribucion([]) == [0, 0, 0, 0]


# ---------------------------------------------------------------- con la base (mascotas reales)

@pytest.fixture
def fido():
    """Perro nacido el 01/03/2026 con la Sextuple aplicada el 01/04/2026. Al 02/11/2026 le faltan la Antirrabica
    (le tocaba al cumplir 3 meses: 01/06 -> 154 días) y la Tos de las perreras (a los 6 meses: 01/09 -> 62 días)."""
    cliente = clientes.alta_cliente("40111222", "Sofía", "Ramírez", "351 555-0000", "sofia@mail.com")
    mascota = clientes.alta_mascota(cliente.id, "Fido", "Perro", "MACHO", date(2026, 3, 1))
    clientes.aplicar_vacuna(mascota.id, "Sextuple", date(2026, 4, 1))
    return cliente, mascota


def de(resultado, nombre):
    return [f for f in resultado.filas if f[0] == nombre]


def test_calcula_el_vencimiento_y_los_dias_de_atraso_de_cada_vacuna(fido):
    r = vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE))

    assert r.columnas == ["Mascota", "Especie", "Vacuna", "Venció el", "Días de atraso", "Responsable", "Teléfono", "Email"]
    assert de(r, "Fido") == [
        ["Fido", "Perro", "Antirrabica", "01/06/2026", "154", "Ramírez, Sofía", "351 555-0000", "sofia@mail.com"],
        ["Fido", "Perro", "Tos de las perreras", "01/09/2026", "62", "Ramírez, Sofía", "351 555-0000", "sofia@mail.com"],
    ]  # la Sextuple no aparece: su refuerzo vence recién el 01/04/2027


def test_con_los_datos_de_prueba_hay_21_vacunas_pendientes_de_9_mascotas(con_seed):
    r = vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE))

    assert r.notas[0] == "Fecha de corte: 02/11/2026. 9 mascota(s) con 21 vacuna(s) pendiente(s)."
    assert len(r.filas) == 21
    atrasos = [int(f[4]) for f in r.filas]
    assert atrasos == sorted(atrasos, reverse=True)  # el más atrasado primero
    assert [(f[2], f[3], f[4]) for f in de(r, "Toby")] == [("Tos de las perreras", "12/02/2026", "263"), ("Sextuple", "15/10/2026", "18")]
    assert de(r, "Rex") == []  # vacunado en abril: al día


def test_la_fecha_de_corte_es_el_hasta_y_el_desde_no_se_usa(fido):
    # A mediados de junio solo había vencido la Antirrabica de Fido (14 días); la Tos recién venció en septiembre.
    r = vacunas.generar(FiltroReporte(date(2026, 1, 1), date(2026, 6, 15)))
    assert [(f[2], f[4]) for f in de(r, "Fido")] == [("Antirrabica", "14")]
    mismo = vacunas.generar(FiltroReporte(date(2026, 6, 15), date(2026, 6, 15)))
    assert mismo.filas == r.filas


def test_una_mascota_que_todavia_no_habia_nacido_en_el_corte_no_entra_ni_da_error(con_seed):
    r = vacunas.generar(FiltroReporte(date(2026, 1, 1), date(2026, 6, 30)))  # Luna nació el 01/07/2026
    assert de(r, "Luna") == []


def test_las_mascotas_y_clientes_de_baja_no_entran(fido):
    _, mascota = fido
    clientes.dar_de_baja_mascota(mascota.id)
    assert de(vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE)), "Fido") == []

    ana = clientes.buscar_clientes("Paz")[0]  # Toby y Mimi
    for m in ana.mascotas:
        clientes.dar_de_baja_mascota(m.id)
    clientes.dar_de_baja_cliente(ana.id)
    r = vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE))
    assert de(r, "Toby") == [] and de(r, "Mimi") == []


def test_con_una_clinica_solo_se_listan_las_mascotas_atendidas_en_ella(fido):
    _, mascota = fido
    consultas.registrar_consulta(mascota.id, veterinario("MP-1001").id, "CONTROL", fecha_hora=datetime(2026, 10, 1, 10, 0))
    centro = next(c.id for c in catalogos.listar_clinicas() if c.nombre == "Clínica Centro")
    norte = next(c.id for c in catalogos.listar_clinicas() if c.nombre == "Clínica Norte")

    en_centro = vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE, centro))
    assert [f[0] for f in en_centro.filas] == ["Fido", "Fido"]
    assert en_centro.grafico.series == {"Vacunas pendientes": [0.0, 1.0, 1.0, 0.0]}  # 62 días y 154 días

    en_norte = vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE, norte))
    assert en_norte.filas == [] and en_norte.grafico is None
    assert "Ninguna mascota tiene vacunas pendientes al 02/11/2026." in en_norte.notas


def test_una_consulta_posterior_al_corte_no_cuenta_como_atendida_en_la_clinica(fido):
    _, mascota = fido
    consultas.registrar_consulta(mascota.id, veterinario("MP-1001").id, "CONTROL", fecha_hora=datetime(2026, 10, 1, 10, 0))
    centro = next(c.id for c in catalogos.listar_clinicas() if c.nombre == "Clínica Centro")
    antes = vacunas.generar(FiltroReporte(date(2026, 1, 1), date(2026, 9, 15), centro))
    assert antes.filas == []  # al 15/09 todavía no la habían atendido


def test_el_grafico_agrupa_los_dias_de_atraso_en_tramos(con_seed):
    g = vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE)).grafico
    assert g.etiquetas == ["0 a 30 días", "31 a 90 días", "91 a 180 días", "Más de 180 días"]
    assert g.series == {"Vacunas pendientes": [1.0, 6.0, 2.0, 12.0]}  # suma 21


def test_una_mascota_sin_telefono_ni_email_muestra_guiones(con_seed):
    cliente = clientes.alta_cliente("40999888", "Sin", "Contacto")
    clientes.alta_mascota(cliente.id, "Anónimo", "Gato", "MACHO", date(2026, 1, 1))
    fila = de(vacunas.generar(FiltroReporte(date(2026, 9, 1), CORTE)), "Anónimo")[0]
    assert fila[-2:] == ["—", "—"]

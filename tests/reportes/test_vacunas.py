"""Reporte de vacunas pendientes: el orden se prueba sin base; la lectura, con el seed real.

La regla de qué vacuna está pendiente vive en el dominio (HistoriaClinica); acá se verifica que
el reporte la reúne bien por mascota, con los días de atraso y el contacto del responsable.
"""

from datetime import date

from app.reportes import vacunas
from app.reportes.filtros import FiltroReporte
from app.reportes.vacunas import VacunaPendiente

CORTE = date(2026, 11, 2)


def pendiente(mascota, especie, vacuna, vencimiento):
    return VacunaPendiente(mascota, especie, "Ana Paz", "351-555", vacuna, vencimiento)


# ---------------------------------------------------------------- cálculo (sin base)

def test_ordena_de_mayor_a_menor_atraso():
    datos = [
        pendiente("Mimi", "Gato", "Antirrabica", date(2026, 10, 1)),   # poco atraso
        pendiente("Toby", "Perro", "Sextuple", date(2026, 1, 1)),      # mucho atraso
    ]
    orden = vacunas.ordenar(datos, CORTE)
    assert [p.mascota for p in orden] == ["Toby", "Mimi"]
    assert orden[0].dias_de_atraso(CORTE) == 305


def test_cuenta_pendientes_por_especie():
    datos = [
        pendiente("Toby", "Perro", "Sextuple", date(2026, 1, 1)),
        pendiente("Kira", "Perro", "Antirrabica", date(2026, 2, 1)),
        pendiente("Mimi", "Gato", "Antirrabica", date(2026, 10, 1)),
    ]
    assert vacunas.pendientes_por_especie(datos) == {"Gato": 1, "Perro": 2}


# ---------------------------------------------------------------- con la base (seed real)

def test_lista_las_mascotas_con_vacunas_pendientes(con_seed):
    resultado = vacunas.generar(FiltroReporte(date(2026, 1, 1), CORTE))

    assert resultado.filas, "el seed tiene mascotas sin vacunar: debería haber pendientes"
    # Luna (gato nacido 2026-07-01, sin vacunas) debe tener Triple felina pendiente.
    luna = [f for f in resultado.filas if f[0] == "Luna"]
    assert luna and any(f[4] == "Triple felina" for f in luna)
    assert all(f[2] and f[3] for f in resultado.filas)  # responsable y contacto cargados

    # Vienen ordenadas de mayor a menor atraso.
    atrasos = [int(f[6].split()[0]) for f in resultado.filas]
    assert atrasos == sorted(atrasos, reverse=True)
    assert "Gato" in resultado.grafico.etiquetas


def test_avisa_que_la_clinica_no_aplica(con_seed):
    resultado = vacunas.generar(FiltroReporte(date(2026, 1, 1), CORTE, clinica_id=1))
    assert any("clínica no aplica" in nota for nota in resultado.notas)

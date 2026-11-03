"""Reporte de tiempos: la mediana/P90 y el cálculo se prueban sin base; la lectura, con muestras reales."""

from datetime import date

import pytest

from app.reportes import estadistica, tiempos
from app.reportes.filtros import FiltroReporte
from app.reportes.tiempos import TiempoMuestra, calcular

SEP = (date(2026, 9, 1), date(2026, 9, 30))


# ---------------------------------------------------------------- estadística (sin base)

def test_mediana_impar_y_par():
    assert estadistica.mediana([3, 1, 2]) == 2          # ordena: [1,2,3]
    assert estadistica.mediana([1, 2, 3, 4]) == 2.5     # promedio de los dos del medio


@pytest.mark.parametrize("valores, p, esperado", [
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90, 9.1),   # interpolación lineal, como PERCENTILE_CONT
    ([10], 90, 10),                                # un solo valor
    ([20, 40], 50, 30),                            # mediana por interpolación
])
def test_percentil_con_interpolacion(valores, p, esperado):
    assert estadistica.percentil(valores, p) == esperado


def test_sin_valores_no_hay_percentil():
    assert estadistica.percentil([], 90) is None and estadistica.mediana([]) is None


# ---------------------------------------------------------------- cálculo (sin base)

def test_agrupa_por_clinica_y_transportista_y_marca_fuera_de_tiempo():
    muestras = [
        TiempoMuestra(1, "Centro", "Sur", 24, 24.0, 12.0),
        TiempoMuestra(2, "Centro", "Sur", 24, 36.0, None),   # 36 h > 24 h: fuera de tiempo
        TiempoMuestra(3, "Norte", "Norte", 72, 12.0, 1.0),
    ]
    resumen = calcular(muestras)

    centro = resumen.por_clinica[0]
    assert (centro.nombre, centro.muestras, centro.transito_mediana, centro.fuera_de_tiempo) == ("Centro", 2, 30.0, 1)
    assert centro.transito_p90 == pytest.approx(34.8)
    assert centro.proceso_mediana == 12.0  # solo la muestra 1 tiene procesamiento medido
    assert [r.nombre for r in resumen.por_transportista] == ["Norte", "Sur"]
    assert resumen.total.muestras == 3 and resumen.total.fuera_de_tiempo == 1


def test_una_muestra_todavia_en_transito_no_cuenta_en_las_medidas():
    # Despachada pero sin recepción: no tiene tránsito medido, pero igual se la ve como muestra.
    muestras = [TiempoMuestra(1, "Centro", None, 24, None, None)]
    resumen = calcular(muestras)
    assert resumen.por_clinica[0].muestras == 0 and resumen.por_clinica[0].transito_mediana is None


# ---------------------------------------------------------------- con la base (muestras reales)

def test_lee_los_tiempos_del_historial_de_cada_muestra(circuito):
    circuito.insertar_muestra(clinica="Clínica Centro", analisis="Hemograma", transportista="Transporte Sur",
                              cambios=[("EN_TRANSITO", "2026-09-01 08:00"), ("RECIBIDA", "2026-09-02 08:00"),
                                       ("ANALIZADA", "2026-09-02 20:00")])  # tránsito 24 h, proceso 12 h
    circuito.insertar_muestra(clinica="Clínica Centro", analisis="Hemograma", transportista="Transporte Sur",
                              cambios=[("EN_TRANSITO", "2026-09-03 08:00"), ("RECIBIDA", "2026-09-04 20:00")])  # 36 h (fuera)
    circuito.insertar_muestra(clinica="Clínica Norte", analisis="Biopsia", transportista="Transporte Norte",
                              cambios=[("EN_TRANSITO", "2026-09-05 08:00"), ("RECHAZADA", "2026-09-05 20:00")])  # 12 h
    # Fuera del rango de fechas: no debe contar.
    circuito.insertar_muestra(clinica="Clínica Centro", analisis="Hemograma", transportista="Transporte Sur",
                              cambios=[("EN_TRANSITO", "2026-08-15 08:00"), ("RECIBIDA", "2026-08-16 08:00")])

    resultado = tiempos.generar(FiltroReporte(*SEP))

    assert resultado.filas[:2] == [
        ["Clínica", "Clínica Centro", "2", "30,0 h", "34,8 h", "12,0 h", "12,0 h", "1"],
        ["Clínica", "Clínica Norte", "1", "12,0 h", "12,0 h", "—", "—", "0"],
    ]
    assert ["Transportista", "Transporte Sur", "2", "30,0 h", "34,8 h", "—", "—", "1"] in resultado.filas
    assert resultado.filas[-1] == ["", "TOTAL", "3", "24,0 h", "33,6 h", "12,0 h", "12,0 h", "1"]
    assert resultado.grafico.etiquetas == ["Clínica Centro", "Clínica Norte"]


def test_un_periodo_sin_despachos_lo_avisa_y_no_tiene_grafico(circuito):
    resultado = tiempos.generar(FiltroReporte(date(2026, 1, 1), date(2026, 1, 31)))
    assert resultado.filas == []
    assert "No hay muestras despachadas en el período elegido." in resultado.notas
    assert resultado.grafico is None

"""Reporte de rechazo: el cálculo de tasas se prueba sin base; la lectura, con muestras reales."""

from datetime import date

from app.dominio.enums import MotivoRechazo
from app.reportes import rechazos
from app.reportes.filtros import FiltroReporte
from app.reportes.rechazos import RechazoMuestra, calcular

SEP = (date(2026, 9, 1), date(2026, 9, 30))
PRECINTO = MotivoRechazo.PRECINTO_ROTO.value
TEMP = MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO.value


# ---------------------------------------------------------------- cálculo (sin base)

def test_tasa_por_clinica_y_conteo_por_motivo():
    muestras = [
        RechazoMuestra(1, "Centro", rechazada=False, precinto_roto=False, temperatura_fuera=False),
        RechazoMuestra(2, "Centro", rechazada=True, precinto_roto=True, temperatura_fuera=False),
        RechazoMuestra(3, "Norte", rechazada=True, precinto_roto=True, temperatura_fuera=True),
    ]
    renglones, total = calcular(muestras)

    centro, norte = renglones
    assert (centro.despachadas, centro.rechazadas, centro.tasa) == (2, 1, 50)
    assert (norte.despachadas, norte.rechazadas, norte.tasa) == (1, 1, 100)
    assert (total.despachadas, total.rechazadas, total.precinto_roto, total.temperatura_fuera) == (3, 2, 2, 1)


def test_sin_despachos_la_tasa_es_none():
    _, total = calcular([])
    assert total.tasa is None


# ---------------------------------------------------------------- con la base (muestras reales)

def test_lee_las_muestras_despachadas_y_su_rechazo(circuito):
    circuito.insertar_muestra(clinica="Clínica Centro", analisis="Hemograma",
                              cambios=[("EN_TRANSITO", "2026-09-01 08:00"), ("RECIBIDA", "2026-09-02 08:00")])
    circuito.insertar_muestra(clinica="Clínica Centro", analisis="Hemograma", motivos=[PRECINTO],
                              cambios=[("EN_TRANSITO", "2026-09-03 08:00"), ("RECHAZADA", "2026-09-04 08:00")])
    circuito.insertar_muestra(clinica="Clínica Norte", analisis="Biopsia", motivos=[PRECINTO, TEMP],
                              cambios=[("EN_TRANSITO", "2026-09-05 08:00"), ("RECHAZADA", "2026-09-06 08:00")])
    # Fuera del rango: no cuenta.
    circuito.insertar_muestra(clinica="Clínica Centro", analisis="Hemograma", motivos=[PRECINTO],
                              cambios=[("EN_TRANSITO", "2026-08-10 08:00"), ("RECHAZADA", "2026-08-11 08:00")])

    resultado = rechazos.generar(FiltroReporte(*SEP))

    assert resultado.filas == [
        ["Clínica Centro", "2", "1", "50,0 %", "1", "0"],
        ["Clínica Norte", "1", "1", "100,0 %", "1", "1"],
        ["TOTAL", "3", "2", "66,7 %", "2", "1"],
    ]
    assert resultado.grafico.series == {"Tasa de rechazo": [50.0, 100.0]}


def test_un_periodo_sin_despachos_lo_avisa(circuito):
    resultado = rechazos.generar(FiltroReporte(date(2026, 1, 1), date(2026, 1, 31)))
    assert resultado.filas == []
    assert "No hay muestras despachadas en el período elegido." in resultado.notas
    assert resultado.grafico is None

from datetime import datetime

import pytest

from app.dominio.excepciones import ReglaNegocio
from app.dominio.tramo_envio import TramoEnvio

SALIDA = datetime(2026, 6, 1, 10, 0)


def test_tramo_en_curso_no_tiene_llegada_ni_temperatura():
    tramo = TramoEnvio(1, "Clínica Centro", "Laboratorio", "Transportes Sur", SALIDA)
    assert tramo.llegada is None
    assert tramo.temperatura is None


def test_tramo_completo():
    tramo = TramoEnvio(
        1, "Clínica Centro", "Laboratorio", "Transportes Sur",
        SALIDA, datetime(2026, 6, 1, 11, 30), 5.5,
    )
    assert tramo.temperatura == 5.5


def test_llegada_anterior_a_la_salida_falla():
    with pytest.raises(ReglaNegocio):
        TramoEnvio(1, "A", "B", "T", SALIDA, datetime(2026, 6, 1, 9, 0))

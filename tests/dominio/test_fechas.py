from datetime import date, timedelta

import pytest

from app.dominio.fechas import meses_entre, sumar_meses


@pytest.mark.parametrize(
    "fecha, meses, esperada",
    [
        (date(2026, 1, 15), 1, date(2026, 2, 15)),
        (date(2026, 1, 15), 0, date(2026, 1, 15)),
        (date(2025, 11, 20), 3, date(2026, 2, 20)),  # cambia de año
        (date(2025, 1, 5), 12, date(2026, 1, 5)),
        (date(2026, 1, 31), 1, date(2026, 3, 1)),  # no hay 31/02: el mes se completa el 01/03
        (date(2024, 1, 31), 1, date(2024, 3, 1)),  # año bisiesto: 29/02 tampoco alcanza
        (date(2024, 2, 29), 12, date(2025, 3, 1)),  # 29/02 + 1 año
        (date(2026, 3, 31), 1, date(2026, 5, 1)),
    ],
)
def test_sumar_meses(fecha, meses, esperada):
    assert sumar_meses(fecha, meses) == esperada


def test_sumar_meses_es_la_inversa_de_meses_entre():
    """Para cada día de 2024 (bisiesto) y de 2025: sumar n meses da justo el primer día en
    que meses_entre llega a n. Si no, el atraso de una vacuna no coincidiría con su pendiente."""
    dia = date(2024, 1, 1)
    while dia < date(2026, 1, 1):
        for meses in (1, 2, 3, 6, 12):
            vence = sumar_meses(dia, meses)
            assert meses_entre(dia, vence) == meses
            assert meses_entre(dia, vence - timedelta(days=1)) == meses - 1
        dia += timedelta(days=1)
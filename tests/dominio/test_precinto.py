from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from app.dominio.enums import EstadoPrecinto
from app.dominio.precinto import Precinto


def test_precinto_guarda_sus_datos():
    precinto = Precinto("P-0001", datetime(2026, 6, 1, 9, 0), "Enf. Ruiz")
    assert precinto.numero == "P-0001"
    assert precinto.responsable == "Enf. Ruiz"


def test_precinto_es_inmutable():
    precinto = Precinto("P-0001", datetime(2026, 6, 1, 9, 0), "Enf. Ruiz")
    with pytest.raises(FrozenInstanceError):
        precinto.numero = "P-9999"


def test_estados_posibles_del_precinto_al_llegar():
    assert {estado.value for estado in EstadoPrecinto} == {"INTACTO", "ROTO"}

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from app.dominio.cambio_estado import CambioEstado
from app.dominio.enums import MotivoRechazo


def un_cambio() -> CambioEstado:
    return CambioEstado("EN_TRANSITO", "RECHAZADA", datetime(2026, 6, 1, 10, 0), "Bioq. Pérez")


def test_cambio_de_estado_es_inmutable():
    cambio = un_cambio()
    with pytest.raises(FrozenInstanceError):
        cambio.nuevo = "RECIBIDA"
    with pytest.raises(FrozenInstanceError):
        cambio.responsable = "otro"


def test_cambio_de_estado_tiene_valores_por_defecto():
    cambio = un_cambio()
    assert cambio.ubicacion == ""
    assert cambio.observacion == ""
    assert cambio.motivos == ()


def test_motivos_de_rechazo_quedan_en_el_cambio():
    cambio = CambioEstado(
        "EN_TRANSITO", "RECHAZADA", datetime(2026, 6, 1, 10, 0), "Bioq. Pérez",
        motivos=(MotivoRechazo.PRECINTO_ROTO, MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO),
    )
    assert MotivoRechazo.PRECINTO_ROTO in cambio.motivos
    assert len(cambio.motivos) == 2

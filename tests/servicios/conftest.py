"""Fixtures de los tests de servicios: reloj fijo y atajos para encontrar los datos del seed."""

from datetime import datetime

import pytest

from app.servicios import catalogos, clientes, tiempo

AHORA = datetime(2026, 11, 2, 12, 0, 0)


@pytest.fixture
def ahora(monkeypatch) -> datetime:
    """Congela el reloj del sistema en el 02/11/2026 12:00."""
    monkeypatch.setattr(tiempo, "ahora", lambda: AHORA)
    return AHORA


# --- Atajos para encontrar los datos del seed por su nombre ---

def mascota(dni: str, nombre: str):
    cliente = clientes.buscar_clientes(dni, incluir_inactivos=True)[0]
    return next(m for m in cliente.mascotas if m.nombre == nombre)


def veterinario(matricula: str):
    return next(v for v in catalogos.listar_veterinarios() if v.matricula == matricula)

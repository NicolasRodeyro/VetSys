"""Fixtures compartidas por los tests del dominio."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.conservadora import Conservadora
from app.dominio.enums import Sexo
from app.dominio.especie import Especie, VacunaObligatoria
from app.dominio.laboratorio import Laboratorio
from app.dominio.mascota import Mascota
from app.dominio.muestra import Muestra
from app.dominio.orden_derivacion import OrdenDerivacion
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.veterinario import Veterinario

SEXTUPLE = VacunaObligatoria("Sextuple", edad_aplicacion_meses=2, refuerzo_cada_meses=12)
ANTIRRABICA = VacunaObligatoria("Antirrabica", edad_aplicacion_meses=3, refuerzo_cada_meses=12)


@pytest.fixture
def clinica() -> Clinica:
    return Clinica("Clínica Centro", "Av. Colón 100")


@pytest.fixture
def veterinario(clinica) -> Veterinario:
    return Veterinario("MP-1234", "Laura", "Gómez", clinica)


@pytest.fixture
def cliente() -> Cliente:
    return Cliente("30111222", "Ana", "Paz", "351-555-0000", "ana@mail.com", "Calle 1")


@pytest.fixture
def perro(cliente) -> Mascota:
    """Perro nacido el 10/01/2026, con esquema de dos vacunas."""
    especie = Especie("Perro")
    especie.agregar_vacuna_obligatoria(SEXTUPLE)
    especie.agregar_vacuna_obligatoria(ANTIRRABICA)
    return Mascota("Toby", especie, Sexo.MACHO, date(2026, 1, 10), cliente)


class RelojFalso:
    """Reloj para los tests: cada vez que se lo consulta avanza media hora."""

    def __init__(self) -> None:
        self._actual = datetime(2026, 6, 1, 9, 0)

    def __call__(self) -> datetime:
        valor = self._actual
        self._actual += timedelta(minutes=30)
        return valor


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def hemograma() -> TipoAnalisis:
    return TipoAnalisis("Hemograma", Decimal("12500"), "Sangre", 2.0, 8.0, 24)


@pytest.fixture
def orden(hemograma) -> OrdenDerivacion:
    return OrdenDerivacion(hemograma)


@pytest.fixture
def crear_muestra(hemograma, reloj):
    """Fábrica: cada muestra nace con su propia orden (una activa por orden)."""

    def _crear(tipo_analisis=hemograma) -> Muestra:
        return Muestra(OrdenDerivacion(tipo_analisis), "Dr. Gómez", "Clínica Centro", reloj=reloj)

    return _crear


@pytest.fixture
def crear_conservadora():
    def _crear(codigo="C-1", capacidad=5, temp_min=4.0, temp_max=6.0) -> Conservadora:
        return Conservadora(codigo, capacidad, temp_min, temp_max)

    return _crear


@pytest.fixture
def laboratorio() -> Laboratorio:
    return Laboratorio("Laboratorio Central", "Bv. Illia 1")

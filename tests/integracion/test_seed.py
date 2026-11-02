import pytest

from app.persistencia import datos_de_prueba


@pytest.fixture
def sembrar(base):
    return datos_de_prueba.cargar


def contar(cx, tabla: str) -> int:
    return cx.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def test_el_seed_carga_lo_que_pide_el_plan(sembrar, cx):
    sembrar()
    assert contar(cx, "clinicas") == 2
    assert contar(cx, "laboratorios") == 1
    assert contar(cx, "veterinarios") == 4
    assert contar(cx, "tipos_analisis") == 5
    assert contar(cx, "clientes") == 10
    assert contar(cx, "mascotas") >= 10


def test_cada_clinica_tiene_veterinarios(sembrar, cx):
    sembrar()
    filas = cx.execute("SELECT clinica_id, COUNT(*) n FROM veterinarios GROUP BY clinica_id").fetchall()
    assert len(filas) == 2 and all(f["n"] == 2 for f in filas)


def test_cada_especie_tiene_su_esquema_de_vacunas(sembrar, cx):
    sembrar()
    sin_esquema = cx.execute(
        "SELECT e.nombre FROM especies e LEFT JOIN vacunas_obligatorias v ON v.especie_id = e.id "
        "WHERE v.id IS NULL").fetchall()
    assert sin_esquema == []


def test_toda_mascota_tiene_responsable_e_historia_clinica(sembrar, cx):
    sembrar()
    assert cx.execute("SELECT COUNT(*) FROM mascotas WHERE cliente_id IS NULL").fetchone()[0] == 0
    sin_historia = cx.execute(
        "SELECT COUNT(*) FROM mascotas m LEFT JOIN historias_clinicas h ON h.mascota_id = m.id "
        "WHERE h.id IS NULL").fetchone()[0]
    assert sin_historia == 0


def test_sembrar_dos_veces_no_duplica_los_datos(sembrar, cx):
    sembrar()
    sembrar()
    assert contar(cx, "clientes") == 10
    assert contar(cx, "clinicas") == 2


def test_cargar_informa_si_cargo_o_si_ya_habia_datos(base):
    assert datos_de_prueba.base_vacia()
    assert datos_de_prueba.cargar() is True
    assert not datos_de_prueba.base_vacia()
    assert datos_de_prueba.cargar() is False  # no duplica

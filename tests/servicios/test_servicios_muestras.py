import pytest

from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.servicios import muestras
from app.servicios.excepciones import EntradaInvalida, NoEncontrado
from tests.servicios.ayudas_circuito import muestra_empaquetada, nueva_orden

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


# --- Extracción ---

def test_registrar_extraccion_deja_la_muestra_extraida_con_su_primer_renglon_de_trazabilidad(cx):
    consulta, orden = nueva_orden()
    muestra = muestras.registrar_extraccion(orden.id, "  Dr.  Gómez ", "Clínica Centro", "En ayunas")

    assert muestra.id is not None and muestra.estado.nombre == "EXTRAIDA"
    (extraccion,) = muestras.trazabilidad_de_muestra(muestra.id)
    assert (extraccion.anterior, extraccion.nuevo, extraccion.responsable) == (None, "EXTRAIDA", "Dr. Gómez")
    assert (extraccion.ubicacion, extraccion.observacion) == ("Clínica Centro", "En ayunas")


def test_una_orden_no_admite_dos_muestras_activas(cx):
    _, orden = nueva_orden()
    muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    with pytest.raises(ReglaNegocio, match="muestra activa"):
        muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    assert cx.execute("SELECT COUNT(*) FROM muestras").fetchone()[0] == 1


def test_extraccion_con_datos_invalidos(cx):
    _, orden = nueva_orden()
    with pytest.raises(EntradaInvalida, match="responsable es obligatorio"):
        muestras.registrar_extraccion(orden.id, "  ")
    with pytest.raises(NoEncontrado, match="la orden de derivación"):
        muestras.registrar_extraccion(9999, "Dr. Gómez")
    assert cx.execute("SELECT COUNT(*) FROM muestras").fetchone()[0] == 0


def test_listar_muestras_por_estado(cx):
    _, orden = nueva_orden()
    muestra = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    assert [m.id for m in muestras.listar_muestras("extraida")] == [muestra.id]
    assert [m.id for m in muestras.listar_muestras()] == [muestra.id]  # sin filtro: las que están en curso
    assert muestras.listar_muestras("ANALIZADA") == []


# --- Conservadoras ---

def test_crear_conservadora(cx):
    conservadora = muestras.crear_conservadora(" C-1 ", "5", "4,5", "6")
    assert (conservadora.codigo, conservadora.capacidad, conservadora.temp_min, conservadora.temp_max) == ("C-1", 5, 4.5, 6.0)
    assert muestras.obtener_conservadora(conservadora.id).codigo == "C-1"


@pytest.mark.parametrize("datos, error, mensaje", [
    (dict(codigo="C-1", capacidad=0, temp_min=2, temp_max=8), EntradaInvalida, "capacidad"),
    (dict(codigo="C-1", capacidad=5, temp_min="frío", temp_max=8), EntradaInvalida, "temperatura mínima"),
    (dict(codigo="", capacidad=5, temp_min=2, temp_max=8), EntradaInvalida, "código"),
    (dict(codigo="C-1", capacidad=5, temp_min=8, temp_max=2), ReglaNegocio, "no puede superar"),
])
def test_crear_conservadora_con_datos_invalidos(cx, datos, error, mensaje):
    with pytest.raises(error, match=mensaje):
        muestras.crear_conservadora(**datos)
    assert cx.execute("SELECT COUNT(*) FROM conservadoras").fetchone()[0] == 0


def test_no_se_repite_el_codigo_de_una_conservadora(cx):
    muestras.crear_conservadora("C-1", 5, 2, 8)
    with pytest.raises(ReglaNegocio, match="Ya existe una conservadora"):
        muestras.crear_conservadora("C-1", 3, 2, 8)


# --- Empaquetado y precinto ---

def test_empaquetar_pasa_la_muestra_a_empaquetada_y_queda_en_la_conservadora(cx):
    conservadora = muestras.crear_conservadora("C-1", 5, 4, 6)
    _, _, muestra = muestra_empaquetada(conservadora)

    guardada = muestras.obtener_muestra(muestra.id)
    assert guardada.estado.nombre == "EMPAQUETADA"
    assert [m.id for m in muestras.obtener_conservadora(conservadora.id).muestras] == [muestra.id]
    empaquetado = muestras.trazabilidad_de_muestra(muestra.id)[-1]
    assert (empaquetado.nuevo, empaquetado.responsable) == ("EMPAQUETADA", "Enf. Ruiz")
    assert "C-1" in empaquetado.observacion  # la trazabilidad dice en qué conservadora


def test_una_conservadora_lleva_muestras_de_distintas_ordenes(cx):
    conservadora = muestras.crear_conservadora("C-1", 5, 4, 6)
    for _ in range(3):
        muestra_empaquetada(conservadora)
    assert len(muestras.obtener_conservadora(conservadora.id).muestras) == 3


def test_empaquetar_en_una_conservadora_de_temperatura_incompatible_no_cambia_nada(cx):
    _, orden = nueva_orden()  # el hemograma pide 2 a 8 °C
    muestra = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    caliente = muestras.crear_conservadora("C-CALIENTE", 5, 4, 12)

    with pytest.raises(ReglaNegocio, match="no es compatible"):
        muestras.empaquetar_muestra(muestra.id, caliente.id, "Enf. Ruiz")

    assert muestras.obtener_muestra(muestra.id).estado.nombre == "EXTRAIDA"
    assert muestras.obtener_conservadora(caliente.id).muestras == ()


def test_empaquetar_respeta_la_capacidad(cx):
    chica = muestras.crear_conservadora("C-CHICA", 1, 4, 6)
    muestra_empaquetada(chica)
    _, orden = nueva_orden("28444555", "Rex")
    sobrante = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    with pytest.raises(ReglaNegocio, match="llena"):
        muestras.empaquetar_muestra(sobrante.id, chica.id, "Enf. Ruiz")
    assert muestras.obtener_muestra(sobrante.id).estado.nombre == "EXTRAIDA"


def test_una_muestra_ya_empaquetada_no_se_empaqueta_de_nuevo(cx):
    una, otra = muestras.crear_conservadora("C-1", 5, 4, 6), muestras.crear_conservadora("C-2", 5, 4, 6)
    _, _, muestra = muestra_empaquetada(una)
    with pytest.raises(TransicionInvalida):
        muestras.empaquetar_muestra(muestra.id, otra.id, "Enf. Ruiz")
    assert muestras.obtener_conservadora(otra.id).muestras == ()


def test_precintar_la_conservadora(cx):
    conservadora = muestras.crear_conservadora("C-1", 5, 4, 6)
    muestra_empaquetada(conservadora)

    precintada = muestras.precintar_conservadora(conservadora.id, " P-0001 ", "Enf. Ruiz")

    assert precintada.precinto.numero == "P-0001"
    guardada = muestras.obtener_conservadora(conservadora.id)
    assert (guardada.precinto.numero, guardada.precinto.responsable) == ("P-0001", "Enf. Ruiz")


def test_una_conservadora_precintada_no_acepta_mas_muestras_ni_otro_precinto(cx):
    conservadora = muestras.crear_conservadora("C-1", 5, 4, 6)
    muestra_empaquetada(conservadora)
    muestras.precintar_conservadora(conservadora.id, "P-1", "Enf. Ruiz")

    _, orden = nueva_orden("28444555", "Rex")
    tardia = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    with pytest.raises(ReglaNegocio, match="precintada"):
        muestras.empaquetar_muestra(tardia.id, conservadora.id, "Enf. Ruiz")
    with pytest.raises(ReglaNegocio, match="ya tiene precinto"):
        muestras.precintar_conservadora(conservadora.id, "P-2", "Enf. Ruiz")


def test_no_se_precinta_una_conservadora_vacia(cx):
    vacia = muestras.crear_conservadora("C-1", 5, 4, 6)
    with pytest.raises(ReglaNegocio, match="vacía"):
        muestras.precintar_conservadora(vacia.id, "P-1", "Enf. Ruiz")
    assert muestras.obtener_conservadora(vacia.id).precinto is None


def test_obtener_lo_que_no_existe(cx):
    with pytest.raises(NoEncontrado, match="la muestra"):
        muestras.obtener_muestra(9999)
    with pytest.raises(NoEncontrado, match="la conservadora"):
        muestras.obtener_conservadora(9999)

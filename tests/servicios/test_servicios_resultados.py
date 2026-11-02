from decimal import Decimal

import pytest

from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.dominio.resultado_analisis import ValorResultado
from app.servicios import consultas, muestras, remitos, resultados
from app.servicios.excepciones import EntradaInvalida, NoEncontrado
from app.servicios.remitos import DetalleDeRecepcion
from tests.servicios.ayudas_circuito import conservadora_precintada, nueva_orden, remito_con

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")

HEMATOCRITO = ValorResultado("Hematocrito", 41.0, "%", 37.0, 55.0)
LEUCOCITOS = ValorResultado("Leucocitos", 25.0, "mil/µl", 6.0, 17.0)


def recibir(precinto="INTACTO"):
    """Una muestra de la consulta de Toby recibida (o rechazada) en el laboratorio.
    Devuelve (consulta, orden, muestra)."""
    conservadora, creadas = conservadora_precintada("C-1")
    remito = remito_con(conservadora)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [DetalleDeRecepcion(conservadora.id, precinto, 5.0)])
    return creadas[0]


# --- Registrar el resultado ---

def test_registrar_el_resultado_pasa_la_muestra_a_analizada_y_avisa_al_responsable(cx):
    _, _, muestra = recibir()

    registrado = resultados.registrar_resultado(
        muestra.id, "Bioq. Pérez", [HEMATOCRITO, LEUCOCITOS], "Leucocitosis")

    assert registrado.avisos == ("Ana Paz: ya está el resultado de Hemograma",)
    assert muestras.obtener_muestra(muestra.id).estado.nombre == "ANALIZADA"
    guardado = resultados.obtener_resultado(muestra.id)
    assert guardado.valores == (HEMATOCRITO, LEUCOCITOS)
    assert guardado.valores_fuera_de_rango() == (LEUCOCITOS,)
    assert (guardado.responsable, guardado.observaciones) == ("Bioq. Pérez", "Leucocitosis")
    ultimo = muestras.trazabilidad_de_muestra(muestra.id)[-1]
    assert (ultimo.anterior, ultimo.nuevo, ultimo.responsable) == ("RECIBIDA", "ANALIZADA", "Bioq. Pérez")


def test_no_se_puede_registrar_el_resultado_de_una_muestra_que_no_fue_recibida(cx):
    _, orden = nueva_orden()
    extraida = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    with pytest.raises(TransicionInvalida, match="EXTRAIDA"):
        resultados.registrar_resultado(extraida.id, "Bioq. Pérez", [HEMATOCRITO])
    assert muestras.obtener_muestra(extraida.id).estado.nombre == "EXTRAIDA"

    _, _, rechazada = recibir(precinto="ROTO")
    with pytest.raises(TransicionInvalida, match="RECHAZADA"):
        resultados.registrar_resultado(rechazada.id, "Bioq. Pérez", [HEMATOCRITO])


def test_una_muestra_tiene_un_solo_resultado(cx):
    _, _, muestra = recibir()
    resultados.registrar_resultado(muestra.id, "Bioq. Pérez", [HEMATOCRITO])
    with pytest.raises(TransicionInvalida, match="ANALIZADA"):
        resultados.registrar_resultado(muestra.id, "Bioq. Pérez", [LEUCOCITOS])
    assert cx.execute("SELECT COUNT(*) FROM resultados_analisis").fetchone()[0] == 1


def test_un_resultado_sin_valores_o_con_datos_invalidos_no_toca_la_muestra(cx):
    _, _, muestra = recibir()
    with pytest.raises(ReglaNegocio, match="al menos un valor"):
        resultados.registrar_resultado(muestra.id, "Bioq. Pérez", [])
    with pytest.raises(EntradaInvalida, match="responsable es obligatorio"):
        resultados.registrar_resultado(muestra.id, " ", [HEMATOCRITO])
    assert muestras.obtener_muestra(muestra.id).estado.nombre == "RECIBIDA"


def test_obtener_el_resultado_de_una_muestra_sin_resultado(cx):
    _, _, muestra = recibir()
    with pytest.raises(NoEncontrado, match="todavía no tiene resultado"):
        resultados.obtener_resultado(muestra.id)
    with pytest.raises(NoEncontrado, match="la muestra"):
        resultados.registrar_resultado(9999, "Bioq. Pérez", [HEMATOCRITO])


# --- Re-extracción de una muestra rechazada ---

def test_re_extraccion_de_una_muestra_rechazada_en_la_misma_orden(cx):
    consulta, orden, rechazada = recibir(precinto="ROTO")
    assert muestras.obtener_muestra(rechazada.id).estado.nombre == "RECHAZADA"

    nueva = muestras.registrar_reextraccion(rechazada.id, "Dr. Gómez", "Clínica Centro")

    assert nueva.id != rechazada.id and nueva.estado.nombre == "EXTRAIDA"
    assert nueva.orden.id == orden.id  # misma orden: no es un pedido nuevo
    assert f"Re-extracción de la muestra {rechazada.id}" in muestras.trazabilidad_de_muestra(nueva.id)[0].observacion
    guardada = consultas.obtener_consulta(consulta.id).ordenes[0]
    assert [m.estado.nombre for m in guardada.muestras] == ["RECHAZADA", "EXTRAIDA"]
    assert guardada.muestra_activa().id == nueva.id


def test_la_re_extraccion_no_cambia_lo_que_se_cobra(cx):
    consulta, _, rechazada = recibir(precinto="ROTO")
    comprobante = consultas.cerrar_consulta(consulta.id, "3000")
    muestras.registrar_reextraccion(rechazada.id, "Dr. Gómez")

    guardado = consultas.obtener_consulta(consulta.id).comprobante
    assert [i.descripcion for i in guardado.items] == ["Consulta", "Hemograma"]  # un solo análisis
    assert guardado.total == comprobante.total == Decimal("15500.00")


def test_solo_se_re_extrae_una_muestra_rechazada(cx):
    _, _, recibida = recibir()
    with pytest.raises(ReglaNegocio, match="Solo se puede re-extraer una muestra que fue rechazada"):
        muestras.registrar_reextraccion(recibida.id, "Dr. Gómez")



def test_no_se_re_extrae_dos_veces_la_misma_muestra_rechazada(cx):
    _, _, rechazada = recibir(precinto="ROTO")
    muestras.registrar_reextraccion(rechazada.id, "Dr. Gómez")
    with pytest.raises(ReglaNegocio, match="muestra activa"):
        muestras.registrar_reextraccion(rechazada.id, "Dr. Gómez")
    assert cx.execute("SELECT COUNT(*) FROM muestras").fetchone()[0] == 2


def test_la_muestra_re_extraida_sigue_el_circuito_completo_hasta_el_resultado(cx):
    _, _, rechazada = recibir(precinto="ROTO")
    nueva = muestras.registrar_reextraccion(rechazada.id, "Dr. Gómez", "Clínica Centro")

    segunda = muestras.crear_conservadora("C-2", 5, 4, 6)
    muestras.empaquetar_muestra(nueva.id, segunda.id, "Enf. Ruiz", "Clínica Centro")
    muestras.precintar_conservadora(segunda.id, "P-2", "Enf. Ruiz")
    remito = remito_con(segunda)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [DetalleDeRecepcion(segunda.id, "INTACTO", 5.0)])
    resultados.registrar_resultado(nueva.id, "Bioq. Pérez", [HEMATOCRITO])

    assert muestras.obtener_muestra(nueva.id).estado.nombre == "ANALIZADA"
    assert muestras.obtener_muestra(rechazada.id).estado.nombre == "RECHAZADA"  # la primera no se tocó
    assert [c.nuevo for c in muestras.trazabilidad_de_muestra(nueva.id)] == [
        "EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA", "ANALIZADA"]


# --- Valores tal como los carga el usuario ---

def test_los_valores_ingresados_como_texto_se_sanitizan_y_convierten(cx):
    from app.servicios.resultados import ValorIngresado

    _, _, muestra = recibir()
    resultados.registrar_resultado(muestra.id, "Bioq. Pérez", [
        ValorIngresado(" Hematocrito ", "41,5", "%", "37", "55,0"),
        ValorIngresado("Urea", "40", "mg/dl", "", None)])  # sin referencias: no se puede estar fuera de rango

    guardado = resultados.obtener_resultado(muestra.id)
    assert guardado.valores == (ValorResultado("Hematocrito", 41.5, "%", 37.0, 55.0),
                                ValorResultado("Urea", 40.0, "mg/dl", None, None))


@pytest.mark.parametrize("valor, mensaje", [
    (dict(parametro="", valor="1", unidad="%"), "parámetro es obligatorio"),
    (dict(parametro="X", valor="alto", unidad="%"), "valor no es un número"),
    (dict(parametro="X", valor="1", unidad=""), "unidad es obligatorio"),
    (dict(parametro="X", valor="1", unidad="%", ref_min="mucho"), "mínimo de referencia"),
])
def test_un_valor_ingresado_invalido_se_rechaza_y_no_toca_la_muestra(cx, valor, mensaje):
    from app.servicios.resultados import ValorIngresado

    _, _, muestra = recibir()
    with pytest.raises(EntradaInvalida, match=mensaje):
        resultados.registrar_resultado(muestra.id, "Bioq. Pérez", [ValorIngresado(**valor)])
    assert muestras.obtener_muestra(muestra.id).estado.nombre == "RECIBIDA"

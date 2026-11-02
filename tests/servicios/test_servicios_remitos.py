from datetime import datetime

import pytest

from app.dominio.enums import MotivoRechazo
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.persistencia.repositorios_envio import RepositorioRemitos
from app.servicios import catalogos, muestras, remitos
from app.servicios.excepciones import EntradaInvalida, NoEncontrado
from app.servicios.remitos import DetalleDeRecepcion
from tests.servicios.ayudas_circuito import (
    conservadora_precintada, estados, muestra_empaquetada, remito_con,
)

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


def detalle(conservadora, precinto="INTACTO", temperatura=5.0, observacion=""):
    return DetalleDeRecepcion(conservadora.id, precinto, temperatura, observacion)


# --- Crear el remito y armarlo ---

def test_los_remitos_se_numeran_solos(cx):
    primero = remitos.crear_remito(catalogos.listar_clinicas()[0].id, catalogos.listar_laboratorios()[0].id)
    segundo = remitos.crear_remito(catalogos.listar_clinicas()[0].id, catalogos.listar_laboratorios()[0].id)
    assert (primero.numero, segundo.numero) == ("R-00001", "R-00002")
    assert primero.estado.nombre == "ABIERTO"
    assert [r.numero for r in remitos.listar_remitos()] == ["R-00002", "R-00001"]


def test_no_se_repite_el_numero_de_un_remito(cx):
    clinica, laboratorio = catalogos.listar_clinicas()[0], catalogos.listar_laboratorios()[0]
    remitos.crear_remito(clinica.id, laboratorio.id, numero="R-ESPECIAL")
    with pytest.raises(ReglaNegocio, match="Ya existe el remito R-ESPECIAL"):
        remitos.crear_remito(clinica.id, laboratorio.id, numero="R-ESPECIAL")


def test_crear_un_remito_con_ids_que_no_existen(cx):
    with pytest.raises(NoEncontrado, match="la clínica"):
        remitos.crear_remito(9999, catalogos.listar_laboratorios()[0].id)
    with pytest.raises(NoEncontrado, match="el laboratorio"):
        remitos.crear_remito(catalogos.listar_clinicas()[0].id, 9999)


def test_agregar_y_quitar_conservadoras_sin_desempaquetar_sus_muestras(cx):
    a, _ = conservadora_precintada("C-A")
    b, _ = conservadora_precintada("C-B")
    remito = remito_con(a, b)
    assert [c.codigo for c in remitos.obtener_remito(remito.id).conservadoras] == ["C-A", "C-B"]

    remitos.quitar_conservadora_de_remito(remito.id, b.id)

    assert [c.codigo for c in remitos.obtener_remito(remito.id).conservadoras] == ["C-A"]
    assert [c.codigo for c in muestras.listar_conservadoras(solo_sin_remito=True)] == ["C-B"]
    assert [m.estado.nombre for m in muestras.obtener_conservadora(b.id).muestras] == ["EMPAQUETADA"]


def test_una_conservadora_no_puede_viajar_en_dos_remitos(cx):
    a, _ = conservadora_precintada("C-A")
    remito_con(a)
    otro = remitos.crear_remito(catalogos.listar_clinicas()[0].id, catalogos.listar_laboratorios()[0].id)
    with pytest.raises(ReglaNegocio, match="ya viaja en otro remito"):
        remitos.agregar_conservadora_a_remito(otro.id, a.id)
    assert remitos.obtener_remito(otro.id).conservadoras == ()


def test_no_se_agrega_dos_veces_la_misma_conservadora(cx):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con(a)
    with pytest.raises(ReglaNegocio, match="ya está en el remito"):
        remitos.agregar_conservadora_a_remito(remito.id, a.id)


# --- Cerrar y despachar ---

def test_no_se_cierra_un_remito_vacio_ni_con_una_conservadora_sin_precinto(cx):
    vacio = remito_con()
    with pytest.raises(ReglaNegocio, match="al menos una conservadora"):
        remitos.cerrar_remito(vacio.id)

    sin_precinto = muestras.crear_conservadora("C-SIN", 5, 4, 6)
    muestra_empaquetada(sin_precinto)
    remito = remito_con(sin_precinto)
    with pytest.raises(ReglaNegocio, match="precinto.*C-SIN"):
        remitos.cerrar_remito(remito.id)
    assert remitos.obtener_remito(remito.id).estado.nombre == "ABIERTO"


def test_un_remito_cerrado_no_admite_cambios_en_sus_conservadoras(cx):
    a, _ = conservadora_precintada("C-A")
    b, _ = conservadora_precintada("C-B")
    remito = remito_con(a)
    remitos.cerrar_remito(remito.id)
    assert remitos.obtener_remito(remito.id).estado.nombre == "CERRADO"
    with pytest.raises(TransicionInvalida, match="CERRADO"):
        remitos.agregar_conservadora_a_remito(remito.id, b.id)
    with pytest.raises(TransicionInvalida):
        remitos.quitar_conservadora_de_remito(remito.id, a.id)


def test_despachar_pasa_el_remito_y_todas_sus_muestras_a_en_transito(cx):
    a, creadas_a = conservadora_precintada("C-A", cantidad=2)
    b, _ = conservadora_precintada("C-B")
    remito = remito_con(a, b)
    remitos.cerrar_remito(remito.id)

    remitos.despachar_remito(remito.id, "Transportes Sur", "Clínica Centro")

    assert remitos.obtener_remito(remito.id).estado.nombre == "EN_TRANSITO"
    assert estados(remito.id) == ["EN_TRANSITO"] * 3
    despacho = muestras.trazabilidad_de_muestra(creadas_a[0][2].id)[-1]  # quedó en la trazabilidad
    assert (despacho.anterior, despacho.nuevo, despacho.responsable) == ("EMPAQUETADA", "EN_TRANSITO", "Transportes Sur")
    assert remito.numero in despacho.observacion


def test_no_se_despacha_un_remito_abierto(cx):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con(a)
    with pytest.raises(TransicionInvalida, match="ABIERTO"):
        remitos.despachar_remito(remito.id, "Transportes Sur")
    assert estados(remito.id) == ["EMPAQUETADA"]


# --- Cadena de envío ---

def test_registrar_los_tramos_de_la_cadena_de_envio(cx):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con(a)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")

    remitos.registrar_tramo(remito.id, "Clínica Centro", "Centro de distribución", "Transportes Sur",
                            datetime(2026, 11, 2, 12, 30), datetime(2026, 11, 2, 13, 30), "5,5")
    remitos.registrar_tramo(remito.id, "Centro de distribución", "Laboratorio", "Logística Norte",
                            datetime(2026, 11, 2, 14, 0))

    tramos = remitos.obtener_remito(remito.id).tramos
    assert [(t.orden, t.transportista, t.temperatura) for t in tramos] == [
        (1, "Transportes Sur", 5.5), (2, "Logística Norte", None)]


def test_no_se_registran_tramos_antes_de_despachar_ni_con_datos_invalidos(cx):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con(a)
    with pytest.raises(TransicionInvalida):
        remitos.registrar_tramo(remito.id, "A", "B", "T", datetime(2026, 11, 2, 12, 30))

    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    with pytest.raises(EntradaInvalida, match="transportista"):
        remitos.registrar_tramo(remito.id, "A", "B", "  ", datetime(2026, 11, 2, 12, 30))
    with pytest.raises(ReglaNegocio, match="anterior a su salida"):
        remitos.registrar_tramo(remito.id, "A", "B", "T", datetime(2026, 11, 2, 12, 30), datetime(2026, 11, 2, 12, 0))
    assert remitos.obtener_remito(remito.id).tramos == ()


# --- Recepción en el laboratorio ---

def en_transito(*conservadoras):
    remito = remito_con(*conservadoras)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    return remito


def test_recepcion_total_aceptada(cx):
    a, _ = conservadora_precintada("C-A")
    b, _ = conservadora_precintada("C-B")
    remito = en_transito(a, b)

    recibida = remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a), detalle(b)])

    assert recibida.remito.estado.nombre == "RECIBIDO" and recibida.alertas == ()
    assert estados(remito.id) == ["RECIBIDA", "RECIBIDA"]
    guardada = remitos.obtener_remito(remito.id).recepcion
    assert guardada.responsable == "Bioq. Pérez" and guardada.todas_aceptadas


def test_recepcion_parcial_rechaza_solo_las_muestras_de_la_conservadora_con_problemas(cx):
    a, creadas_a = conservadora_precintada("C-A")
    b, creadas_b = conservadora_precintada("C-B")
    remito = en_transito(a, b)

    recibida = remitos.registrar_recepcion(
        remito.id, "Bioq. Pérez", [detalle(a), detalle(b, precinto="roto", observacion="Llegó abierto")])

    assert recibida.remito.estado.nombre == "RECIBIDO_PARCIAL"
    assert len(recibida.alertas) == 1 and "PRECINTO_ROTO" in recibida.alertas[0]  # aviso para la clínica
    assert muestras.obtener_muestra(creadas_a[0][2].id).estado.nombre == "RECIBIDA"
    rechazada = muestras.obtener_muestra(creadas_b[0][2].id)
    assert rechazada.estado.nombre == "RECHAZADA" and rechazada.estado.motivos == (MotivoRechazo.PRECINTO_ROTO,)
    assert [c.nuevo for c in muestras.trazabilidad_de_muestra(rechazada.id)] == [
        "EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECHAZADA"]


def test_recepcion_con_todas_rechazadas_por_temperatura(cx):
    a, creadas = conservadora_precintada("C-A")
    remito = en_transito(a)

    recibida = remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a, temperatura="19,5")])

    assert recibida.remito.estado.nombre == "RECHAZADO"
    assert muestras.obtener_muestra(creadas[0][2].id).estado.motivos == (MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO,)


def test_la_recepcion_tiene_que_cubrir_exactamente_las_conservadoras_del_remito(cx):
    a, _ = conservadora_precintada("C-A")
    b, _ = conservadora_precintada("C-B")
    ajena, _ = conservadora_precintada("C-X")
    remito = en_transito(a, b)

    with pytest.raises(ReglaNegocio, match="un detalle por cada conservadora"):
        remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a)])  # falta la B
    with pytest.raises(ReglaNegocio, match="no está en el remito"):
        remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a), detalle(ajena)])

    assert remitos.obtener_remito(remito.id).estado.nombre == "EN_TRANSITO"  # nada cambió
    assert estados(remito.id) == ["EN_TRANSITO", "EN_TRANSITO"]


def test_recepcion_con_datos_invalidos(cx):
    a, _ = conservadora_precintada("C-A")
    remito = en_transito(a)
    with pytest.raises(EntradaInvalida, match="estado del precinto"):
        remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a, precinto="quizás")])
    with pytest.raises(EntradaInvalida, match="temperatura de llegada"):
        remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a, temperatura="fría")])
    with pytest.raises(EntradaInvalida, match="responsable es obligatorio"):
        remitos.registrar_recepcion(remito.id, "", [detalle(a)])


def test_no_se_recibe_un_remito_que_no_esta_en_transito_ni_dos_veces(cx):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con(a)
    with pytest.raises(TransicionInvalida, match="ABIERTO"):
        remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a)])

    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a)])
    with pytest.raises(TransicionInvalida, match="RECIBIDO"):
        remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a)])


def test_listar_remitos_por_estado(cx):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con(a)
    assert [r.id for r in remitos.listar_remitos("abierto")] == [remito.id]
    assert remitos.listar_remitos("EN_TRANSITO") == []


# --- Cada caso de uso es una sola transacción ---

def test_si_un_caso_de_uso_falla_a_mitad_de_camino_no_queda_nada_a_medias(cx, monkeypatch):
    a, _ = conservadora_precintada("C-A")
    remito = en_transito(a)

    def falla_al_final(self, remito):
        raise RuntimeError("se cortó la luz justo al guardar el remito")

    # La recepción cambia primero las muestras y recién al final guarda el remito: si eso falla,
    # TODO se deshace, incluso lo que ya se había escrito de las muestras.
    with monkeypatch.context() as parche:  # el parche vale solo dentro de este bloque
        parche.setattr(RepositorioRemitos, "guardar", falla_al_final)
        with pytest.raises(RuntimeError):
            remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [detalle(a, precinto="roto")])

    assert estados(remito.id) == ["EN_TRANSITO"]  # la muestra NO quedó rechazada
    assert remitos.obtener_remito(remito.id).estado.nombre == "EN_TRANSITO"
    assert cx.execute("SELECT COUNT(*) FROM recepciones").fetchone()[0] == 0
    assert cx.execute("SELECT COUNT(*) FROM cambios_estado WHERE nuevo = 'RECHAZADA'").fetchone()[0] == 0

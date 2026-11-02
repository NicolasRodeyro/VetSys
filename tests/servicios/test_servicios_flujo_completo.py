"""El sistema completo, recorrido solo con la capa de servicios (como lo hará la interfaz).

Es el guion de la demo: turno -> consulta con advertencia de vacunas -> orden -> extracción ->
conservadora -> remito -> envío -> recepción con precinto roto -> alerta -> re-extracción ->
segundo envío -> resultado -> cierre de consulta y comprobante.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.dominio.enums import MotivoRechazo
from app.dominio.resultado_analisis import ValorResultado
from app.servicios import catalogos, clientes, consultas, muestras, remitos, resultados, turnos
from app.servicios.remitos import DetalleDeRecepcion
from tests.servicios.conftest import AHORA, mascota, veterinario

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


def enviar(numero_conservadora: str, muestra_id: int, precinto: str):
    """Empaqueta, precinta, arma el remito, lo despacha y el laboratorio lo recibe."""
    conservadora = muestras.crear_conservadora(numero_conservadora, 5, 4, 6)
    muestras.empaquetar_muestra(muestra_id, conservadora.id, "Enf. Ruiz", "Clínica Centro")
    muestras.precintar_conservadora(conservadora.id, f"P-{numero_conservadora}", "Enf. Ruiz")

    remito = remitos.crear_remito(catalogos.listar_clinicas()[0].id, catalogos.listar_laboratorios()[0].id)
    remitos.agregar_conservadora_a_remito(remito.id, conservadora.id)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur", "Clínica Centro")
    remitos.registrar_tramo(remito.id, "Clínica Centro", "Laboratorio Central", "Transportes Sur",
                            datetime(2026, 11, 2, 12, 30), datetime(2026, 11, 2, 13, 30), 5.2)
    return remitos.registrar_recepcion(
        remito.id, "Bioq. Pérez", [DetalleDeRecepcion(conservadora.id, precinto, 5.2)]), remito


def test_flujo_completo_con_precinto_roto_y_re_extraccion(cx):
    ana_toby, vet = mascota("30111222", "Toby"), veterinario("MP-1001")

    # 1. Turno y consulta. Al 02/11/2026 a Toby le venció el refuerzo de la Sextuple (octubre) y nunca
    #    recibió la Tos de las perreras; su Antirrábica vence recién el 20/11. Se advierte, no se bloquea.
    turno = turnos.reservar_turno(vet.id, ana_toby.id, AHORA, 30)
    consulta = consultas.registrar_consulta(ana_toby.id, vet.id, "CONTROL", turno_id=turno.id,
                                            diagnostico="Control anual")
    assert set(consulta.advertencias) == {"Vacuna pendiente: Sextuple", "Vacuna pendiente: Tos de las perreras"}

    # 2. Orden de derivación y extracción de la muestra.
    orden = consultas.emitir_orden(consulta.id, "Hemograma", "urgente")
    primera = muestras.registrar_extraccion(orden.id, "Dr. Gómez", "Clínica Centro")

    # 3. Primer envío: llega con el precinto roto y se rechaza.
    recepcion, remito_1 = enviar("C-1", primera.id, "ROTO")
    assert recepcion.remito.estado.nombre == "RECHAZADO"
    assert len(recepcion.alertas) == 1 and "re-extracción" in recepcion.alertas[0]  # aviso a la clínica

    # 4. Re-extracción sin cargo en la misma orden, y segundo envío: llega bien.
    segunda = muestras.registrar_reextraccion(primera.id, "Dr. Gómez", "Clínica Centro")
    recepcion, remito_2 = enviar("C-2", segunda.id, "INTACTO")
    assert recepcion.remito.estado.nombre == "RECIBIDO" and recepcion.alertas == ()

    # 5. El laboratorio registra el resultado y se avisa al responsable.
    registrado = resultados.registrar_resultado(
        segunda.id, "Bioq. Pérez", [ValorResultado("Hematocrito", 41.0, "%", 37.0, 55.0)])
    assert registrado.avisos == ("Ana Paz: ya está el resultado de Hemograma",)

    # 6. Se cierra la consulta: UN solo análisis cobrado, aunque hubo dos extracciones.
    comprobante = consultas.cerrar_consulta(consulta.id, "3000")
    assert [i.descripcion for i in comprobante.items] == ["Control", "Hemograma"]
    assert comprobante.total == Decimal("15500.00")

    # --- Verificación final: todo quedó guardado y trazable ---
    guardada = consultas.obtener_consulta(consulta.id)
    (orden_guardada,) = guardada.ordenes
    rechazada, analizada = orden_guardada.muestras
    assert [c.nuevo for c in muestras.trazabilidad_de_muestra(rechazada.id)] == [
        "EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECHAZADA"]
    assert rechazada.estado.motivos == (MotivoRechazo.PRECINTO_ROTO,)
    assert [c.nuevo for c in muestras.trazabilidad_de_muestra(analizada.id)] == [
        "EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA", "ANALIZADA"]
    assert [r.estado.nombre for r in remitos.listar_remitos()] == ["RECIBIDO", "RECHAZADO"]  # el más nuevo primero
    assert len(remito_1.numero) == len(remito_2.numero) == 7
    assert [c.id for c in clientes.obtener_mascota(ana_toby.id).historia_clinica.consultas] == [consulta.id]
    assert cx.execute("SELECT COUNT(*) FROM cambios_estado").fetchone()[0] == 9  # 4 + 5 renglones de trazabilidad

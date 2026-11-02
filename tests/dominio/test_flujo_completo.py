"""Recorrido completo del dominio, de la orden a la recepción, con objetos reales.

Es el guion de la demo: flujo feliz y flujo con precinto roto y re-extracción.
"""

from datetime import datetime

from app.dominio.enums import EstadoPrecinto, MotivoRechazo
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import AlertaRechazo, RegistroTrazabilidad
from app.dominio.recepcion import DetalleRecepcion, Recepcion
from app.dominio.remito_biologico import RemitoBiologico

HORA = datetime(2026, 6, 1, 10, 0)


def extraer(orden, reloj) -> tuple[Muestra, AlertaRechazo]:
    muestra = Muestra(orden, "Dr. Gómez", "Clínica Centro", reloj=reloj)
    muestra.suscribir(RegistroTrazabilidad())
    alerta = AlertaRechazo()
    muestra.suscribir(alerta)
    return muestra, alerta


def enviar(muestra, numero, clinica, laboratorio, crear_conservadora, rota: bool) -> RemitoBiologico:
    conservadora = crear_conservadora(f"C-{numero}")
    conservadora.agregar_muestra(muestra, "Enf. Ruiz", "Clínica Centro")
    conservadora.precintar(f"P-{numero}", "Enf. Ruiz", HORA)

    remito = RemitoBiologico(numero, clinica, laboratorio)
    remito.agregar_conservadora(conservadora)
    remito.cerrar()
    remito.despachar("Transportes Sur", "Clínica Centro")
    remito.registrar_tramo("Clínica Centro", laboratorio.nombre, "Transportes Sur", HORA, HORA, 5.0)

    precinto = EstadoPrecinto.ROTO if rota else EstadoPrecinto.INTACTO
    remito.registrar_recepcion(
        Recepcion(
            laboratorio, "Bioq. Pérez", datetime(2026, 6, 1, 14, 0),
            [DetalleRecepcion(conservadora, precinto, 5.0)],
        )
    )
    return remito


def test_flujo_feliz_de_la_extraccion_al_analisis(orden, clinica, laboratorio, crear_conservadora, reloj):
    muestra, alerta = extraer(orden, reloj)

    remito = enviar(muestra, "R-1", clinica, laboratorio, crear_conservadora, rota=False)
    muestra.analizar("Bioq. Pérez", "Laboratorio Central")

    assert remito.estado.nombre == "RECIBIDO"
    assert [c.nuevo for c in muestra.historial] == [
        "EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA", "ANALIZADA"
    ]
    assert alerta.alertas == ()


def test_flujo_con_precinto_roto_y_re_extraccion(orden, clinica, laboratorio, crear_conservadora, reloj):
    # 1. La primera muestra llega con el precinto roto y se rechaza.
    primera, alerta = extraer(orden, reloj)
    remito_1 = enviar(primera, "R-1", clinica, laboratorio, crear_conservadora, rota=True)

    assert remito_1.estado.nombre == "RECHAZADO"
    assert primera.estado.nombre == "RECHAZADA"
    assert primera.estado.motivos == (MotivoRechazo.PRECINTO_ROTO,)
    assert len(alerta.alertas) == 1  # se avisa a la clínica
    assert orden.muestra_activa() is None  # la orden queda libre para re-extraer

    # 2. Re-extracción sin cargo: nueva muestra en la MISMA orden.
    segunda, _ = extraer(orden, reloj)
    remito_2 = enviar(segunda, "R-2", clinica, laboratorio, crear_conservadora, rota=False)
    segunda.analizar("Bioq. Pérez", "Laboratorio Central")

    assert remito_2.estado.nombre == "RECIBIDO"
    assert orden.muestras == (primera, segunda)
    assert orden.muestra_activa() is segunda
    # La trazabilidad de la rechazada se conserva intacta.
    assert [c.nuevo for c in primera.historial][-1] == "RECHAZADA"


def test_flujo_de_punta_a_punta_de_la_consulta_al_comprobante(
    perro, veterinario, hemograma, clinica, laboratorio, crear_conservadora, reloj
):
    """Consulta con vacunas pendientes -> orden -> muestra -> conservadora -> remito ->
    envío -> recepción -> resultado -> comprobante. Todo con objetos reales."""
    from decimal import Decimal

    from app.dominio.consulta import Consulta
    from app.dominio.enums import TipoConsulta
    from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado

    # 1. Consulta: la mascota tiene vacunas pendientes, se advierte pero se atiende.
    consulta = Consulta(TipoConsulta.CONSULTA, datetime(2026, 5, 10, 11, 0), perro, veterinario)
    perro.historia_clinica.registrar_consulta(consulta)
    assert len(consulta.advertencias) == 2

    # 2. Orden de derivación y extracción.
    orden = consulta.emitir_orden(hemograma)
    muestra, _ = extraer(orden, reloj)

    # 3. Empaquetado, envío y recepción.
    remito = enviar(muestra, "R-1", clinica, laboratorio, crear_conservadora, rota=False)
    assert remito.estado.nombre == "RECIBIDO"

    # 4. Resultado.
    resultado = ResultadoAnalisis(
        muestra, "Bioq. Pérez", datetime(2026, 6, 2, 9, 0),
        [ValorResultado("Hematocrito", 41.0, "%", 37.0, 55.0)],
    )
    assert muestra.estado.nombre == "ANALIZADA"
    assert resultado.valores_fuera_de_rango() == ()

    # 5. Comprobante: la consulta más el análisis derivado.
    comprobante = consulta.cerrar(Decimal("3000"), datetime(2026, 6, 2, 10, 0))
    assert comprobante.total == Decimal("15500")
    assert comprobante.cliente is perro.responsable

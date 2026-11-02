from datetime import datetime
from itertools import product
from types import SimpleNamespace

import pytest

from app.dominio.enums import EstadoPrecinto, MotivoRechazo
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.recepcion import DetalleRecepcion, Recepcion
from app.dominio.remito_biologico import RemitoBiologico

AHORA = datetime(2026, 6, 1, 10, 0)


@pytest.fixture
def armar(clinica, laboratorio, crear_conservadora, crear_muestra):
    """Arma un remito abierto con dos conservadoras precintadas (A con 2 muestras y
    B con 1) y una tercera, `extra`, que no está en el remito."""

    def _conservadora_precintada(codigo, cantidad):
        conservadora = crear_conservadora(codigo)
        for _ in range(cantidad):
            conservadora.agregar_muestra(crear_muestra(), "Enf. Ruiz", "Clínica Centro")
        conservadora.precintar(f"P-{codigo}", "Enf. Ruiz", AHORA)
        return conservadora

    def _armar() -> SimpleNamespace:
        a, b, extra = (_conservadora_precintada(c, n) for c, n in (("A", 2), ("B", 1), ("X", 1)))
        remito = RemitoBiologico("R-001", clinica, laboratorio)
        remito.agregar_conservadora(a)
        remito.agregar_conservadora(b)
        return SimpleNamespace(remito=remito, a=a, b=b, extra=extra, laboratorio=laboratorio)

    return _armar


def recepcion_de(esc, rotas=(), temperatura=5.0) -> Recepcion:
    detalles = [
        DetalleRecepcion(
            c, EstadoPrecinto.ROTO if c in rotas else EstadoPrecinto.INTACTO, temperatura
        )
        for c in (esc.a, esc.b)
    ]
    return Recepcion(esc.laboratorio, "Bioq. Pérez", datetime(2026, 6, 1, 14, 0), detalles)


def nombres_de_muestras(*conservadoras) -> set[str]:
    return {m.estado.nombre for c in conservadoras for m in c.muestras}


# --- Remito nuevo ---

def test_remito_nuevo_esta_abierto_y_sin_tramos_ni_recepcion(armar):
    esc = armar()
    assert esc.remito.estado.nombre == "ABIERTO"
    assert esc.remito.tramos == ()
    assert esc.remito.recepcion is None
    assert esc.remito.conservadoras == (esc.a, esc.b)


# --- Abierto: agregar, quitar y cerrar ---

def test_cerrar_sin_conservadoras_falla(clinica, laboratorio):
    remito = RemitoBiologico("R-002", clinica, laboratorio)
    with pytest.raises(ReglaNegocio, match="al menos una conservadora"):
        remito.cerrar()
    assert remito.estado.nombre == "ABIERTO"


def test_cerrar_con_una_conservadora_sin_precinto_falla(armar, crear_conservadora, crear_muestra):
    esc = armar()
    sin_precinto = crear_conservadora("S")
    sin_precinto.agregar_muestra(crear_muestra(), "Enf. Ruiz")
    esc.remito.agregar_conservadora(sin_precinto)

    with pytest.raises(ReglaNegocio, match="precinto.*S"):
        esc.remito.cerrar()
    assert esc.remito.estado.nombre == "ABIERTO"


def test_cerrar_con_todas_precintadas(armar):
    esc = armar()
    esc.remito.cerrar()
    assert esc.remito.estado.nombre == "CERRADO"


def test_no_se_agrega_dos_veces_la_misma_conservadora(armar):
    esc = armar()
    with pytest.raises(ReglaNegocio, match="ya está en el remito"):
        esc.remito.agregar_conservadora(esc.a)
    assert esc.remito.conservadoras == (esc.a, esc.b)


def test_quitar_conservadora_no_desempaqueta_sus_muestras(armar):
    esc = armar()
    esc.remito.quitar_conservadora(esc.b)

    assert esc.remito.conservadoras == (esc.a,)
    assert len(esc.b.muestras) == 1  # las muestras siguen en la conservadora
    assert nombres_de_muestras(esc.b) == {"EMPAQUETADA"}


def test_no_se_puede_quitar_una_conservadora_que_no_esta(armar):
    esc = armar()
    with pytest.raises(ReglaNegocio, match="no está en el remito"):
        esc.remito.quitar_conservadora(esc.extra)


def test_agregar_conservadora_a_un_remito_cerrado_falla(armar):
    esc = armar()
    esc.remito.cerrar()
    with pytest.raises(TransicionInvalida, match="CERRADO"):
        esc.remito.agregar_conservadora(esc.extra)
    assert esc.remito.conservadoras == (esc.a, esc.b)


def test_quitar_conservadora_de_un_remito_cerrado_falla(armar):
    esc = armar()
    esc.remito.cerrar()
    with pytest.raises(TransicionInvalida):
        esc.remito.quitar_conservadora(esc.a)


# --- Cerrado: despachar ---

def test_despachar_pasa_el_remito_y_todas_sus_muestras_a_en_transito(armar):
    esc = armar()
    esc.remito.cerrar()
    assert nombres_de_muestras(esc.a, esc.b) == {"EMPAQUETADA"}

    esc.remito.despachar("Transportes Sur", "Clínica Centro")

    assert esc.remito.estado.nombre == "EN_TRANSITO"
    assert nombres_de_muestras(esc.a, esc.b) == {"EN_TRANSITO"}
    assert nombres_de_muestras(esc.extra) == {"EMPAQUETADA"}  # la que no está en el remito no se toca


def test_el_despacho_queda_en_la_trazabilidad_de_cada_muestra(armar):
    esc = armar()
    muestra = esc.a.muestras[0]
    muestra.suscribir(RegistroTrazabilidad())
    esc.remito.cerrar()

    esc.remito.despachar("Transportes Sur", "Clínica Centro")

    despacho = muestra.historial[-1]
    assert (despacho.anterior, despacho.nuevo) == ("EMPAQUETADA", "EN_TRANSITO")
    assert despacho.responsable == "Transportes Sur"
    assert "R-001" in despacho.observacion


def test_no_se_puede_despachar_un_remito_abierto(armar):
    esc = armar()
    with pytest.raises(TransicionInvalida, match="ABIERTO"):
        esc.remito.despachar("Transportes Sur")
    assert nombres_de_muestras(esc.a, esc.b) == {"EMPAQUETADA"}


# --- EnTransito: tramos ---

def test_registrar_tramos_numera_en_orden(armar):
    esc = armar()
    esc.remito.cerrar()
    esc.remito.despachar("Transportes Sur")

    esc.remito.registrar_tramo("Clínica Centro", "Centro de distribución", "Transportes Sur", AHORA)
    esc.remito.registrar_tramo(
        "Centro de distribución", "Laboratorio", "Logística Norte",
        datetime(2026, 6, 1, 12, 0), datetime(2026, 6, 1, 13, 0), 5.5,
    )

    assert [t.orden for t in esc.remito.tramos] == [1, 2]
    assert esc.remito.tramos[1].temperatura == 5.5


@pytest.mark.parametrize("preparar", ["abierto", "cerrado"])
def test_no_se_registran_tramos_antes_de_despachar(armar, preparar):
    esc = armar()
    if preparar == "cerrado":
        esc.remito.cerrar()
    with pytest.raises(TransicionInvalida):
        esc.remito.registrar_tramo("A", "B", "T", AHORA)
    assert esc.remito.tramos == ()


# --- EnTransito: recepción ---

def en_transito(esc):
    esc.remito.cerrar()
    esc.remito.despachar("Transportes Sur")


def test_recepcion_total_aceptada(armar):
    esc = armar()
    en_transito(esc)
    recepcion = recepcion_de(esc)

    esc.remito.registrar_recepcion(recepcion)

    assert esc.remito.estado.nombre == "RECIBIDO"
    assert nombres_de_muestras(esc.a, esc.b) == {"RECIBIDA"}
    assert esc.remito.recepcion is recepcion


def test_recepcion_parcial_rechaza_solo_las_muestras_de_la_conservadora_con_problemas(armar):
    esc = armar()
    en_transito(esc)

    esc.remito.registrar_recepcion(recepcion_de(esc, rotas=(esc.b,)))

    assert esc.remito.estado.nombre == "RECIBIDO_PARCIAL"
    assert nombres_de_muestras(esc.a) == {"RECIBIDA"}
    assert nombres_de_muestras(esc.b) == {"RECHAZADA"}
    assert esc.b.muestras[0].estado.motivos == (MotivoRechazo.PRECINTO_ROTO,)


def test_recepcion_con_todas_rechazadas(armar):
    esc = armar()
    en_transito(esc)

    esc.remito.registrar_recepcion(recepcion_de(esc, rotas=(esc.a, esc.b)))

    assert esc.remito.estado.nombre == "RECHAZADO"
    assert nombres_de_muestras(esc.a, esc.b) == {"RECHAZADA"}


def test_temperatura_fuera_de_rango_rechaza_aunque_el_precinto_este_intacto(armar):
    esc = armar()
    en_transito(esc)

    esc.remito.registrar_recepcion(recepcion_de(esc, temperatura=15.0))

    assert esc.remito.estado.nombre == "RECHAZADO"
    assert esc.a.muestras[0].estado.motivos == (MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO,)


def test_la_recepcion_queda_en_la_trazabilidad_de_las_muestras(armar):
    esc = armar()
    muestra = esc.a.muestras[0]
    muestra.suscribir(RegistroTrazabilidad())
    en_transito(esc)

    esc.remito.registrar_recepcion(recepcion_de(esc))

    recibida = muestra.historial[-1]
    assert (recibida.anterior, recibida.nuevo) == ("EN_TRANSITO", "RECIBIDA")
    assert recibida.responsable == "Bioq. Pérez"
    assert recibida.ubicacion == "Laboratorio Central"


def test_muestra_rechazada_por_el_remito_libera_su_orden_para_re_extraer(armar, crear_muestra):
    esc = armar()
    en_transito(esc)
    rechazada = esc.b.muestras[0]
    esc.remito.registrar_recepcion(recepcion_de(esc, rotas=(esc.b,)))

    assert rechazada.orden.muestra_activa() is None  # ya se puede re-extraer


def test_recepcion_que_no_cubre_todas_las_conservadoras_falla_y_no_cambia_nada(armar):
    esc = armar()
    en_transito(esc)
    incompleta = Recepcion(
        esc.laboratorio, "Bioq. Pérez", AHORA,
        [DetalleRecepcion(esc.a, EstadoPrecinto.INTACTO, 5.0)],  # falta la B
    )

    with pytest.raises(ReglaNegocio, match="un detalle por cada conservadora"):
        esc.remito.registrar_recepcion(incompleta)

    assert esc.remito.estado.nombre == "EN_TRANSITO"
    assert nombres_de_muestras(esc.a, esc.b) == {"EN_TRANSITO"}
    assert esc.remito.recepcion is None


def test_recepcion_con_una_conservadora_que_no_es_del_remito_falla(armar):
    esc = armar()
    en_transito(esc)
    ajena = Recepcion(
        esc.laboratorio, "Bioq. Pérez", AHORA,
        [
            DetalleRecepcion(esc.a, EstadoPrecinto.INTACTO, 5.0),
            DetalleRecepcion(esc.extra, EstadoPrecinto.INTACTO, 5.0),
        ],
    )
    with pytest.raises(ReglaNegocio):
        esc.remito.registrar_recepcion(ajena)
    assert esc.remito.estado.nombre == "EN_TRANSITO"


def test_recepcion_con_una_conservadora_repetida_falla(armar):
    esc = armar()
    en_transito(esc)
    repetida = Recepcion(
        esc.laboratorio, "Bioq. Pérez", AHORA,
        [
            DetalleRecepcion(esc.a, EstadoPrecinto.INTACTO, 5.0),
            DetalleRecepcion(esc.a, EstadoPrecinto.INTACTO, 5.0),
        ],
    )
    with pytest.raises(ReglaNegocio):
        esc.remito.registrar_recepcion(repetida)
    assert esc.remito.estado.nombre == "EN_TRANSITO"


# --- Cada estado solo permite sus operaciones ---

ESTADOS = ["ABIERTO", "CERRADO", "EN_TRANSITO", "RECIBIDO", "RECIBIDO_PARCIAL", "RECHAZADO"]

OPERACIONES = {
    "agregar_conservadora": lambda esc: esc.remito.agregar_conservadora(esc.extra),
    "quitar_conservadora": lambda esc: esc.remito.quitar_conservadora(esc.a),
    "cerrar": lambda esc: esc.remito.cerrar(),
    "despachar": lambda esc: esc.remito.despachar("x"),
    "registrar_tramo": lambda esc: esc.remito.registrar_tramo("A", "B", "T", AHORA),
    "registrar_recepcion": lambda esc: esc.remito.registrar_recepcion(recepcion_de(esc)),
}

PERMITIDAS = {
    "ABIERTO": {"agregar_conservadora", "quitar_conservadora", "cerrar"},
    "CERRADO": {"despachar"},
    "EN_TRANSITO": {"registrar_tramo", "registrar_recepcion"},
    "RECIBIDO": set(), "RECIBIDO_PARCIAL": set(), "RECHAZADO": set(),
}


def llevar_a(esc, estado: str) -> None:
    if estado == "ABIERTO":
        return
    esc.remito.cerrar()
    if estado == "CERRADO":
        return
    esc.remito.despachar("Transportes Sur")
    if estado == "EN_TRANSITO":
        return
    rotas = {"RECIBIDO": (), "RECIBIDO_PARCIAL": (esc.b,), "RECHAZADO": (esc.a, esc.b)}[estado]
    esc.remito.registrar_recepcion(recepcion_de(esc, rotas))


COMBINACIONES_INVALIDAS = [
    (estado, operacion)
    for estado, operacion in product(ESTADOS, OPERACIONES)
    if operacion not in PERMITIDAS[estado]
]


@pytest.mark.parametrize("estado, operacion", COMBINACIONES_INVALIDAS)
def test_operacion_no_permitida_lanza_error_y_no_cambia_nada(armar, estado, operacion):
    esc = armar()
    llevar_a(esc, estado)
    estado_antes = esc.remito.estado
    conservadoras_antes = esc.remito.conservadoras
    tramos_antes = esc.remito.tramos

    with pytest.raises(TransicionInvalida, match=estado):
        OPERACIONES[operacion](esc)

    assert esc.remito.estado is estado_antes
    assert esc.remito.conservadoras == conservadoras_antes
    assert esc.remito.tramos == tramos_antes


@pytest.mark.parametrize("estado", ESTADOS)
def test_estados_finales_son_los_tres_de_la_recepcion(armar, estado):
    esc = armar()
    llevar_a(esc, estado)
    assert esc.remito.estado.es_final == (estado in {"RECIBIDO", "RECIBIDO_PARCIAL", "RECHAZADO"})


def test_listas_del_remito_no_se_modifican_desde_afuera(armar):
    esc = armar()
    with pytest.raises(AttributeError):
        esc.remito.conservadoras.append("x")  # es una tupla
    with pytest.raises(AttributeError):
        esc.remito.tramos.append("x")

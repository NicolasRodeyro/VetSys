from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.consulta import Consulta
from app.dominio.enums import MotivoRechazo, Sexo, TipoConsulta
from app.dominio.especie import Especie
from app.dominio.excepciones import ReglaNegocio, TransicionInvalida
from app.dominio.mascota import Mascota
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.veterinario import Veterinario
from app.persistencia.identidad import HistorialIncompleto


class Reloj:
    """Reloj de prueba: cada consulta avanza media hora."""

    def __init__(self):
        self.actual = datetime(2026, 6, 1, 9, 0)

    def __call__(self):
        valor, self.actual = self.actual, self.actual + timedelta(minutes=30)
        return valor


@pytest.fixture
def escenario(sesion):
    """Consulta con una orden de hemograma, todo guardado. Devuelve (ctx, consulta, orden)."""
    ctx = sesion()
    cliente = Cliente("30111222", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)
    veterinario = Veterinario("MP-1", "Laura", "Gómez", Clinica("Centro", ""))
    consulta = Consulta(TipoConsulta.CONSULTA, datetime(2026, 5, 10, 11, 0), toby, veterinario)
    orden = consulta.emitir_orden(TipoAnalisis("Hemograma", Decimal("12500"), "Sangre", 2.0, 8.0, 24))
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.clientes.guardar(cliente)
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()
    return ctx, consulta, orden


def extraer(orden, reloj=None) -> Muestra:
    muestra = Muestra(orden, "Dr. Gómez", "Clínica Centro", reloj=reloj or Reloj())
    muestra.suscribir(RegistroTrazabilidad())
    return muestra


def orden_cargada(sesion):
    """La primera orden de la primera consulta, cargada en una sesión nueva."""
    ctx = sesion()
    cliente = ctx.clientes.obtener_por_dni("30111222")
    return ctx, cliente.mascotas[0].historia_clinica.consultas[0].ordenes[0]


def guardar_orden(ctx, orden):
    ctx.ordenes.guardar(orden)  # la orden ya está guardada: se actualizan sus muestras
    ctx.conexion.commit()


# --- Guardar y recuperar una muestra con su historial y estado (criterio del plan) ---

def test_muestra_rechazada_vuelve_con_su_estado_motivos_e_historial(escenario, sesion):
    ctx, consulta, orden = escenario
    muestra = extraer(orden)
    muestra.empaquetar("Enf. Ruiz", "Clínica Centro", "Conservadora C-1")
    muestra.despachar("Transportes Sur", "Clínica Centro", "Remito R-1")
    muestra.recibir(False, "Bioq. Pérez", [MotivoRechazo.PRECINTO_ROTO, MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO],
                    "Laboratorio", "Llegó caliente y con el precinto roto")
    esperado = muestra.historial
    guardar_orden(ctx, orden)

    _, orden2 = orden_cargada(sesion)
    (cargada,) = orden2.muestras

    assert cargada.estado.nombre == "RECHAZADA"
    assert cargada.estado.motivos == (MotivoRechazo.PRECINTO_ROTO, MotivoRechazo.TEMPERATURA_FUERA_DE_RANGO)
    assert cargada.estado.es_final and not cargada.esta_activa()
    assert cargada.historial == esperado  # mismos renglones, mismo orden, mismos valores
    assert [c.nuevo for c in cargada.historial] == ["EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECHAZADA"]
    assert cargada.historial[-1].observacion == "Llegó caliente y con el precinto roto"
    assert cargada.orden is orden2 and orden2.muestra_activa() is None


def test_recorrido_completo_vuelve_en_estado_analizada(escenario, sesion):
    ctx, consulta, orden = escenario
    muestra = extraer(orden)
    muestra.empaquetar("Enf. Ruiz")
    muestra.despachar("Transportes Sur")
    muestra.recibir(True, "Bioq. Pérez")
    muestra.analizar("Bioq. Pérez", "Laboratorio")
    guardar_orden(ctx, orden)

    _, orden2 = orden_cargada(sesion)

    cargada = orden2.muestra_activa()
    assert cargada.estado.nombre == "ANALIZADA" and cargada.estado.es_final
    assert cargada.historial == muestra.historial and len(cargada.historial) == 5


def test_re_extraccion_vuelve_con_ambas_muestras_y_la_activa(escenario, sesion):
    ctx, consulta, orden = escenario
    reloj = Reloj()
    primera = extraer(orden, reloj)
    primera.empaquetar("x"); primera.despachar("x"); primera.recibir(False, "x", [MotivoRechazo.PRECINTO_ROTO])
    extraer(orden, reloj)  # la re-extracción
    guardar_orden(ctx, orden)

    _, orden2 = orden_cargada(sesion)

    rechazada, activa = orden2.muestras
    assert rechazada.estado.nombre == "RECHAZADA" and activa.estado.nombre == "EXTRAIDA"
    assert orden2.muestra_activa() is activa
    with pytest.raises(ReglaNegocio, match="muestra activa"):  # la regla sigue valiendo al recargar
        Muestra(orden2, "Dr. Gómez")


# --- Después de cargar, la máquina de estados sigue funcionando ---

def test_una_muestra_cargada_puede_seguir_su_recorrido(escenario, sesion):
    ctx, consulta, orden = escenario
    extraer(orden).empaquetar("Enf. Ruiz")
    guardar_orden(ctx, orden)

    ctx2, orden2 = orden_cargada(sesion)
    muestra = orden2.muestra_activa()
    assert muestra.estado.nombre == "EMPAQUETADA"

    muestra.suscribir(RegistroTrazabilidad())  # los observadores no se persisten: se suscriben al cargar
    muestra.despachar("Transportes Sur", "Clínica Centro")  # usa el reloj real, ya no el de la carga
    assert muestra.estado.nombre == "EN_TRANSITO"
    assert isinstance(muestra.historial[-1].fecha_hora, datetime)
    ctx2.ordenes.guardar(orden2)
    ctx2.conexion.commit()

    _, orden3 = orden_cargada(sesion)
    assert [c.nuevo for c in orden3.muestra_activa().historial] == ["EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO"]


def test_una_muestra_cargada_sigue_rechazando_transiciones_invalidas(escenario, sesion):
    ctx, consulta, orden = escenario
    extraer(orden)
    guardar_orden(ctx, orden)

    muestra = orden_cargada(sesion)[1].muestra_activa()
    with pytest.raises(TransicionInvalida):
        muestra.despachar("x")  # una muestra Extraída no se despacha


def test_guardar_de_nuevo_agrega_solo_los_cambios_nuevos(escenario, sesion):
    ctx, consulta, orden = escenario
    muestra = extraer(orden)
    guardar_orden(ctx, orden)
    muestra.empaquetar("Enf. Ruiz")
    guardar_orden(ctx, orden)
    guardar_orden(ctx, orden)  # sin cambios: no inserta nada

    assert ctx.conexion.execute("SELECT COUNT(*) FROM cambios_estado").fetchone()[0] == 2
    assert ctx.conexion.execute("SELECT estado FROM muestras").fetchone()[0] == "EMPAQUETADA"


# --- Integridad de la trazabilidad ---

def test_guardar_sin_registro_de_trazabilidad_avisa_que_el_historial_esta_incompleto(escenario):
    ctx, consulta, orden = escenario
    muestra = Muestra(orden, "Dr. Gómez", reloj=Reloj())  # sin suscribir RegistroTrazabilidad
    muestra.empaquetar("Enf. Ruiz")

    with pytest.raises(HistorialIncompleto, match="EMPAQUETADA"):
        guardar_orden(ctx, orden)


def test_una_base_con_historial_incompleto_se_detecta_al_cargar(escenario, sesion):
    ctx, consulta, orden = escenario
    extraer(orden)
    guardar_orden(ctx, orden)
    # Alguien cambia el estado "a mano" sin dejar el renglón de trazabilidad.
    ctx.conexion.execute("UPDATE muestras SET estado = 'RECIBIDA'")
    ctx.conexion.commit()

    with pytest.raises(HistorialIncompleto):
        orden_cargada(sesion)


def test_la_trazabilidad_guardada_no_se_puede_modificar_desde_sql(escenario):
    import sqlite3

    ctx, consulta, orden = escenario
    extraer(orden)
    guardar_orden(ctx, orden)
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        ctx.conexion.execute("UPDATE cambios_estado SET responsable = 'Otro'")


def test_obtener_una_muestra_por_id_trae_la_misma_de_su_orden(escenario, sesion):
    ctx, consulta, orden = escenario
    extraer(orden)
    guardar_orden(ctx, orden)
    id_ = ctx.conexion.execute("SELECT id FROM muestras").fetchone()[0]

    nueva = sesion()
    muestra = nueva.muestras.obtener(id_)
    orden_id = nueva.mapa.id_de("orden", muestra.orden)
    assert nueva.ordenes.obtener(orden_id).muestras[0] is muestra
    assert nueva.muestras.obtener(999) is None


def test_listar_muestras_por_estado(escenario, sesion):
    ctx, consulta, orden = escenario
    reloj = Reloj()
    primera = extraer(orden, reloj)
    primera.empaquetar("x"); primera.despachar("x"); primera.recibir(False, "x", [MotivoRechazo.PRECINTO_ROTO])
    extraer(orden, reloj)
    guardar_orden(ctx, orden)

    nueva = sesion()
    assert len(nueva.muestras.listar_por_estado("RECHAZADA")) == 1
    assert len(nueva.muestras.listar_por_estado("EXTRAIDA")) == 1
    assert nueva.muestras.listar_por_estado("ANALIZADA") == []


def test_una_orden_nueva_no_se_guarda_sin_su_consulta(escenario):
    from app.dominio.orden_derivacion import OrdenDerivacion
    from app.persistencia.identidad import ObjetoNoGuardado

    ctx, consulta, orden = escenario
    suelta = OrdenDerivacion(orden.tipo_analisis)
    with pytest.raises(ObjetoNoGuardado, match="junto con su consulta"):
        ctx.ordenes.guardar(suelta)

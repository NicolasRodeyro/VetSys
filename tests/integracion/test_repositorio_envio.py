import sqlite3
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.conservadora import Conservadora
from app.dominio.consulta import Consulta
from app.dominio.enums import EstadoPrecinto, MotivoRechazo, Sexo, TipoConsulta
from app.dominio.especie import Especie
from app.dominio.excepciones import ReglaNegocio
from app.dominio.laboratorio import Laboratorio
from app.dominio.mascota import Mascota
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.recepcion import DetalleRecepcion, Recepcion
from app.dominio.remito_biologico import RemitoBiologico
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.veterinario import Veterinario
from app.persistencia.identidad import ObjetoNoGuardado

HORA = datetime(2026, 6, 1, 10, 0)


def muestras_de(consulta) -> list[Muestra]:
    return [m for orden in consulta.ordenes for m in orden.muestras]


def suscribir_trazabilidad(*muestras) -> None:
    """Lo que hará la capa de servicios al cargar muestras (los observadores no se persisten)."""
    for muestra in muestras:
        muestra.suscribir(RegistroTrazabilidad())


def guardar_todo(ctx, esc) -> None:
    """Guarda en el orden en que dependen entre sí: consulta (con órdenes y muestras),
    conservadoras y remito."""
    ctx.consultas.guardar(esc.consulta)
    for conservadora in esc.conservadoras:
        ctx.conservadoras.guardar(conservadora)
    if esc.remito is not None:
        ctx.remitos.guardar(esc.remito)
    ctx.conexion.commit()


@pytest.fixture
def armar(sesion):
    """Tres muestras de tres órdenes de una consulta, empaquetadas en dos conservadoras
    precintadas (A con 2 y B con 1) y un remito abierto con las dos. Todo guardado."""

    def _armar() -> SimpleNamespace:
        ctx = sesion()
        cliente = Cliente("30111222", "Ana", "Paz", "", "", "")
        toby = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)
        clinica = Clinica("Centro", "Av. Colón 100")
        veterinario = Veterinario("MP-1", "Laura", "Gómez", clinica)
        laboratorio = Laboratorio("Central", "Bv. Illia 1")
        hemograma = TipoAnalisis("Hemograma", Decimal("12500"), "Sangre", 2.0, 8.0, 24)

        consulta = Consulta(TipoConsulta.CONSULTA, datetime(2026, 5, 10, 11, 0), toby, veterinario)
        muestras = []
        for _ in range(3):
            orden = consulta.emitir_orden(hemograma)
            muestra = Muestra(orden, "Dr. Gómez", "Clínica Centro")
            suscribir_trazabilidad(muestra)
            muestras.append(muestra)
        toby.historia_clinica.registrar_consulta(consulta)

        a, b = Conservadora("C-A", 5, 4.0, 6.0), Conservadora("C-B", 5, 4.0, 6.0)
        a.agregar_muestra(muestras[0], "Enf. Ruiz", "Clínica Centro")
        a.agregar_muestra(muestras[1], "Enf. Ruiz", "Clínica Centro")
        b.agregar_muestra(muestras[2], "Enf. Ruiz", "Clínica Centro")
        a.precintar("P-A", "Enf. Ruiz", HORA)
        b.precintar("P-B", "Enf. Ruiz", HORA)

        remito = RemitoBiologico("R-001", clinica, laboratorio)
        remito.agregar_conservadora(a)
        remito.agregar_conservadora(b)

        ctx.clientes.guardar(cliente)
        esc = SimpleNamespace(ctx=ctx, consulta=consulta, a=a, b=b, conservadoras=[a, b], remito=remito,
                              laboratorio=laboratorio, clinica=clinica)
        guardar_todo(ctx, esc)
        return esc

    return _armar


def cargar_remito(sesion, numero="R-001"):
    """Carga un remito en una sesión nueva y suscribe la trazabilidad en sus muestras."""
    ctx = sesion()
    remito = ctx.remitos.obtener_por_numero(numero)
    for conservadora in remito.conservadoras:
        suscribir_trazabilidad(*conservadora.muestras)
    return ctx, remito


def guardar_cambios(ctx, remito) -> None:
    """Guarda lo que modificó un caso de uso sobre un remito cargado: las muestras (con su
    orden), las conservadoras y el remito."""
    ordenes = {id(m.orden): m.orden for c in remito.conservadoras for m in c.muestras}
    for orden in ordenes.values():
        ctx.ordenes.guardar(orden)
    for conservadora in remito.conservadoras:
        ctx.conservadoras.guardar(conservadora)
    ctx.remitos.guardar(remito)
    ctx.conexion.commit()


def recepcion_de(remito, laboratorio, rotas=()) -> Recepcion:
    detalles = [
        DetalleRecepcion(c, EstadoPrecinto.ROTO if c in rotas else EstadoPrecinto.INTACTO, 5.0)
        for c in remito.conservadoras
    ]
    return Recepcion(laboratorio, "Bioq. Pérez", datetime(2026, 6, 1, 14, 0), detalles)


# --- Conservadoras ---

def test_conservadora_vuelve_con_su_precinto_y_sus_muestras(armar, sesion):
    armar()
    ctx = sesion()
    a = ctx.conservadoras.obtener_por_codigo("C-A")

    assert (a.codigo, a.capacidad, a.temp_min, a.temp_max) == ("C-A", 5, 4.0, 6.0)
    assert (a.precinto.numero, a.precinto.responsable, a.precinto.fecha_colocacion) == ("P-A", "Enf. Ruiz", HORA)
    assert len(a.muestras) == 2
    assert {m.estado.nombre for m in a.muestras} == {"EMPAQUETADA"}
    assert a.muestras[0].orden.muestra_activa() is a.muestras[0]


def test_conservadora_sin_precinto_vuelve_sin_precinto(sesion):
    ctx = sesion()
    ctx.conservadoras.guardar(Conservadora("C-X", 3, 2.0, 8.0))
    ctx.conexion.commit()
    assert sesion().conservadoras.obtener_por_codigo("C-X").precinto is None


def test_las_muestras_de_la_conservadora_son_las_mismas_que_las_de_la_consulta(armar, sesion):
    armar()
    ctx = sesion()
    consulta = ctx.clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]
    a = ctx.conservadoras.obtener_por_codigo("C-A")
    assert a.muestras[0] is muestras_de(consulta)[0]  # un solo objeto por fila dentro de la sesión


def test_una_conservadora_cargada_sigue_respetando_su_capacidad_y_su_precinto(armar, sesion):
    esc = armar()
    ctx = sesion()
    a = ctx.conservadoras.obtener_por_codigo("C-A")
    nueva = Muestra(esc.consulta.emitir_orden(TipoAnalisis("Otro", Decimal("1"), "Sangre", 2.0, 8.0, 24)), "x")
    with pytest.raises(ReglaNegocio, match="precintada"):  # ya tiene precinto: no admite más
        a.agregar_muestra(nueva, "x")


def test_precintar_despues_de_cargar_se_guarda(sesion):
    ctx = sesion()
    hemograma = TipoAnalisis("Hemograma", Decimal("1"), "Sangre", 2.0, 8.0, 24)
    cliente = Cliente("1", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)
    consulta = Consulta(TipoConsulta.CONSULTA, HORA, toby, Veterinario("M", "L", "G", Clinica("C", "")))
    muestra = Muestra(consulta.emitir_orden(hemograma), "x")
    suscribir_trazabilidad(muestra)
    conservadora = Conservadora("C-1", 5, 4.0, 6.0)
    conservadora.agregar_muestra(muestra, "x")
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.clientes.guardar(cliente)
    ctx.consultas.guardar(consulta)
    ctx.conservadoras.guardar(conservadora)
    ctx.conexion.commit()

    ctx2 = sesion()
    cargada = ctx2.conservadoras.obtener_por_codigo("C-1")
    assert cargada.precinto is None
    cargada.precintar("P-9", "Enf. Ruiz", HORA)
    ctx2.conservadoras.guardar(cargada)
    ctx2.conexion.commit()

    assert sesion().conservadoras.obtener_por_codigo("C-1").precinto.numero == "P-9"


def test_listar_las_conservadoras_que_no_estan_en_ningun_remito(armar, sesion):
    esc = armar()
    ctx = esc.ctx
    ctx.conservadoras.guardar(Conservadora("C-LIBRE", 3, 2.0, 8.0))
    ctx.conexion.commit()

    nueva = sesion()
    assert [c.codigo for c in nueva.conservadoras.listar_sin_remito()] == ["C-LIBRE"]
    assert [c.codigo for c in nueva.conservadoras.listar()] == ["C-A", "C-B", "C-LIBRE"]


# --- Remitos ---

def test_remito_abierto_vuelve_con_sus_conservadoras(armar, sesion):
    armar()
    ctx = sesion()
    remito = ctx.remitos.obtener_por_numero("R-001")

    assert remito.estado.nombre == "ABIERTO"
    assert (remito.origen.nombre, remito.destino.nombre) == ("Centro", "Central")
    assert [c.codigo for c in remito.conservadoras] == ["C-A", "C-B"]
    assert remito.tramos == () and remito.recepcion is None


def llevar_a(esc, estado):
    r = esc.remito
    if estado == "ABIERTO":
        return
    r.cerrar()
    if estado == "CERRADO":
        return
    r.despachar("Transportes Sur", "Clínica Centro")
    if estado == "EN_TRANSITO":
        return
    rotas = {"RECIBIDO": (), "RECIBIDO_PARCIAL": (esc.b,), "RECHAZADO": (esc.a, esc.b)}[estado]
    r.registrar_recepcion(recepcion_de(r, esc.laboratorio, rotas))


@pytest.mark.parametrize(
    "estado", ["ABIERTO", "CERRADO", "EN_TRANSITO", "RECIBIDO", "RECIBIDO_PARCIAL", "RECHAZADO"])
def test_cada_estado_del_remito_se_guarda_y_se_recupera(armar, sesion, estado):
    esc = armar()
    llevar_a(esc, estado)
    guardar_todo(esc.ctx, esc)

    cargado = sesion().remitos.obtener_por_numero("R-001")

    assert cargado.estado.nombre == estado
    assert cargado.estado.es_final == (estado in {"RECIBIDO", "RECIBIDO_PARCIAL", "RECHAZADO"})


def test_remito_con_recepcion_parcial_vuelve_completo(armar, sesion):
    esc = armar()
    llevar_a(esc, "EN_TRANSITO")
    esc.remito.registrar_tramo("Clínica Centro", "Central", "Transportes Sur", HORA, HORA, 5.5)
    esc.remito.registrar_tramo("Central", "Central", "Logística Norte", datetime(2026, 6, 1, 12, 0))
    esc.remito.registrar_recepcion(recepcion_de(esc.remito, esc.laboratorio, rotas=(esc.b,)))
    guardar_todo(esc.ctx, esc)

    cargado = sesion().remitos.obtener_por_numero("R-001")

    assert cargado.estado.nombre == "RECIBIDO_PARCIAL"
    assert [(t.orden, t.transportista, t.llegada, t.temperatura) for t in cargado.tramos] == [
        (1, "Transportes Sur", HORA, 5.5), (2, "Logística Norte", None, None)]
    recepcion = cargado.recepcion
    assert (recepcion.responsable, recepcion.laboratorio.nombre) == ("Bioq. Pérez", "Central")
    assert [(d.conservadora.codigo, d.aceptada, d.motivos) for d in recepcion.detalles] == [
        ("C-A", True, ()), ("C-B", False, (MotivoRechazo.PRECINTO_ROTO,))]
    estados = {c.codigo: {m.estado.nombre for m in c.muestras} for c in cargado.conservadoras}
    assert estados == {"C-A": {"RECIBIDA"}, "C-B": {"RECHAZADA"}}


def test_quitar_una_conservadora_del_remito_abierto_se_guarda(armar, sesion):
    esc = armar()
    esc.remito.quitar_conservadora(esc.b)
    guardar_todo(esc.ctx, esc)

    nueva = sesion()
    assert [c.codigo for c in nueva.remitos.obtener_por_numero("R-001").conservadoras] == ["C-A"]
    assert [c.codigo for c in nueva.conservadoras.listar_sin_remito()] == ["C-B"]
    assert len(nueva.conservadoras.obtener_por_codigo("C-B").muestras) == 1  # no se desempaquetó


def test_el_remito_cargado_en_transito_puede_recibirse_en_otra_sesion(armar, sesion):
    esc = armar()
    llevar_a(esc, "EN_TRANSITO")
    guardar_todo(esc.ctx, esc)

    ctx, remito = cargar_remito(sesion)  # otra sesión, como otro caso de uso
    assert remito.estado.nombre == "EN_TRANSITO"
    remito.registrar_recepcion(recepcion_de(remito, remito.destino, rotas=(remito.conservadoras[0],)))
    guardar_cambios(ctx, remito)

    final = sesion().remitos.obtener_por_numero("R-001")
    assert final.estado.nombre == "RECIBIDO_PARCIAL"
    rechazada = final.conservadoras[0].muestras[0]
    assert rechazada.estado.nombre == "RECHAZADA"
    assert [c.nuevo for c in rechazada.historial] == ["EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECHAZADA"]
    assert rechazada.orden.muestra_activa() is None  # lista para re-extraer


def test_un_remito_cargado_cerrado_ya_no_acepta_conservadoras(armar, sesion):
    esc = armar()
    llevar_a(esc, "CERRADO")
    guardar_todo(esc.ctx, esc)

    _, remito = cargar_remito(sesion)
    from app.dominio.excepciones import TransicionInvalida

    with pytest.raises(TransicionInvalida):
        remito.agregar_conservadora(Conservadora("C-Z", 1, 2.0, 8.0))


def test_buscar_y_listar_remitos_por_estado(armar, sesion):
    esc = armar()
    llevar_a(esc, "EN_TRANSITO")
    guardar_todo(esc.ctx, esc)

    nueva = sesion()
    assert nueva.remitos.obtener_por_numero("R-999") is None
    assert [r.numero for r in nueva.remitos.listar_por_estado("EN_TRANSITO")] == ["R-001"]
    assert nueva.remitos.listar_por_estado("ABIERTO") == []


def test_no_se_puede_guardar_un_remito_con_una_conservadora_no_guardada(armar):
    esc = armar()
    esc.remito.agregar_conservadora(Conservadora("C-SUELTA", 1, 2.0, 8.0))
    with pytest.raises(ObjetoNoGuardado, match="conservadora"):
        esc.ctx.remitos.guardar(esc.remito)


def test_el_numero_de_remito_es_unico(armar):
    esc = armar()
    duplicado = RemitoBiologico("R-001", esc.clinica, esc.laboratorio)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        esc.ctx.remitos.guardar(duplicado)

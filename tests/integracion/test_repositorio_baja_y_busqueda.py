from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.conservadora import Conservadora
from app.dominio.consulta import Consulta
from app.dominio.enums import Sexo, TipoConsulta
from app.dominio.especie import Especie
from app.dominio.laboratorio import Laboratorio
from app.dominio.mascota import Mascota
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.remito_biologico import RemitoBiologico
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.turno import Turno
from app.dominio.veterinario import Veterinario
from app.persistencia.identidad import ObjetoNoGuardado


def cliente(dni, nombre, apellido, mascota=None) -> Cliente:
    nuevo = Cliente(dni, nombre, apellido, "", "", "")
    if mascota:
        Mascota(mascota, Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), nuevo)
    return nuevo


@pytest.fixture
def clientes(sesion):
    ctx = sesion()
    for c in (cliente("30111222", "Ana", "Paz", "Toby"), cliente("28444555", "Luis", "Gómez"),
              cliente("33222111", "Marta", "Paz")):
        ctx.clientes.guardar(c)
    ctx.conexion.commit()
    return sesion


# --- Baja lógica persistida ---

def test_la_baja_logica_del_cliente_y_de_la_mascota_se_guarda_y_se_recupera(sesion):
    ctx = sesion()
    ana = cliente("30111222", "Ana", "Paz", "Toby")
    ana.mascotas[0].dar_de_baja()
    ana.dar_de_baja()
    id_ = ctx.clientes.guardar(ana)
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener(id_)

    assert not cargada.activo
    assert not cargada.mascotas[0].activa
    assert cargada.mascotas[0].nombre == "Toby"  # no se borró nada


def test_reactivar_se_guarda(sesion):
    ctx = sesion()
    ana = cliente("30111222", "Ana", "Paz")
    ana.dar_de_baja()
    id_ = ctx.clientes.guardar(ana)
    ana.reactivar()
    ctx.clientes.guardar(ana)
    ctx.conexion.commit()
    assert sesion().clientes.obtener(id_).activo


# --- Búsqueda ---

def test_buscar_por_dni_apellido_o_nombre_sin_distinguir_mayusculas(clientes):
    ctx = clientes()
    assert [c.nombre for c in ctx.clientes.buscar("30111")] == ["Ana"]
    assert [c.nombre for c in ctx.clientes.buscar("paz")] == ["Ana", "Marta"]
    assert [c.apellido for c in ctx.clientes.buscar("LUIS")] == ["Gómez"]
    assert ctx.clientes.buscar("zzz") == []


def test_buscar_sin_texto_devuelve_todos_los_activos(clientes):
    assert len(clientes().clientes.buscar()) == 3


def test_la_busqueda_oculta_a_los_clientes_dados_de_baja_salvo_que_se_pidan(clientes):
    ctx = clientes()
    luis = ctx.clientes.obtener_por_dni("28444555")
    luis.dar_de_baja()
    ctx.clientes.guardar(luis)
    ctx.conexion.commit()

    nueva = clientes()
    assert [c.nombre for c in nueva.clientes.buscar("")] == ["Ana", "Marta"]
    assert len(nueva.clientes.buscar("", incluir_inactivos=True)) == 3


def test_los_comodines_de_sql_se_buscan_como_texto_literal(clientes):
    ctx = clientes()
    assert ctx.clientes.buscar("%") == []  # no es "todos"
    assert ctx.clientes.buscar("_") == []
    assert ctx.clientes.buscar("'; DROP TABLE clientes; --") == []
    assert len(ctx.clientes.buscar("")) == 3  # y la tabla sigue ahí


# --- id asignado por la persistencia ---

def test_la_persistencia_le_asigna_el_id_a_las_entidades_al_guardar_y_al_cargar(sesion):
    ctx = sesion()
    ana = cliente("30111222", "Ana", "Paz", "Toby")
    assert ana.id is None and ana.mascotas[0].id is None
    ctx.clientes.guardar(ana)
    assert ana.id == 1 and ana.mascotas[0].id == 1
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener(ana.id)
    assert (cargada.id, cargada.mascotas[0].id) == (1, 1)


# --- Consultas nuevas ---

@pytest.fixture
def escenario(sesion):
    ctx = sesion()
    ana = cliente("30111222", "Ana", "Paz", "Toby")
    toby = ana.mascotas[0]
    clinica = Clinica("Centro", "")
    veterinario = Veterinario("MP-1", "Laura", "Gómez", clinica)
    laboratorio = Laboratorio("Central", "")
    turno = Turno(datetime(2026, 5, 10, 11, 0), 30, toby)
    veterinario.agregar_turno(turno)
    consulta = Consulta(TipoConsulta.CONSULTA, datetime(2026, 5, 10, 11, 0), toby, veterinario, turno=turno)
    orden = consulta.emitir_orden(TipoAnalisis("Hemograma", Decimal("1"), "Sangre", 2.0, 8.0, 24))
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.clientes.guardar(ana)
    ctx.laboratorios.guardar(laboratorio)
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()
    return SimpleNamespace(sesion=sesion, consulta=consulta, orden=orden, turno=turno,
                           clinica=clinica, laboratorio=laboratorio, ctx=ctx)


def test_encontrar_la_consulta_de_una_orden(escenario):
    nueva = escenario.sesion()
    orden = nueva.ordenes.obtener(escenario.orden.id)
    consulta = nueva.consultas.de_orden(orden)
    assert consulta.id == escenario.consulta.id
    assert consulta.ordenes[0] is orden  # la misma orden dentro de la sesión


def test_saber_si_un_turno_ya_fue_atendido(escenario):
    nueva = escenario.sesion()
    veterinario = nueva.veterinarios.de_turno(escenario.turno.id)
    turno = nueva.veterinarios.turno_por_id(escenario.turno.id)
    assert veterinario.matricula == "MP-1" and turno in veterinario.turnos
    assert nueva.consultas.turno_tiene_consulta(turno)
    assert nueva.veterinarios.de_turno(999) is None


def test_saber_si_una_conservadora_ya_viaja_en_un_remito(escenario):
    ctx = escenario.ctx
    muestra = Muestra(escenario.orden, "Dr. Gómez")
    muestra.suscribir(RegistroTrazabilidad())
    libre, usada = Conservadora("C-LIBRE", 3, 4.0, 6.0), Conservadora("C-USADA", 3, 4.0, 6.0)
    usada.agregar_muestra(muestra, "x")
    usada.precintar("P-1", "x", datetime(2026, 6, 1, 10, 0))
    remito = RemitoBiologico("R-00001", escenario.clinica, escenario.laboratorio)
    remito.agregar_conservadora(usada)
    ctx.consultas.guardar(escenario.consulta)
    ctx.conservadoras.guardar(libre)
    ctx.conservadoras.guardar(usada)
    ctx.remitos.guardar(remito)
    ctx.conexion.commit()

    assert not ctx.conservadoras.esta_en_remito(libre)
    assert ctx.conservadoras.esta_en_remito(usada)
    with pytest.raises(ObjetoNoGuardado):
        ctx.conservadoras.esta_en_remito(Conservadora("C-NUEVA", 1, 2.0, 8.0))


def test_numeros_de_remito_correlativos_y_listado(escenario):
    ctx = escenario.ctx
    assert ctx.remitos.proximo_numero() == "R-00001"
    ctx.remitos.guardar(RemitoBiologico("R-00001", escenario.clinica, escenario.laboratorio))
    ctx.remitos.guardar(RemitoBiologico(ctx.remitos.proximo_numero(), escenario.clinica, escenario.laboratorio))
    ctx.conexion.commit()

    assert [r.numero for r in ctx.remitos.listar()] == ["R-00002", "R-00001"]  # el más nuevo primero
    assert escenario.sesion().remitos.proximo_numero() == "R-00003"

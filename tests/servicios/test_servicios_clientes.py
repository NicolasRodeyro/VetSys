from datetime import date

import pytest

from app.dominio.enums import Sexo
from app.dominio.excepciones import ReglaNegocio
from app.servicios import clientes
from app.servicios.excepciones import EntradaInvalida, NoEncontrado
from tests.servicios.conftest import mascota

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


def cantidad_de_clientes(cx) -> int:
    return cx.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]


# --- Alta, consulta y búsqueda ---

def test_alta_de_cliente_normaliza_los_datos_y_lo_guarda(cx):
    cliente = clientes.alta_cliente("40.123.456", "  sofía   ", " Ramírez ", "351 555-9999",
                                    " Sofia@Mail.com ", "  Calle  7 ")

    assert cliente.id is not None
    assert (cliente.dni, cliente.nombre, cliente.apellido) == ("40123456", "sofía", "Ramírez")
    assert (cliente.telefono, cliente.email, cliente.direccion) == ("351 555-9999", "sofia@mail.com", "Calle 7")
    assert clientes.obtener_cliente(cliente.id).dni == "40123456"  # quedó en la base


def test_no_se_pueden_repetir_dnis(cx):
    antes = cantidad_de_clientes(cx)
    with pytest.raises(ReglaNegocio, match="Ya existe un cliente con el DNI 30111222"):
        clientes.alta_cliente("30.111.222", "Otra", "Persona")
    assert cantidad_de_clientes(cx) == antes


@pytest.mark.parametrize("datos, mensaje", [
    (dict(dni="123", nombre="Ana", apellido="Paz"), "DNI"),
    (dict(dni="40123456", nombre="  ", apellido="Paz"), "nombre es obligatorio"),
    (dict(dni="40123456", nombre="Ana", apellido=""), "apellido es obligatorio"),
    (dict(dni="40123456", nombre="Ana", apellido="Paz", email="mal"), "email"),
    (dict(dni="40123456", nombre="Ana", apellido="Paz", telefono="abc"), "teléfono"),
])
def test_una_entrada_invalida_se_rechaza_sin_guardar_nada(cx, datos, mensaje):
    antes = cantidad_de_clientes(cx)
    with pytest.raises(EntradaInvalida, match=mensaje):
        clientes.alta_cliente(**datos)
    assert cantidad_de_clientes(cx) == antes


def test_un_dato_con_sql_se_guarda_como_texto_sin_danar_la_base(cx):
    cliente = clientes.alta_cliente("40123456", "Robert'); DROP TABLE clientes;--", "Tables")
    assert clientes.obtener_cliente(cliente.id).nombre == "Robert'); DROP TABLE clientes;--"
    assert cantidad_de_clientes(cx) == 11  # la tabla sigue ahí, con los 10 del seed más este


def test_obtener_un_cliente_que_no_existe(cx):
    with pytest.raises(NoEncontrado, match="el cliente"):
        clientes.obtener_cliente(9999)


def test_buscar_clientes(cx):
    assert [c.apellido for c in clientes.buscar_clientes("paz")] == ["Paz"]
    assert [c.nombre for c in clientes.buscar_clientes("30.111")] == []  # la búsqueda es literal, no normaliza
    assert [c.nombre for c in clientes.buscar_clientes("30111")] == ["Ana"]
    assert len(clientes.buscar_clientes()) == 10


# --- Modificación ---

def test_modificar_cliente_cambia_solo_lo_que_se_pasa(cx):
    ana = clientes.buscar_clientes("30111222")[0]
    modificada = clientes.modificar_cliente(ana.id, telefono="351 000-1111", email="nuevo@mail.com")

    assert (modificada.telefono, modificada.email) == ("351 000-1111", "nuevo@mail.com")
    recargada = clientes.obtener_cliente(ana.id)
    assert (recargada.nombre, recargada.apellido, recargada.direccion) == ("Ana", "Paz", "Calle 1 N° 100")
    assert recargada.telefono == "351 000-1111"


def test_modificar_el_dni_no_puede_pisar_el_de_otro_cliente(cx):
    ana = clientes.buscar_clientes("30111222")[0]
    with pytest.raises(ReglaNegocio, match="Ya existe otro cliente"):
        clientes.modificar_cliente(ana.id, dni="28444555")
    assert clientes.modificar_cliente(ana.id, dni="30111222").dni == "30111222"  # el propio no molesta
    assert clientes.obtener_cliente(ana.id).dni == "30111222"


def test_modificar_con_datos_invalidos_no_cambia_nada(cx):
    ana = clientes.buscar_clientes("30111222")[0]
    with pytest.raises(EntradaInvalida):
        clientes.modificar_cliente(ana.id, nombre="Ana Lucía", email="mal")
    assert clientes.obtener_cliente(ana.id).nombre == "Ana"


# --- Baja lógica ---

def test_no_se_da_de_baja_a_un_cliente_con_mascotas_activas(cx):
    ana = clientes.buscar_clientes("30111222")[0]
    with pytest.raises(ReglaNegocio, match="mascotas activas"):
        clientes.dar_de_baja_cliente(ana.id)
    assert clientes.obtener_cliente(ana.id).activo


def test_baja_logica_del_cliente_despues_de_sus_mascotas_y_reactivacion(cx):
    ana = clientes.buscar_clientes("30111222")[0]
    for m in ana.mascotas:
        clientes.dar_de_baja_mascota(m.id)
    clientes.dar_de_baja_cliente(ana.id)

    assert ana.id not in [c.id for c in clientes.buscar_clientes()]  # ya no aparece...
    assert ana.id in [c.id for c in clientes.buscar_clientes(incluir_inactivos=True)]  # ...pero no se borró
    assert len(clientes.obtener_cliente(ana.id).mascotas) == 2  # sus mascotas y su historia siguen

    clientes.reactivar_cliente(ana.id)
    assert clientes.obtener_cliente(ana.id).activo


# --- Mascotas ---

def test_alta_de_mascota(cx):
    ana = clientes.buscar_clientes("30111222")[0]
    nueva = clientes.alta_mascota(ana.id, "  Rocky ", "Perro", "macho", date(2026, 5, 1))

    assert nueva.id is not None and nueva.nombre == "Rocky" and nueva.sexo is Sexo.MACHO
    recargada = clientes.obtener_mascota(nueva.id)
    assert recargada.responsable.dni == "30111222" and recargada.especie.nombre == "Perro"
    assert len(clientes.obtener_cliente(ana.id).mascotas) == 3


@pytest.mark.parametrize("cambios, error, mensaje", [
    (dict(especie="Dragón"), NoEncontrado, "la especie"),
    (dict(sexo="x"), EntradaInvalida, "sexo"),
    (dict(nombre=""), EntradaInvalida, "nombre de la mascota"),
    (dict(fecha_nacimiento=date(2027, 1, 1)), EntradaInvalida, "no puede ser futura"),
])
def test_alta_de_mascota_con_datos_invalidos(cx, cambios, error, mensaje):
    ana = clientes.buscar_clientes("30111222")[0]
    datos = dict(nombre="Rocky", especie="Perro", sexo="MACHO", fecha_nacimiento=date(2026, 5, 1))
    datos.update(cambios)
    with pytest.raises(error, match=mensaje):
        clientes.alta_mascota(ana.id, **datos)
    assert len(clientes.obtener_cliente(ana.id).mascotas) == 2


def test_no_se_le_agregan_mascotas_a_un_cliente_dado_de_baja(cx):
    marta = clientes.buscar_clientes("33222111")[0]
    clientes.dar_de_baja_mascota(marta.mascotas[0].id)
    clientes.dar_de_baja_cliente(marta.id)
    with pytest.raises(ReglaNegocio, match="dado de baja"):
        clientes.alta_mascota(marta.id, "Nueva", "Gato", "HEMBRA", date(2026, 5, 1))


def test_modificar_y_dar_de_baja_una_mascota(cx):
    toby = mascota("30111222", "Toby")
    clientes.modificar_mascota(toby.id, nombre="Tobías", sexo="HEMBRA")
    assert (clientes.obtener_mascota(toby.id).nombre, clientes.obtener_mascota(toby.id).sexo) == ("Tobías", Sexo.HEMBRA)

    clientes.dar_de_baja_mascota(toby.id)
    assert not clientes.obtener_mascota(toby.id).activa
    clientes.reactivar_mascota(toby.id)
    assert clientes.obtener_mascota(toby.id).activa


def test_no_se_reactiva_una_mascota_si_su_responsable_esta_de_baja(cx):
    marta = clientes.buscar_clientes("33222111")[0]
    luna = marta.mascotas[0]
    clientes.dar_de_baja_mascota(luna.id)
    clientes.dar_de_baja_cliente(marta.id)
    with pytest.raises(ReglaNegocio, match="responsable está dado de baja"):
        clientes.reactivar_mascota(luna.id)


# --- Historia clínica y vacunas ---

def test_actualizar_la_historia_clinica(cx):
    toby = mascota("30111222", "Toby")
    clientes.actualizar_historia_clinica(toby.id, alergias="Polen", antecedentes="Operado")
    historia = clientes.obtener_mascota(toby.id).historia_clinica
    assert (historia.alergias, historia.antecedentes) == ("Polen", "Operado")

    clientes.actualizar_historia_clinica(toby.id, alergias="")  # vaciar un dato; el otro no se toca
    historia = clientes.obtener_mascota(toby.id).historia_clinica
    assert (historia.alergias, historia.antecedentes) == ("", "Operado")


def test_aplicar_una_vacuna_la_saca_de_las_pendientes(cx):
    luna = mascota("33222111", "Luna")  # gata nacida el 01/07/2026: a 4 meses le corresponden las 3
    assert {v.nombre for v in clientes.vacunas_pendientes(luna.id)} == {"Triple felina", "Antirrabica", "Leucemia felina"}

    clientes.aplicar_vacuna(luna.id, "triple felina")  # sin distinguir mayúsculas; por defecto, hoy
    assert {v.nombre for v in clientes.vacunas_pendientes(luna.id)} == {"Antirrabica", "Leucemia felina"}
    aplicada = clientes.obtener_mascota(luna.id).historia_clinica.vacunas_aplicadas[0]
    assert (aplicada.vacuna.nombre, aplicada.fecha) == ("Triple felina", date(2026, 11, 2))


@pytest.mark.parametrize("vacuna, fecha, error, mensaje", [
    ("Rabia canina", None, NoEncontrado, "no está en el esquema de Gato"),
    ("Triple felina", date(2026, 6, 1), EntradaInvalida, "anterior al nacimiento"),
    ("Triple felina", date(2026, 12, 1), EntradaInvalida, "no puede ser futura"),
    ("", None, EntradaInvalida, "vacuna es obligatorio"),
])
def test_aplicar_una_vacuna_con_datos_invalidos(cx, vacuna, fecha, error, mensaje):
    luna = mascota("33222111", "Luna")
    with pytest.raises(error, match=mensaje):
        clientes.aplicar_vacuna(luna.id, vacuna, fecha)
    assert clientes.obtener_mascota(luna.id).historia_clinica.vacunas_aplicadas == ()


def test_las_vacunas_pendientes_se_pueden_consultar_en_otra_fecha(cx):
    luna = mascota("33222111", "Luna")
    # A los 2 meses y medio solo le corresponde la Triple felina (2 meses).
    assert [v.nombre for v in clientes.vacunas_pendientes(luna.id, date(2026, 9, 15))] == ["Triple felina"]

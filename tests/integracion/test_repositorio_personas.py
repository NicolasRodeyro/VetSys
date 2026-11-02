from datetime import date

import pytest

from app.dominio.cliente import Cliente
from app.dominio.enums import Sexo
from app.dominio.especie import Especie, VacunaObligatoria
from app.dominio.mascota import Mascota
from app.persistencia.identidad import ObjetoNoGuardado

SEXTUPLE = VacunaObligatoria("Sextuple", 2, 12)
ANTIRRABICA = VacunaObligatoria("Antirrabica", 3, 12)
UNICA = VacunaObligatoria("Unica dosis", 1)  # sin refuerzo


def un_perro() -> Especie:
    especie = Especie("Perro")
    for vacuna in (SEXTUPLE, ANTIRRABICA, UNICA):
        especie.agregar_vacuna_obligatoria(vacuna)
    return especie


def cliente_con_toby(especie=None) -> Cliente:
    cliente = Cliente("30111222", "Ana", "Paz", "351-555-0000", "ana@mail.com", "Calle 1")
    Mascota("Toby", especie or un_perro(), Sexo.MACHO, date(2026, 1, 10), cliente)
    return cliente


def guardar_y_confirmar(ctx, *objetos) -> list[int]:
    ids = [ctx.clientes.guardar(o) for o in objetos]
    ctx.conexion.commit()
    return ids


# --- Especies ---

def test_especie_vuelve_con_su_esquema_de_vacunas(sesion):
    ctx = sesion()
    id_ = ctx.especies.guardar(un_perro())
    ctx.conexion.commit()

    cargada = sesion().especies.obtener(id_)

    assert cargada.nombre == "Perro"
    assert cargada.esquema_vacunas == (SEXTUPLE, ANTIRRABICA, UNICA)  # mismo orden y valores


def test_guardar_dos_veces_la_misma_especie_no_duplica_vacunas(sesion):
    ctx = sesion()
    especie = un_perro()
    ctx.especies.guardar(especie)
    ctx.especies.guardar(especie)
    assert ctx.conexion.execute("SELECT COUNT(*) FROM vacunas_obligatorias").fetchone()[0] == 3
    assert ctx.conexion.execute("SELECT COUNT(*) FROM especies").fetchone()[0] == 1


def test_buscar_especie_por_nombre_y_listar(sesion):
    ctx = sesion()
    ctx.especies.guardar(un_perro())
    ctx.especies.guardar(Especie("Gato"))
    ctx.conexion.commit()

    nueva = sesion()
    assert nueva.especies.obtener_por_nombre("Gato").nombre == "Gato"
    assert nueva.especies.obtener_por_nombre("Dragón") is None
    assert [e.nombre for e in nueva.especies.listar()] == ["Gato", "Perro"]


# --- Clientes, mascotas e historia clínica ---

def test_cliente_vuelve_con_sus_datos(sesion):
    ctx = sesion()
    (id_,) = guardar_y_confirmar(ctx, cliente_con_toby())

    cargado = sesion().clientes.obtener(id_)

    assert (cargado.dni, cargado.nombre, cargado.apellido) == ("30111222", "Ana", "Paz")
    assert (cargado.telefono, cargado.email, cargado.direccion) == ("351-555-0000", "ana@mail.com", "Calle 1")


def test_la_mascota_vuelve_con_su_responsable_y_su_historia(sesion):
    cliente = cliente_con_toby()
    historia = cliente.mascotas[0].historia_clinica
    historia.alergias = "Penicilina"
    historia.antecedentes = "Operado en 2026"
    historia.registrar_vacuna(SEXTUPLE, date(2026, 3, 10))
    ctx = sesion()
    (id_,) = guardar_y_confirmar(ctx, cliente)

    cargado = sesion().clientes.obtener(id_)

    (toby,) = cargado.mascotas
    assert (toby.nombre, toby.sexo, toby.fecha_nacimiento) == ("Toby", Sexo.MACHO, date(2026, 1, 10))
    assert toby.responsable is cargado  # el mismo objeto, no una copia
    assert toby.especie.nombre == "Perro"
    assert toby.historia_clinica.alergias == "Penicilina"
    assert toby.historia_clinica.antecedentes == "Operado en 2026"
    assert [(a.vacuna, a.fecha) for a in toby.historia_clinica.vacunas_aplicadas] == [(SEXTUPLE, date(2026, 3, 10))]


def test_las_vacunas_pendientes_dan_lo_mismo_antes_y_despues_de_guardar(sesion):
    cliente = cliente_con_toby()
    historia = cliente.mascotas[0].historia_clinica
    historia.registrar_vacuna(SEXTUPLE, date(2026, 3, 10))
    esperadas = historia.vacunas_pendientes(date(2026, 5, 10))
    assert esperadas == [ANTIRRABICA, UNICA]
    (id_,) = guardar_y_confirmar(sesion(), cliente)

    recargada = sesion().clientes.obtener(id_).mascotas[0].historia_clinica

    assert recargada.vacunas_pendientes(date(2026, 5, 10)) == esperadas


def test_guardar_dos_veces_no_duplica_filas(sesion):
    ctx = sesion()
    cliente = cliente_con_toby()
    cliente.mascotas[0].historia_clinica.registrar_vacuna(SEXTUPLE, date(2026, 3, 10))
    ctx.clientes.guardar(cliente)
    ctx.clientes.guardar(cliente)
    for tabla, esperadas in [("clientes", 1), ("mascotas", 1), ("historias_clinicas", 1), ("vacunas_aplicadas", 1)]:
        assert ctx.conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == esperadas


def test_cambios_posteriores_se_guardan_sin_duplicar_lo_anterior(sesion):
    ctx = sesion()
    cliente = cliente_con_toby()
    (id_,) = guardar_y_confirmar(ctx, cliente)

    cliente.telefono = "351-999-9999"
    toby = cliente.mascotas[0]
    toby.historia_clinica.alergias = "Polen"
    toby.historia_clinica.registrar_vacuna(SEXTUPLE, date(2026, 3, 10))
    Mascota("Mimi", Especie("Gato"), Sexo.HEMBRA, date(2025, 5, 5), cliente)
    toby.historia_clinica.registrar_vacuna(ANTIRRABICA, date(2026, 4, 10))
    guardar_y_confirmar(ctx, cliente)

    cargado = sesion().clientes.obtener(id_)
    assert cargado.telefono == "351-999-9999"
    assert [m.nombre for m in cargado.mascotas] == ["Toby", "Mimi"]
    assert cargado.mascotas[0].historia_clinica.alergias == "Polen"
    assert [a.vacuna.nombre for a in cargado.mascotas[0].historia_clinica.vacunas_aplicadas] == [
        "Sextuple", "Antirrabica"]


def test_cargar_dos_veces_devuelve_el_mismo_objeto(sesion):
    (id_,) = guardar_y_confirmar(sesion(), cliente_con_toby())
    ctx = sesion()
    assert ctx.clientes.obtener(id_) is ctx.clientes.obtener(id_)
    assert ctx.clientes.obtener_por_dni("30111222") is ctx.clientes.obtener(id_)


def test_una_mascota_nueva_comparte_la_especie_ya_guardada(sesion):
    perro = un_perro()
    cliente = cliente_con_toby(perro)
    Mascota("Rex", perro, Sexo.MACHO, date(2025, 1, 1), cliente)
    ctx = sesion()
    guardar_y_confirmar(ctx, cliente)
    assert ctx.conexion.execute("SELECT COUNT(*) FROM especies").fetchone()[0] == 1


def test_buscar_cliente_por_dni_y_listar(sesion):
    ctx = sesion()
    guardar_y_confirmar(ctx, cliente_con_toby())
    otro = Cliente("28444555", "Luis", "Gómez", "", "", "")
    guardar_y_confirmar(ctx, otro)

    nueva = sesion()
    assert nueva.clientes.obtener_por_dni("28444555").apellido == "Gómez"
    assert nueva.clientes.obtener_por_dni("00000000") is None
    assert [c.apellido for c in nueva.clientes.listar()] == ["Gómez", "Paz"]


def test_cargar_una_mascota_por_id_trae_a_su_cliente(sesion):
    ctx = sesion()
    guardar_y_confirmar(ctx, cliente_con_toby())
    mascota_id = ctx.conexion.execute("SELECT id FROM mascotas").fetchone()[0]

    mascota = sesion().clientes.mascota_por_id(mascota_id)

    assert mascota.nombre == "Toby"
    assert mascota.responsable.dni == "30111222"


def test_obtener_algo_que_no_existe_devuelve_none(sesion):
    ctx = sesion()
    assert ctx.clientes.obtener(999) is None
    assert ctx.especies.obtener(999) is None
    assert ctx.clientes.mascota_por_id(999) is None


def test_no_se_puede_guardar_una_vacuna_que_no_esta_guardada(sesion):
    cliente = cliente_con_toby()
    ajena = VacunaObligatoria("De otra especie", 1)
    cliente.mascotas[0].historia_clinica.registrar_vacuna(ajena, date(2026, 3, 1))
    with pytest.raises(ObjetoNoGuardado, match="vacuna"):
        sesion().clientes.guardar(cliente)


# --- Con los datos de prueba (seed.sql) ---

def test_los_clientes_del_seed_se_cargan_como_objetos_del_dominio(con_seed, sesion):
    ctx = sesion()
    clientes = ctx.clientes.listar()
    assert len(clientes) == 10
    assert all(m.responsable is c for c in clientes for m in c.mascotas)  # todas con su responsable

    ana = ctx.clientes.obtener_por_dni("30111222")
    assert sorted(m.nombre for m in ana.mascotas) == ["Mimi", "Toby"]


def test_las_vacunas_pendientes_se_calculan_con_los_datos_del_seed(con_seed, sesion):
    ctx = sesion()
    ana = ctx.clientes.obtener_por_dni("30111222")
    toby = next(m for m in ana.mascotas if m.nombre == "Toby")
    # Toby nació el 12/08/2025 y tiene Sextuple y Antirrabica de oct/nov 2025:
    # a fines de 2026 ya venció el refuerzo anual de las dos, y le falta la tos de las perreras.
    pendientes = {v.nombre for v in toby.historia_clinica.vacunas_pendientes(date(2026, 12, 15))}
    assert pendientes == {"Sextuple", "Antirrabica", "Tos de las perreras"}

    rex = ctx.clientes.obtener_por_dni("28444555").mascotas[0]
    assert rex.historia_clinica.alergias == "Alergia a la penicilina"
    assert rex.historia_clinica.vacunas_pendientes(date(2026, 12, 15)) == []  # vacunado en abril 2026

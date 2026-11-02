from datetime import date, datetime
from decimal import Decimal

import pytest

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.consulta import Consulta
from app.dominio.enums import EstadoTurno, Prioridad, Sexo, TipoConsulta
from app.dominio.especie import Especie, VacunaObligatoria
from app.dominio.excepciones import ReglaNegocio
from app.dominio.laboratorio import Laboratorio
from app.dominio.mascota import Mascota
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.turno import Turno
from app.dominio.veterinario import Veterinario
from app.persistencia.identidad import ObjetoNoGuardado

SEXTUPLE = VacunaObligatoria("Sextuple", 2, 12)
ANTIRRABICA = VacunaObligatoria("Antirrabica", 3, 12)
FECHA_CONSULTA = datetime(2026, 5, 10, 11, 0)  # Toby tiene 4 meses: le corresponden las dos vacunas


def hemograma() -> TipoAnalisis:
    return TipoAnalisis("Hemograma", Decimal("12500.50"), "Sangre", 2.0, 8.0, 24)


@pytest.fixture
def escenario(sesion):
    """Cliente con Toby, una clínica, un veterinario y un catálogo, todo guardado."""
    ctx = sesion()
    perro = Especie("Perro")
    perro.agregar_vacuna_obligatoria(SEXTUPLE)
    perro.agregar_vacuna_obligatoria(ANTIRRABICA)
    cliente = Cliente("30111222", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", perro, Sexo.MACHO, date(2026, 1, 10), cliente)
    veterinario = Veterinario("MP-1", "Laura", "Gómez", Clinica("Centro", "Av. Colón 100"))
    tipo = hemograma()

    ctx.clientes.guardar(cliente)
    ctx.veterinarios.guardar(veterinario)
    ctx.tipos_analisis.guardar(tipo)
    ctx.conexion.commit()
    return ctx, cliente, toby, veterinario, tipo


# --- Clínicas, laboratorios y catálogo de análisis ---

def test_clinicas_y_laboratorios_se_guardan_y_se_listan(sesion):
    ctx = sesion()
    ctx.clinicas.guardar(Clinica("Norte", "Av. Norte 1"))
    ctx.clinicas.guardar(Clinica("Centro", "Av. Colón 100"))
    ctx.laboratorios.guardar(Laboratorio("Central", "Bv. Illia 1"))
    ctx.conexion.commit()

    nueva = sesion()
    assert [c.nombre for c in nueva.clinicas.listar()] == ["Centro", "Norte"]
    assert nueva.clinicas.obtener_por_nombre("Norte").direccion == "Av. Norte 1"
    assert nueva.laboratorios.listar()[0].nombre == "Central"


def test_tipo_de_analisis_conserva_el_precio_decimal_exacto(sesion):
    ctx = sesion()
    id_ = ctx.tipos_analisis.guardar(hemograma())
    ctx.conexion.commit()

    cargado = sesion().tipos_analisis.obtener(id_)

    assert cargado == hemograma()  # mismos valores
    assert isinstance(cargado.precio, Decimal) and cargado.precio == Decimal("12500.50")
    assert sesion().tipos_analisis.obtener_por_nombre("Hemograma") is not None


# --- Veterinarios y su agenda ---

def test_veterinario_vuelve_con_su_clinica(escenario, sesion):
    veterinario = sesion().veterinarios.obtener_por_matricula("MP-1")
    assert (veterinario.nombre, veterinario.apellido) == ("Laura", "Gómez")
    assert veterinario.clinica.nombre == "Centro"


def test_los_turnos_guardados_siguen_bloqueando_el_horario_al_recargar(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    veterinario.agregar_turno(Turno(datetime(2026, 6, 1, 10, 0), 30, toby))
    ctx.veterinarios.guardar(veterinario)
    ctx.conexion.commit()

    recargado = sesion().veterinarios.obtener_por_matricula("MP-1")

    assert len(recargado.turnos) == 1
    solapado = Turno(datetime(2026, 6, 1, 10, 15), 30, recargado.turnos[0].mascota)
    with pytest.raises(ReglaNegocio, match="se superpone"):
        recargado.agregar_turno(solapado)  # la regla de agenda sigue funcionando después de cargar
    recargado.agregar_turno(Turno(datetime(2026, 6, 1, 10, 30), 30, solapado.mascota))  # contiguo: ok


def test_un_turno_cancelado_vuelve_cancelado_y_libera_el_horario(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    turno = Turno(datetime(2026, 6, 1, 10, 0), 30, toby)
    veterinario.agregar_turno(turno)
    ctx.veterinarios.guardar(veterinario)
    turno.cancelar()
    ctx.veterinarios.guardar(veterinario)
    ctx.conexion.commit()

    recargado = sesion().veterinarios.obtener_por_matricula("MP-1")

    assert recargado.turnos[0].estado is EstadoTurno.CANCELADO
    recargado.agregar_turno(Turno(datetime(2026, 6, 1, 10, 0), 30, recargado.turnos[0].mascota))


def test_sin_agenda_el_veterinario_no_trae_turnos_y_despues_se_puede_pedir(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    veterinario.agregar_turno(Turno(datetime(2026, 6, 1, 10, 0), 30, toby))
    ctx.veterinarios.guardar(veterinario)
    ctx.conexion.commit()

    nuevo = sesion()
    sin_agenda = nuevo.veterinarios.obtener_por_matricula("MP-1", con_agenda=False)
    assert sin_agenda.turnos == ()
    con_agenda = nuevo.veterinarios.obtener_por_matricula("MP-1")  # ahora sí, y es el mismo objeto
    assert con_agenda is sin_agenda and len(con_agenda.turnos) == 1


def test_guardar_un_veterinario_sin_agenda_cargada_no_borra_sus_turnos(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    veterinario.agregar_turno(Turno(datetime(2026, 6, 1, 10, 0), 30, toby))
    ctx.veterinarios.guardar(veterinario)
    ctx.conexion.commit()

    nuevo = sesion()
    vet = nuevo.veterinarios.obtener_por_matricula("MP-1", con_agenda=False)
    vet.nombre = "Laura María"
    nuevo.veterinarios.guardar(vet)
    nuevo.conexion.commit()

    assert nuevo.conexion.execute("SELECT COUNT(*) FROM turnos").fetchone()[0] == 1


def test_listar_los_veterinarios_de_una_clinica(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    ctx.veterinarios.guardar(Veterinario("MP-2", "Marcos", "Ruiz", veterinario.clinica))
    ctx.conexion.commit()

    nueva = sesion()
    clinica = nueva.clinicas.obtener_por_nombre("Centro")
    assert [v.apellido for v in nueva.veterinarios.listar_de_clinica(clinica)] == ["Gómez", "Ruiz"]


# --- Consultas ---

def test_una_urgencia_sin_turno_se_guarda_y_se_carga(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    urgencia = Consulta(TipoConsulta.URGENCIA, FECHA_CONSULTA, toby, veterinario,
                        diagnostico="Intoxicación", tratamiento="Carbón activado")
    toby.historia_clinica.registrar_consulta(urgencia)
    ctx.consultas.guardar(urgencia)
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]

    assert cargada.tipo is TipoConsulta.URGENCIA
    assert cargada.turno is None
    assert (cargada.diagnostico, cargada.tratamiento) == ("Intoxicación", "Carbón activado")
    assert cargada.fecha_hora == FECHA_CONSULTA
    assert cargada.veterinario.matricula == "MP-1"


def test_las_advertencias_de_vacunas_se_guardan_y_no_se_recalculan_al_cargar(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    toby.historia_clinica.registrar_consulta(consulta)  # advierte las dos vacunas pendientes
    assert len(consulta.advertencias) == 2
    ctx.consultas.guardar(consulta)
    ctx.consultas.guardar(consulta)  # guardar de nuevo no duplica advertencias
    ctx.conexion.commit()

    historia = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica
    cargada = historia.consultas[0]

    assert cargada.advertencias == consulta.advertencias == (
        "Vacuna pendiente: Sextuple", "Vacuna pendiente: Antirrabica")
    assert len(historia.consultas) == 1


def test_consulta_con_turno_vuelve_con_su_turno(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    turno = Turno(datetime(2026, 5, 10, 11, 0), 30, toby)
    veterinario.agregar_turno(turno)
    consulta = Consulta(TipoConsulta.CONTROL, FECHA_CONSULTA, toby, veterinario, turno=turno)
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]

    assert cargada.turno is not None
    assert cargada.turno.inicio == datetime(2026, 5, 10, 11, 0)
    assert cargada.turno.mascota is cargada.mascota


def test_obtener_una_consulta_por_id_devuelve_la_misma_de_la_historia(escenario, sesion):
    ctx, cliente, toby, veterinario, _ = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    toby.historia_clinica.registrar_consulta(consulta)
    id_ = ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    nueva = sesion()
    por_id = nueva.consultas.obtener(id_)
    assert por_id is nueva.clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]
    assert nueva.consultas.obtener(999) is None


def test_las_ordenes_de_derivacion_vuelven_con_su_tipo_de_analisis(escenario, sesion):
    ctx, cliente, toby, veterinario, tipo = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    consulta.emitir_orden(tipo, Prioridad.URGENTE)
    consulta.emitir_orden(tipo)
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]

    assert [o.prioridad for o in cargada.ordenes] == [Prioridad.URGENTE, Prioridad.NORMAL]
    assert cargada.ordenes[0].tipo_analisis == tipo
    assert cargada.ordenes[0].tipo_analisis is cargada.ordenes[1].tipo_analisis  # mismo catálogo


def test_el_comprobante_se_guarda_y_vuelve_con_sus_items_y_su_total(escenario, sesion):
    ctx, cliente, toby, veterinario, tipo = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    consulta.emitir_orden(tipo)
    toby.historia_clinica.registrar_consulta(consulta)
    consulta.cerrar(Decimal("3000.25"), datetime(2026, 5, 10, 12, 0))
    ctx.consultas.guardar(consulta)
    ctx.consultas.guardar(consulta)  # el comprobante no se duplica
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]

    assert cargada.cerrada
    comprobante = cargada.comprobante
    assert [(i.descripcion, i.monto, i.es_laboratorio) for i in comprobante.items] == [
        ("Consulta", Decimal("3000.25"), False), ("Hemograma", Decimal("12500.50"), True)]
    assert comprobante.total == Decimal("15500.75")
    assert comprobante.cliente.dni == "30111222"
    assert comprobante.fecha_hora == datetime(2026, 5, 10, 12, 0)
    with pytest.raises(ReglaNegocio, match="ya está cerrada"):
        cargada.cerrar(Decimal("1"), datetime(2026, 5, 11, 9, 0))


def test_el_comprobante_conserva_el_precio_de_cuando_se_emitio(escenario, sesion):
    ctx, cliente, toby, veterinario, tipo = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    consulta.emitir_orden(tipo)
    toby.historia_clinica.registrar_consulta(consulta)
    consulta.cerrar(Decimal("3000"), datetime(2026, 5, 10, 12, 0))
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    # Sube el precio del análisis en el catálogo.
    ctx.conexion.execute("UPDATE tipos_analisis SET precio = '99999'")
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]
    assert cargada.ordenes[0].tipo_analisis.precio == Decimal("99999")  # el catálogo cambió...
    assert cargada.comprobante.total == Decimal("15500.50")  # ...pero lo ya facturado no (3000 + 12500.50)


def test_una_consulta_cerrada_cargada_no_admite_nuevas_ordenes(escenario, sesion):
    ctx, cliente, toby, veterinario, tipo = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    toby.historia_clinica.registrar_consulta(consulta)
    consulta.cerrar(Decimal("3000"), datetime(2026, 5, 10, 12, 0))
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]
    with pytest.raises(ReglaNegocio, match="no admite nuevas órdenes"):
        cargada.emitir_orden(tipo)


def test_una_consulta_se_puede_actualizar_y_cerrar_despues(escenario, sesion):
    ctx, cliente, toby, veterinario, tipo = escenario
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    consulta.diagnostico = "Gastroenteritis"
    consulta.emitir_orden(tipo)
    consulta.cerrar(Decimal("3000"), datetime(2026, 5, 10, 12, 0))
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    cargada = sesion().clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]
    assert cargada.diagnostico == "Gastroenteritis"
    assert len(cargada.ordenes) == 1 and cargada.cerrada
    assert ctx.conexion.execute("SELECT COUNT(*) FROM consultas").fetchone()[0] == 1


def test_no_se_puede_guardar_una_consulta_de_una_mascota_no_guardada(sesion):
    ctx = sesion()
    especie = Especie("Perro")
    cliente = Cliente("1", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", especie, Sexo.MACHO, date(2026, 1, 10), cliente)
    veterinario = Veterinario("MP-1", "Laura", "Gómez", Clinica("Centro", ""))
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA_CONSULTA, toby, veterinario)
    with pytest.raises(ObjetoNoGuardado, match="mascota"):
        ctx.consultas.guardar(consulta)

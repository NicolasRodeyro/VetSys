from datetime import date, datetime
from decimal import Decimal

import pytest

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.consulta import Consulta
from app.dominio.enums import Sexo, TipoConsulta
from app.dominio.especie import Especie
from app.dominio.mascota import Mascota
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import RegistroTrazabilidad
from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.veterinario import Veterinario
from app.persistencia.identidad import ObjetoNoGuardado

FECHA = datetime(2026, 6, 2, 9, 0)
HEMATOCRITO = ValorResultado("Hematocrito", 41.0, "%", 37.0, 55.0)
LEUCOCITOS = ValorResultado("Leucocitos", 25.0, "mil/µl", 6.0, 17.0)  # alto
UREA = ValorResultado("Urea", 40.0, "mg/dl", ref_max=60.0)  # solo tiene máximo


@pytest.fixture
def recibida(sesion):
    """Una muestra Recibida, guardada junto con su orden. Devuelve (ctx, muestra)."""
    ctx = sesion()
    cliente = Cliente("1", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA, toby, Veterinario("M", "L", "G", Clinica("C", "")))
    orden = consulta.emitir_orden(TipoAnalisis("Hemograma", Decimal("12500"), "Sangre", 2.0, 8.0, 24))
    muestra = Muestra(orden, "Dr. Gómez")
    muestra.suscribir(RegistroTrazabilidad())
    muestra.empaquetar("x")
    muestra.despachar("x")
    muestra.recibir(True, "x")
    toby.historia_clinica.registrar_consulta(consulta)
    ctx.clientes.guardar(cliente)
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()
    return ctx, muestra


def test_el_resultado_se_guarda_y_vuelve_con_sus_valores(recibida, sesion):
    ctx, muestra = recibida
    resultado = ResultadoAnalisis(muestra, "Bioq. Pérez", FECHA, [HEMATOCRITO, LEUCOCITOS, UREA],
                                  observaciones="Leucocitosis", ubicacion="Laboratorio")
    ctx.ordenes.guardar(muestra.orden)  # guarda la muestra, ya Analizada
    ctx.resultados.guardar(resultado)
    ctx.conexion.commit()

    nueva = sesion()
    muestra2 = nueva.muestras.obtener(1)
    cargado = nueva.resultados.obtener_de_muestra(muestra2)

    assert muestra2.estado.nombre == "ANALIZADA"
    assert cargado.muestra is muestra2
    assert (cargado.responsable, cargado.fecha_hora, cargado.observaciones) == ("Bioq. Pérez", FECHA, "Leucocitosis")
    assert cargado.valores == (HEMATOCRITO, LEUCOCITOS, UREA)  # mismos valores, mismo orden
    assert cargado.valores_fuera_de_rango() == (LEUCOCITOS,)
    assert cargado.valores[2].ref_min is None  # los límites que faltan siguen faltando


def test_guardar_dos_veces_el_resultado_no_lo_duplica(recibida):
    ctx, muestra = recibida
    resultado = ResultadoAnalisis(muestra, "Bioq. Pérez", FECHA, [HEMATOCRITO])
    ctx.ordenes.guardar(muestra.orden)
    assert ctx.resultados.guardar(resultado) == ctx.resultados.guardar(resultado)
    assert ctx.conexion.execute("SELECT COUNT(*) FROM resultados_analisis").fetchone()[0] == 1
    assert ctx.conexion.execute("SELECT COUNT(*) FROM valores_resultado").fetchone()[0] == 1


def test_una_muestra_sin_resultado_devuelve_none(recibida, sesion):
    nueva = sesion()
    assert nueva.resultados.obtener_de_muestra(nueva.muestras.obtener(1)) is None


def test_no_se_guarda_el_resultado_de_una_muestra_no_guardada(sesion):
    ctx = sesion()
    cliente = Cliente("1", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", Especie("Perro"), Sexo.MACHO, date(2026, 1, 10), cliente)
    consulta = Consulta(TipoConsulta.CONSULTA, FECHA, toby, Veterinario("M", "L", "G", Clinica("C", "")))
    orden = consulta.emitir_orden(TipoAnalisis("H", Decimal("1"), "Sangre", 2.0, 8.0, 24))
    muestra = Muestra(orden, "x")
    muestra.empaquetar("x"); muestra.despachar("x"); muestra.recibir(True, "x")
    resultado = ResultadoAnalisis(muestra, "Bioq. Pérez", FECHA, [HEMATOCRITO])
    with pytest.raises(ObjetoNoGuardado, match="muestra"):
        ctx.resultados.guardar(resultado)

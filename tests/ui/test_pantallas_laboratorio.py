"""Muestras, conservadoras, remitos, recepción y resultados: la lógica de cada pantalla."""

import pytest

from app.servicios import muestras, remitos
from app.ui.pantallas.conservadoras import PantallaConservadoras
from app.ui.pantallas.muestras import PantallaMuestras
from app.ui.pantallas.recepcion import PantallaRecepcion
from app.ui.pantallas.remitos import PantallaRemitos
from app.ui.pantallas.resultados import PantallaResultados
from tests.servicios.ayudas_circuito import conservadora_precintada, nueva_orden, remito_con
from tests.ui.conftest import elegir, elegir_consulta, elegir_mascota, sin_parametros

pytestmark = pytest.mark.usefixtures("con_seed", "ahora")


def armar(clase, sesion_ui):
    pantalla = clase(sesion_ui)
    pantalla.build()
    pantalla.al_mostrar()
    return pantalla


# =========================================================== Muestras

@pytest.fixture
def p_muestras(sesion_ui) -> PantallaMuestras:
    return armar(PantallaMuestras, sesion_ui)


def elegir_orden(selector, nombre="Toby", buscar="paz"):
    elegir_mascota(selector, nombre, buscar)
    elegir_consulta(selector)
    selector.lista_ordenes.value = selector.lista_ordenes.options[0].key
    selector._orden_elegida()


def test_registrar_una_extraccion_desde_la_pantalla(p_muestras, mensajes):
    consulta, orden = nueva_orden()
    elegir_orden(p_muestras.selector)
    p_muestras.observacion.value = "En ayunas"
    p_muestras.registrar_extraccion()

    assert mensajes.errores == [] and mensajes.exitos == ["Extracción registrada."]
    assert p_muestras.tabla.cantidad == 1
    assert p_muestras.detalle.visible and "Extraída" in p_muestras.titulo_detalle.value
    assert "Empaquetarla en una conservadora" in p_muestras.proximo_paso.value  # lo dice el estado
    assert not p_muestras.boton_reextraer.visible


def test_sin_orden_elegida_se_explica(p_muestras, mensajes):
    p_muestras.registrar_extraccion()
    assert "Elegí la orden" in mensajes.errores[-1]


def test_el_operador_vacio_se_pide_y_no_se_registra_nada(p_muestras, mensajes, operador):
    nueva_orden()
    elegir_orden(p_muestras.selector)
    operador["valor"] = "   "
    p_muestras.registrar_extraccion()
    assert "campo «Operador»" in mensajes.errores[-1]
    assert p_muestras.tabla.cantidad == 0


def test_una_orden_no_admite_dos_muestras_activas(p_muestras, mensajes):
    nueva_orden()
    elegir_orden(p_muestras.selector)
    p_muestras.registrar_extraccion()
    p_muestras.registrar_extraccion()
    assert "muestra activa" in mensajes.errores[-1]
    assert p_muestras.tabla.cantidad == 1


def test_la_muestra_rechazada_muestra_la_trazabilidad_y_permite_la_re_extraccion(p_muestras, mensajes):
    conservadora, creadas = conservadora_precintada("C-1")
    remito = remito_con(conservadora)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [remitos.DetalleDeRecepcion(conservadora.id, "ROTO", 5.0)])
    muestra_id = creadas[0][2].id

    p_muestras.filtro.value = "RECHAZADA"
    p_muestras.cargar()
    assert p_muestras.tabla.cantidad == 1
    p_muestras.elegir(muestra_id)

    assert "Rechazada" in p_muestras.titulo_detalle.value
    assert "estado final" in p_muestras.proximo_paso.value
    assert p_muestras.boton_reextraer.visible
    textos = repr(p_muestras.tiempo.controls[0].controls)
    assert "Precinto roto" in textos and "En tránsito" in textos and "Extracción" in textos  # la línea de tiempo

    p_muestras.re_extraer()
    assert "sin cargo" in mensajes.exitos[-1]
    assert "Extraída" in p_muestras.titulo_detalle.value and not p_muestras.boton_reextraer.visible


def test_los_botones_de_muestras_no_reciben_el_evento(p_muestras):
    for manejador in (p_muestras.cargar, p_muestras.registrar_extraccion, p_muestras.re_extraer):
        assert sin_parametros(manejador)


# =========================================================== Conservadoras

@pytest.fixture
def p_cons(sesion_ui) -> PantallaConservadoras:
    return armar(PantallaConservadoras, sesion_ui)


def test_crear_una_conservadora_y_elegirla(p_cons, mensajes):
    p_cons.codigo.value, p_cons.temp_min.value, p_cons.temp_max.value = "C-77", "4", "6"
    p_cons.crear()
    assert mensajes.exitos == ["Conservadora creada."]
    assert p_cons.tabla.cantidad == 1 and "C-77" in p_cons.titulo_detalle.value
    assert p_cons.bloque_empaquetar.visible and p_cons.bloque_precinto.visible


@pytest.mark.parametrize("campo, valor, mensaje", [("capacidad", "0", "capacidad"), ("temp_min", "frío", "temperatura mínima"), ("codigo", "", "código")])
def test_crear_con_datos_invalidos(p_cons, mensajes, campo, valor, mensaje):
    p_cons.codigo.value = "C-1"
    setattr(getattr(p_cons, campo), "value", valor)
    p_cons.crear()
    assert mensaje in mensajes.errores[-1] and p_cons.tabla.cantidad == 0


def test_empaquetar_y_precintar_desde_la_pantalla(p_cons, mensajes):
    _, orden = nueva_orden()
    muestra = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    p_cons.codigo.value, p_cons.temp_min.value, p_cons.temp_max.value = "C-1", "4", "6"
    p_cons.crear()
    assert [o.key for o in p_cons.muestra.options] == [str(muestra.id)]  # la muestra extraída aparece

    p_cons.empaquetar()  # sin elegir la muestra
    assert "Elegí la muestra" in mensajes.errores[-1]
    p_cons.muestra.value = p_cons.muestra.options[0].key
    p_cons.empaquetar()
    assert p_cons.tabla_muestras.cantidad == 1
    assert muestras.obtener_muestra(muestra.id).estado.nombre == "EMPAQUETADA"

    p_cons.numero_precinto.value = "P-100"
    p_cons.precintar()
    assert "Precintada con el N° P-100" in p_cons.nota.value
    assert not p_cons.bloque_empaquetar.visible and not p_cons.bloque_precinto.visible  # ya no admite más


def test_una_conservadora_de_temperatura_incompatible_rechaza_la_muestra(p_cons, mensajes):
    _, orden = nueva_orden()
    muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    p_cons.codigo.value, p_cons.temp_min.value, p_cons.temp_max.value = "C-CALIENTE", "4", "12"
    p_cons.crear()
    p_cons.empaquetar()  # sin elegir muestra
    assert "Elegí la muestra" in mensajes.errores[-1]
    elegir(p_cons.muestra, "#")
    p_cons.empaquetar()
    assert "no es compatible" in mensajes.errores[-1]


# =========================================================== Remitos

@pytest.fixture
def p_remitos(sesion_ui) -> PantallaRemitos:
    return armar(PantallaRemitos, sesion_ui)


def visibles(p) -> dict[str, bool]:
    return {"agregar": p.bloque_agregar.visible, "cerrar": p.bloque_cerrar.visible,
            "despachar": p.bloque_despachar.visible, "tramo": p.bloque_tramo.visible}


def test_crear_un_remito_numerado(p_remitos, mensajes):
    p_remitos.crear()
    assert "Elegí la clínica" in mensajes.errores[-1]
    p_remitos.clinica.value, p_remitos.laboratorio.value = p_remitos.clinica.options[0].key, p_remitos.laboratorio.options[0].key
    p_remitos.crear()
    assert mensajes.exitos[-1] == "Remito creado."
    assert "R-00001 · Abierto" in p_remitos.titulo_detalle.value


def test_remito_abierto_ofrece_solo_agregar_y_cerrar(p_remitos):
    conservadora, _ = conservadora_precintada("C-1")
    remito = remito_con(conservadora)
    p_remitos.cargar()
    p_remitos.elegir(remito.id)

    assert visibles(p_remitos) == {"agregar": True, "cerrar": True, "despachar": False, "tramo": False}
    assert "agregar conservadoras" in p_remitos.permitido.value and "despacharlo" not in p_remitos.permitido.value
    quitar = p_remitos.conservadoras.controls[0].controls[-1]  # el botón «Quitar» de la conservadora
    assert sin_parametros(quitar.on_click)


def test_cada_estado_del_remito_muestra_solo_lo_que_permite(p_remitos, mensajes):
    conservadora, _ = conservadora_precintada("C-1")
    remito = remito_con(conservadora)
    p_remitos.elegir(remito.id)

    p_remitos.cerrar()
    assert "Cerrado" in p_remitos.titulo_detalle.value
    assert visibles(p_remitos) == {"agregar": False, "cerrar": False, "despachar": True, "tramo": False}
    assert len(p_remitos.conservadoras.controls[0].controls) == 1  # sin botón «Quitar»

    p_remitos.despachar()
    assert "En tránsito" in p_remitos.titulo_detalle.value
    assert visibles(p_remitos) == {"agregar": False, "cerrar": False, "despachar": False, "tramo": True}
    assert "Recepción" in p_remitos.permitido.value  # indica dónde registrar la llegada

    remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [remitos.DetalleDeRecepcion(conservadora.id, "INTACTO", 5.0)])
    p_remitos.elegir(remito.id)
    assert visibles(p_remitos) == {"agregar": False, "cerrar": False, "despachar": False, "tramo": False}
    assert "ya está recibido" in p_remitos.permitido.value
    assert any("aceptada" in repr(x) for x in p_remitos.recepcion.controls)


def test_cerrar_un_remito_con_una_conservadora_sin_precinto_se_explica(p_remitos, mensajes):
    sin_precinto = muestras.crear_conservadora("C-SIN", 5, 4, 6)
    _, orden = nueva_orden()
    nueva = muestras.registrar_extraccion(orden.id, "Dr. Gómez")
    muestras.empaquetar_muestra(nueva.id, sin_precinto.id, "Enf. Ruiz")
    remito = remito_con(sin_precinto)
    p_remitos.elegir(remito.id)
    p_remitos.cerrar()
    assert "precinto" in mensajes.errores[-1] and "C-SIN" in mensajes.errores[-1]


def test_agregar_y_quitar_conservadoras(p_remitos, mensajes):
    a, _ = conservadora_precintada("C-A")
    remito = remito_con()
    p_remitos.elegir(remito.id)
    p_remitos.agregar()
    assert "Elegí la conservadora" in mensajes.errores[-1]

    elegir(p_remitos.libres, "C-A")
    p_remitos.agregar()
    assert mensajes.exitos[-1] == "Conservadora agregada."
    p_remitos.conservadoras.controls[0].controls[-1].on_click()  # «Quitar»
    assert "sus muestras siguen empaquetadas" in mensajes.exitos[-1]
    assert muestras.obtener_conservadora(a.id).muestras[0].estado.nombre == "EMPAQUETADA"


def test_registrar_un_tramo_desde_la_pantalla(p_remitos, mensajes):
    conservadora, _ = conservadora_precintada("C-1")
    remito = remito_con(conservadora)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    p_remitos.elegir(remito.id)

    p_remitos.origen.value, p_remitos.destino.value, p_remitos.transportista.value = "Clínica Centro", "Laboratorio", "Transportes Sur"
    p_remitos.salida.value, p_remitos.temperatura.value = "2026-11-02 12:30", "5,5"
    p_remitos.registrar_tramo()
    assert mensajes.exitos[-1] == "Tramo registrado." and p_remitos.tabla_tramos.cantidad == 1

    p_remitos.salida.value = "ayer"
    p_remitos.registrar_tramo()
    assert "AAAA-MM-DD HH:MM" in mensajes.errores[-1]


# =========================================================== Recepción

@pytest.fixture
def p_recepcion(sesion_ui) -> PantallaRecepcion:
    return armar(PantallaRecepcion, sesion_ui)


def remito_en_transito(codigos=("C-A", "C-B")):
    conservadoras = [conservadora_precintada(c)[0] for c in codigos]
    remito = remito_con(*conservadoras)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    return remito, conservadoras


def test_solo_se_ofrecen_los_remitos_en_transito(p_recepcion):
    conservadora, _ = conservadora_precintada("C-1")
    remito_con(conservadora)  # abierto: no se puede recibir
    p_recepcion.cargar()
    assert p_recepcion.remito.options == []
    remito, _ = remito_en_transito(("C-X",))
    p_recepcion.cargar()
    assert len(p_recepcion.remito.options) == 1


def test_recepcion_aceptada_confirma_sin_alertas(p_recepcion, mensajes):
    remito, _ = remito_en_transito()
    p_recepcion.cargar()
    p_recepcion.remito.value = p_recepcion.remito.options[0].key
    p_recepcion.elegir()
    assert len(p_recepcion._filas) == 2 and p_recepcion.formulario.visible
    for fila in p_recepcion._filas:
        fila.temperatura.value = "5"
    p_recepcion.registrar()

    assert mensajes.errores == [] and mensajes.avisos == []
    assert "todas las muestras aceptadas" in mensajes.exitos[-1]
    assert remitos.obtener_remito(remito.id).estado.nombre == "RECIBIDO"
    assert not p_recepcion.formulario.visible  # ya no está en tránsito


def test_recepcion_con_precinto_roto_rechaza_y_avisa_a_la_clinica(p_recepcion, mensajes):
    remito, _ = remito_en_transito()
    p_recepcion.cargar()
    p_recepcion.remito.value = p_recepcion.remito.options[0].key
    p_recepcion.elegir()
    p_recepcion._filas[0].temperatura.value = "5"
    p_recepcion._filas[1].temperatura.value = "5"
    p_recepcion._filas[1].precinto.value = "ROTO"
    p_recepcion.registrar()

    titulo, lineas = mensajes.avisos[0]
    assert "Recibido parcial" in titulo
    assert len(lineas) == 1 and "precinto roto" in lineas[0] and "re-extracción" in lineas[0]
    assert remitos.obtener_remito(remito.id).estado.nombre == "RECIBIDO_PARCIAL"


def test_recepcion_con_datos_invalidos_no_cambia_nada(p_recepcion, mensajes):
    remito, _ = remito_en_transito(("C-A",))
    p_recepcion.cargar()
    p_recepcion.remito.value = p_recepcion.remito.options[0].key
    p_recepcion.elegir()
    p_recepcion.registrar()  # temperatura vacía
    assert "temperatura de llegada" in mensajes.errores[-1]
    assert remitos.obtener_remito(remito.id).estado.nombre == "EN_TRANSITO"


# =========================================================== Resultados

@pytest.fixture
def p_resultados(sesion_ui) -> PantallaResultados:
    return armar(PantallaResultados, sesion_ui)


def muestra_recibida():
    conservadora, creadas = conservadora_precintada("C-1")
    remito = remito_con(conservadora)
    remitos.cerrar_remito(remito.id)
    remitos.despachar_remito(remito.id, "Transportes Sur")
    remitos.registrar_recepcion(remito.id, "Bioq. Pérez", [remitos.DetalleDeRecepcion(conservadora.id, "INTACTO", 5.0)])
    return creadas[0][2]


def agregar(p, parametro, valor, unidad, minimo="", maximo=""):
    p.parametro.value, p.valor.value, p.unidad.value, p.ref_min.value, p.ref_max.value = parametro, valor, unidad, minimo, maximo
    p.agregar_valor()


def test_solo_se_ofrecen_las_muestras_recibidas(p_resultados):
    muestra = muestra_recibida()
    _, orden = nueva_orden("28444555", "Rex")
    muestras.registrar_extraccion(orden.id, "Dr. Gómez")  # extraída: todavía no
    p_resultados.cargar()
    assert [o.key for o in p_resultados.muestra.options] == [str(muestra.id)]


def test_agregar_y_quitar_valores(p_resultados, mensajes):
    agregar(p_resultados, "Hematocrito", "41,5", "%", "37", "55")
    agregar(p_resultados, "Urea", "40", "mg/dl")
    assert p_resultados.tabla_valores.cantidad == 2 and p_resultados.parametro.value == ""
    agregar(p_resultados, "Mal", "alto", "%")
    assert "valor no es un número" in mensajes.errores[-1] and p_resultados.tabla_valores.cantidad == 2
    p_resultados.quitar_valor(0)
    assert p_resultados.tabla_valores.cantidad == 1


def test_registrar_el_resultado_avisa_al_responsable_y_se_puede_consultar(p_resultados, mensajes):
    muestra = muestra_recibida()
    p_resultados.cargar()
    p_resultados.muestra.value = p_resultados.muestra.options[0].key
    agregar(p_resultados, "Hematocrito", "41", "%", "37", "55")
    agregar(p_resultados, "Leucocitos", "25", "mil/µl", "6", "17")
    p_resultados.observaciones.value = "Leucocitosis"
    p_resultados.registrar()

    assert mensajes.errores == []
    assert mensajes.avisos[0] == ("Resultado registrado", ["Ana Paz: ya está el resultado de Hemograma"])
    assert p_resultados.tabla_valores.cantidad == 0  # el formulario quedó listo
    assert muestras.obtener_muestra(muestra.id).estado.nombre == "ANALIZADA"
    assert [o.key for o in p_resultados.analizada.options] == [str(muestra.id)]

    p_resultados.analizada.value = p_resultados.analizada.options[0].key
    p_resultados.ver()
    assert p_resultados.resultado.visible and p_resultados.nota_resultado.value == "Leucocitosis"
    assert p_resultados.tabla_resultado.cantidad == 2
    situaciones = [fila[-1] for fila in p_resultados.tabla_resultado.textos()]
    assert situaciones == ["Normal", "⚠ Fuera de rango"]


def test_registrar_sin_valores_o_sin_muestra_se_explica(p_resultados, mensajes):
    p_resultados.registrar()
    assert "Elegí la muestra" in mensajes.errores[-1]
    muestra = muestra_recibida()
    p_resultados.cargar()
    p_resultados.muestra.value = p_resultados.muestra.options[0].key
    p_resultados.registrar()
    assert "al menos un valor" in mensajes.errores[-1]
    assert muestras.obtener_muestra(muestra.id).estado.nombre == "RECIBIDA"

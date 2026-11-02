"""El flujo completo del sistema, persistido paso a paso.

Cada paso corre en su propia sesión (conexión y mapa de identidad nuevos), como lo hará
cada caso de uso de la capa de servicios (Fase 7): se carga lo que hace falta, se llama
al dominio, se guarda. Es el guion de la demo con precinto roto y re-extracción.
"""

from datetime import date, datetime
from decimal import Decimal

from app.dominio.clinica import Clinica
from app.dominio.cliente import Cliente
from app.dominio.conservadora import Conservadora
from app.dominio.consulta import Consulta
from app.dominio.enums import EstadoPrecinto, MotivoRechazo, Sexo, TipoConsulta
from app.dominio.especie import Especie, VacunaObligatoria
from app.dominio.laboratorio import Laboratorio
from app.dominio.mascota import Mascota
from app.dominio.muestra import Muestra
from app.dominio.observadores_muestra import AlertaRechazo, RegistroTrazabilidad
from app.dominio.recepcion import DetalleRecepcion, Recepcion
from app.dominio.remito_biologico import RemitoBiologico
from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.veterinario import Veterinario


def consulta_de(ctx) -> Consulta:
    return ctx.clientes.obtener_por_dni("30111222").mascotas[0].historia_clinica.consultas[0]


def con_trazabilidad(*muestras):
    for muestra in muestras:
        muestra.suscribir(RegistroTrazabilidad())


def enviar(sesion, numero, codigo, rota):
    """Empaqueta la muestra activa de la consulta, arma el remito, lo despacha y lo recibe."""
    ctx = sesion()
    consulta = consulta_de(ctx)
    orden = consulta.ordenes[0]
    muestra = orden.muestra_activa()
    con_trazabilidad(muestra)
    conservadora = Conservadora(codigo, 5, 4.0, 6.0)
    conservadora.agregar_muestra(muestra, "Enf. Ruiz", "Clínica Centro")
    conservadora.precintar(f"P-{codigo}", "Enf. Ruiz", datetime(2026, 6, 1, 10, 0))
    remito = RemitoBiologico(numero, consulta.veterinario.clinica, ctx.laboratorios.listar()[0])
    remito.agregar_conservadora(conservadora)
    remito.cerrar()
    remito.despachar("Transportes Sur", "Clínica Centro")
    remito.registrar_tramo("Clínica Centro", "Laboratorio", "Transportes Sur", datetime(2026, 6, 1, 10, 30))
    ctx.ordenes.guardar(orden)
    ctx.conservadoras.guardar(conservadora)
    ctx.remitos.guardar(remito)
    ctx.conexion.commit()

    # --- otra sesión: el laboratorio recibe ---
    ctx = sesion()
    remito = ctx.remitos.obtener_por_numero(numero)
    muestra = remito.conservadoras[0].muestras[0]
    alerta = AlertaRechazo()
    con_trazabilidad(muestra)
    muestra.suscribir(alerta)
    precinto = EstadoPrecinto.ROTO if rota else EstadoPrecinto.INTACTO
    remito.registrar_recepcion(Recepcion(
        remito.destino, "Bioq. Pérez", datetime(2026, 6, 1, 14, 0),
        [DetalleRecepcion(remito.conservadoras[0], precinto, 5.0)]))
    ctx.muestras.guardar(muestra)
    ctx.remitos.guardar(remito)
    ctx.conexion.commit()
    return alerta


def test_flujo_completo_persistido_con_precinto_roto_y_re_extraccion(sesion):
    # 1. Alta y consulta con una orden de hemograma.
    ctx = sesion()
    perro = Especie("Perro")
    perro.agregar_vacuna_obligatoria(VacunaObligatoria("Sextuple", 2, 12))
    cliente = Cliente("30111222", "Ana", "Paz", "", "", "")
    toby = Mascota("Toby", perro, Sexo.MACHO, date(2026, 1, 10), cliente)
    veterinario = Veterinario("MP-1", "Laura", "Gómez", Clinica("Centro", "Av. Colón 100"))
    consulta = Consulta(TipoConsulta.CONSULTA, datetime(2026, 5, 10, 11, 0), toby, veterinario)
    consulta.emitir_orden(TipoAnalisis("Hemograma", Decimal("12500"), "Sangre", 2.0, 8.0, 24))
    toby.historia_clinica.registrar_consulta(consulta)  # advierte la Sextuple pendiente
    ctx.clientes.guardar(cliente)
    ctx.laboratorios.guardar(Laboratorio("Central", "Bv. Illia 1"))
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    # 2. Extracción de la primera muestra.
    ctx = sesion()
    orden = consulta_de(ctx).ordenes[0]
    primera = Muestra(orden, "Dr. Gómez", "Clínica Centro")
    con_trazabilidad(primera)
    ctx.ordenes.guardar(orden)
    ctx.conexion.commit()

    # 3 y 4. Empaquetado, envío y recepción: llega con el precinto roto.
    alerta = enviar(sesion, "R-1", "C-1", rota=True)
    assert len(alerta.alertas) == 1  # se avisa a la clínica

    # 5. Re-extracción en la misma orden.
    ctx = sesion()
    orden = consulta_de(ctx).ordenes[0]
    assert orden.muestra_activa() is None
    segunda = Muestra(orden, "Dr. Gómez", "Clínica Centro", "Re-extracción")
    con_trazabilidad(segunda)
    ctx.ordenes.guardar(orden)
    ctx.conexion.commit()

    # 6. Segundo envío: llega bien.
    enviar(sesion, "R-2", "C-2", rota=False)

    # 7. El laboratorio registra el resultado (la trazabilidad se suscribe antes de analizar).
    ctx = sesion()
    consulta = consulta_de(ctx)
    segunda = consulta.ordenes[0].muestra_activa()
    con_trazabilidad(segunda)
    resultado = ResultadoAnalisis(segunda, "Bioq. Pérez", datetime(2026, 6, 2, 9, 0),
                                  [ValorResultado("Hematocrito", 41.0, "%", 37.0, 55.0)], ubicacion="Laboratorio")
    ctx.muestras.guardar(segunda)
    ctx.resultados.guardar(resultado)
    ctx.conexion.commit()

    # 8. Se cierra la consulta y se emite el comprobante.
    ctx = sesion()
    consulta = consulta_de(ctx)
    consulta.cerrar(Decimal("3000"), datetime(2026, 6, 2, 10, 0))
    ctx.consultas.guardar(consulta)
    ctx.conexion.commit()

    # --- Verificación final, en una sesión nueva ---
    ctx = sesion()
    consulta = consulta_de(ctx)
    assert consulta.advertencias == ("Vacuna pendiente: Sextuple",)
    (orden,) = consulta.ordenes
    rechazada, analizada = orden.muestras

    assert [c.nuevo for c in rechazada.historial] == ["EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECHAZADA"]
    assert rechazada.estado.motivos == (MotivoRechazo.PRECINTO_ROTO,)
    assert [c.nuevo for c in analizada.historial] == [
        "EXTRAIDA", "EMPAQUETADA", "EN_TRANSITO", "RECIBIDA", "ANALIZADA"]
    assert analizada.historial[0].observacion == "Re-extracción"

    assert ctx.remitos.obtener_por_numero("R-1").estado.nombre == "RECHAZADO"
    assert ctx.remitos.obtener_por_numero("R-2").estado.nombre == "RECIBIDO"
    assert ctx.resultados.obtener_de_muestra(analizada).valores[0].parametro == "Hematocrito"

    # La re-extracción no generó cargo: el comprobante tiene la consulta y UN solo análisis.
    assert [i.descripcion for i in consulta.comprobante.items] == ["Consulta", "Hemograma"]
    assert consulta.comprobante.total == Decimal("15500")

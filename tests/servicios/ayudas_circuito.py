"""Ayudas compartidas por los tests del circuito de muestras (extracción, envío, recepción)."""

from app.servicios import catalogos, consultas, muestras, remitos
from tests.servicios.conftest import mascota, veterinario


def nueva_orden(dni="30111222", nombre="Toby", analisis="Hemograma"):
    """Una consulta de la mascota con una orden de derivación. Devuelve (consulta, orden)."""
    consulta = consultas.registrar_consulta(mascota(dni, nombre).id, veterinario("MP-1001").id, "CONSULTA")
    return consulta, consultas.emitir_orden(consulta.id, analisis)


def muestra_empaquetada(conservadora, dni="30111222", nombre="Toby"):
    """Extrae una muestra de una orden nueva y la empaqueta en `conservadora`."""
    consulta, orden = nueva_orden(dni, nombre)
    muestra = muestras.registrar_extraccion(orden.id, "Dr. Gómez", "Clínica Centro")
    muestras.empaquetar_muestra(muestra.id, conservadora.id, "Enf. Ruiz", "Clínica Centro")
    return consulta, orden, muestra


def conservadora_precintada(codigo="C-1", cantidad=1, **ubicacion):
    """Una conservadora con `cantidad` muestras empaquetadas y precintada."""
    conservadora = muestras.crear_conservadora(codigo, 5, 4.0, 6.0)
    creadas = [muestra_empaquetada(conservadora) for _ in range(cantidad)]
    muestras.precintar_conservadora(conservadora.id, f"P-{codigo}", "Enf. Ruiz")
    return muestras.obtener_conservadora(conservadora.id), creadas


def remito_con(*conservadoras):
    remito = remitos.crear_remito(catalogos.listar_clinicas()[0].id, catalogos.listar_laboratorios()[0].id)
    for conservadora in conservadoras:
        remitos.agregar_conservadora_a_remito(remito.id, conservadora.id)
    return remito


def estados(remito_id):
    """Estado de cada muestra del remito, tal como está guardado en la base."""
    remito = remitos.obtener_remito(remito_id)
    return [m.estado.nombre for c in remito.conservadoras for m in c.muestras]

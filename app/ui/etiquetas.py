"""Textos para mostrar: los estados y motivos se guardan como códigos (EN_TRANSITO) y
acá se traducen a lo que lee el usuario (En tránsito)."""

ESTADOS_MUESTRA = {
    "EXTRAIDA": "Extraída", "EMPAQUETADA": "Empaquetada", "EN_TRANSITO": "En tránsito",
    "RECIBIDA": "Recibida", "ANALIZADA": "Analizada", "RECHAZADA": "Rechazada",
}

ESTADOS_REMITO = {
    "ABIERTO": "Abierto", "CERRADO": "Cerrado", "EN_TRANSITO": "En tránsito",
    "RECIBIDO": "Recibido", "RECIBIDO_PARCIAL": "Recibido parcial", "RECHAZADO": "Rechazado",
}

MOTIVOS = {
    "PRECINTO_ROTO": "Precinto roto",
    "TEMPERATURA_FUERA_DE_RANGO": "Temperatura fuera de rango",
}

# Lo que puede hacerse con una muestra / un remito según lo que su estado permite.
OPERACIONES_MUESTRA = {
    "empaquetar": "Empaquetarla en una conservadora",
    "despachar": "Despacharla junto con su remito",
    "recibir": "Que el laboratorio la reciba",
    "analizar": "Registrar su resultado",
}


# Color con que se muestra cada estado en las tablas (ver tema.TONOS). Una celda cuyo texto
# figura acá se dibuja como insignia; cualquier otro texto se muestra normal.
TONO_DE_ESTADO = {
    # Muestras
    "Extraída": "neutro", "Empaquetada": "info", "En tránsito": "progreso",
    "Recibida": "info", "Analizada": "ok", "Rechazada": "peligro",
    # Remitos
    "Abierto": "neutro", "Cerrado": "info", "Recibido": "ok", "Recibido parcial": "progreso", "Rechazado": "peligro",
    # Clientes, mascotas, turnos y consultas
    "Activo": "ok", "Activa": "ok", "De baja": "neutro",
    "Programado": "info", "Cancelado": "neutro",
    "Abierta": "progreso", "Cerrada": "ok",
    # Prioridad de la orden y situación de un valor de resultado
    "Urgente": "peligro", "Normal": "ok", "⚠ Fuera de rango": "peligro",
}


def estado_muestra(codigo: str) -> str:
    return ESTADOS_MUESTRA.get(codigo, codigo)


def estado_remito(codigo: str) -> str:
    return ESTADOS_REMITO.get(codigo, codigo)


def motivos(codigos) -> str:
    return ", ".join(MOTIVOS.get(c, c) for c in codigos)

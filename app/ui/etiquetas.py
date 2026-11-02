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


def estado_muestra(codigo: str) -> str:
    return ESTADOS_MUESTRA.get(codigo, codigo)


def estado_remito(codigo: str) -> str:
    return ESTADOS_REMITO.get(codigo, codigo)


def motivos(codigos) -> str:
    return ", ".join(MOTIVOS.get(c, c) for c in codigos)

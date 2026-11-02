"""Atajos de los tests de servicios para encontrar los datos del seed por su nombre."""

from app.servicios import catalogos, clientes

# --- Atajos para encontrar los datos del seed por su nombre ---

def mascota(dni: str, nombre: str):
    cliente = clientes.buscar_clientes(dni, incluir_inactivos=True)[0]
    return next(m for m in cliente.mascotas if m.nombre == nombre)


def veterinario(matricula: str):
    return next(v for v in catalogos.listar_veterinarios() if v.matricula == matricula)

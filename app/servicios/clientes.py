"""Casos de uso: clientes, mascotas e historias clínicas (procesos 1 y 2).

Cada función pública es un caso de uso y corre en UNA transacción. Reciben ids o
datos simples (lo que maneja la interfaz) y devuelven objetos del dominio.
"""

from __future__ import annotations

from datetime import date

from app.dominio.cliente import Cliente
from app.dominio.enums import Sexo
from app.dominio.especie import VacunaObligatoria
from app.dominio.excepciones import ReglaNegocio
from app.dominio.mascota import Mascota
from app.servicios import tiempo, validaciones as v
from app.servicios._comun import caso_de_uso, requerir
from app.servicios.excepciones import EntradaInvalida, NoEncontrado

# ---------------------------------------------------------------- clientes


def alta_cliente(dni: str, nombre: str, apellido: str, telefono: str = "",
                 email: str = "", direccion: str = "") -> Cliente:
    dni = v.dni(dni)
    cliente = Cliente(
        dni,
        v.texto_obligatorio(nombre, "El nombre", 60),
        v.texto_obligatorio(apellido, "El apellido", 60),
        v.telefono_opcional(telefono),
        v.email_opcional(email),
        v.texto_opcional(direccion, "La dirección"),
    )
    with caso_de_uso() as ctx:
        if ctx.clientes.obtener_por_dni(dni) is not None:
            raise ReglaNegocio(f"Ya existe un cliente con el DNI {dni}")
        ctx.clientes.guardar(cliente)
    return cliente


def obtener_cliente(cliente_id: int) -> Cliente:
    with caso_de_uso() as ctx:
        return requerir(ctx.clientes.obtener(cliente_id), "el cliente", cliente_id)


def buscar_clientes(texto: str = "", incluir_inactivos: bool = False) -> list[Cliente]:
    """Clientes cuyo DNI, apellido o nombre contienen el texto. Por defecto, solo los activos."""
    with caso_de_uso() as ctx:
        return ctx.clientes.buscar(v.texto_opcional(texto, "La búsqueda", 60), incluir_inactivos)


def modificar_cliente(cliente_id: int, dni: str | None = None, nombre: str | None = None,
                      apellido: str | None = None, telefono: str | None = None,
                      email: str | None = None, direccion: str | None = None) -> Cliente:
    """Cambia solo los datos que se pasan (los que son None quedan como estaban)."""
    with caso_de_uso() as ctx:
        cliente = requerir(ctx.clientes.obtener(cliente_id), "el cliente", cliente_id)
        if dni is not None:
            dni = v.dni(dni)
            otro = ctx.clientes.obtener_por_dni(dni)
            if otro is not None and otro is not cliente:
                raise ReglaNegocio(f"Ya existe otro cliente con el DNI {dni}")
            cliente.dni = dni
        if nombre is not None:
            cliente.nombre = v.texto_obligatorio(nombre, "El nombre", 60)
        if apellido is not None:
            cliente.apellido = v.texto_obligatorio(apellido, "El apellido", 60)
        if telefono is not None:
            cliente.telefono = v.telefono_opcional(telefono)
        if email is not None:
            cliente.email = v.email_opcional(email)
        if direccion is not None:
            cliente.direccion = v.texto_opcional(direccion, "La dirección")
        ctx.clientes.guardar(cliente)
    return cliente


def dar_de_baja_cliente(cliente_id: int) -> Cliente:
    with caso_de_uso() as ctx:
        cliente = requerir(ctx.clientes.obtener(cliente_id), "el cliente", cliente_id)
        cliente.dar_de_baja()  # falla si todavía tiene mascotas activas
        ctx.clientes.guardar(cliente)
    return cliente


def reactivar_cliente(cliente_id: int) -> Cliente:
    with caso_de_uso() as ctx:
        cliente = requerir(ctx.clientes.obtener(cliente_id), "el cliente", cliente_id)
        cliente.reactivar()
        ctx.clientes.guardar(cliente)
    return cliente


# ---------------------------------------------------------------- mascotas


def alta_mascota(cliente_id: int, nombre: str, especie: str, sexo: Sexo | str,
                 fecha_nacimiento: date) -> Mascota:
    nombre = v.texto_obligatorio(nombre, "El nombre de la mascota", 60)
    sexo = v.opcion(sexo, Sexo, "El sexo")
    fecha_nacimiento = v.fecha_no_futura(fecha_nacimiento, "La fecha de nacimiento", tiempo.hoy())
    with caso_de_uso() as ctx:
        cliente = requerir(ctx.clientes.obtener(cliente_id), "el cliente", cliente_id)
        nombre_especie = v.texto_obligatorio(especie, "La especie", 60)
        especie_dominio = requerir(ctx.especies.obtener_por_nombre(nombre_especie), "la especie", nombre_especie)
        mascota = Mascota(nombre, especie_dominio, sexo, fecha_nacimiento, cliente)  # exige cliente activo
        ctx.clientes.guardar(cliente)
    return mascota


def obtener_mascota(mascota_id: int) -> Mascota:
    with caso_de_uso() as ctx:
        return requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)


def modificar_mascota(mascota_id: int, nombre: str | None = None, sexo: Sexo | str | None = None) -> Mascota:
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        if nombre is not None:
            mascota.nombre = v.texto_obligatorio(nombre, "El nombre de la mascota", 60)
        if sexo is not None:
            mascota.sexo = v.opcion(sexo, Sexo, "El sexo")
        ctx.clientes.guardar(mascota.responsable)
    return mascota


def dar_de_baja_mascota(mascota_id: int) -> Mascota:
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        mascota.dar_de_baja()
        ctx.clientes.guardar(mascota.responsable)
    return mascota


def reactivar_mascota(mascota_id: int) -> Mascota:
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        mascota.reactivar()  # falla si su responsable está de baja
        ctx.clientes.guardar(mascota.responsable)
    return mascota


# ---------------------------------------------------------------- historia clínica


def actualizar_historia_clinica(mascota_id: int, alergias: str | None = None,
                                antecedentes: str | None = None) -> Mascota:
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        historia = mascota.historia_clinica
        if alergias is not None:
            historia.alergias = v.texto_opcional(alergias, "Las alergias", 500)
        if antecedentes is not None:
            historia.antecedentes = v.texto_opcional(antecedentes, "Los antecedentes", 500)
        ctx.clientes.guardar(mascota.responsable)
    return mascota


def aplicar_vacuna(mascota_id: int, vacuna: str, fecha: date | None = None) -> Mascota:
    """Registra una vacuna del esquema de la especie como aplicada en `fecha` (por defecto, hoy)."""
    nombre = v.texto_obligatorio(vacuna, "La vacuna", 60)
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        fecha = v.fecha_no_futura(fecha if fecha is not None else tiempo.hoy(), "La fecha de aplicación", tiempo.hoy())
        if fecha < mascota.fecha_nacimiento:
            raise EntradaInvalida("La vacuna no puede ser anterior al nacimiento de la mascota")
        elegida = next((x for x in mascota.especie.esquema_vacunas if x.nombre.lower() == nombre.lower()), None)
        if elegida is None:
            raise NoEncontrado(f"La vacuna {nombre} no está en el esquema de {mascota.especie.nombre}")
        mascota.historia_clinica.registrar_vacuna(elegida, fecha)
        ctx.clientes.guardar(mascota.responsable)
    return mascota


def vacunas_pendientes(mascota_id: int, fecha: date | None = None) -> list[VacunaObligatoria]:
    """Vacunas del esquema que le faltan a la mascota en `fecha` (por defecto, hoy)."""
    with caso_de_uso() as ctx:
        mascota = requerir(ctx.clientes.mascota_por_id(mascota_id), "la mascota", mascota_id)
        return mascota.historia_clinica.vacunas_pendientes(fecha if fecha is not None else tiempo.hoy())

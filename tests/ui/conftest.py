"""Fixtures de los tests de la interfaz: se prueba la lógica de cada pantalla sin abrir una ventana."""

import inspect

import pytest

from app.ui.sesion import Sesion


class MensajeroEnMemoria:
    """Reemplaza al mensajero de Flet: guarda lo que se le diría al usuario."""

    def __init__(self) -> None:
        self.exitos: list[str] = []
        self.errores: list[str] = []
        self.avisos: list[tuple[str, list[str]]] = []

    def exito(self, texto: str) -> None:
        self.exitos.append(texto)

    def error(self, texto: str) -> None:
        self.errores.append(texto)

    def aviso(self, titulo, lineas) -> None:
        self.avisos.append((titulo, list(lineas)))


@pytest.fixture
def mensajes() -> MensajeroEnMemoria:
    return MensajeroEnMemoria()


@pytest.fixture
def operador() -> dict:
    """El texto del campo «Operador»; los tests lo cambian con operador["valor"] = ..."""
    return {"valor": "Dr. Gómez"}


@pytest.fixture
def sesion_ui(mensajes, operador) -> Sesion:
    return Sesion(mensajes, lambda: operador["valor"])


def sin_parametros(manejador) -> bool:
    """Flet le pasa el evento a un manejador solo si declara parámetros: los botones de las
    pantallas tienen que quedar sin ninguno."""
    return len(inspect.signature(manejador).parameters) == 0


# --- Ayudas para manejar los selectores y listas como lo haría el usuario ---

def elegir_cliente_en_la_lista(buscador, buscar: str, posicion: int = 0) -> None:
    """Escribe en el buscador y toca el cliente de la lista, como lo haría el usuario."""
    buscador.campo.value = buscar
    buscador.escribir()
    if not buscador.coincidencias:
        raise AssertionError(f"La búsqueda {buscar!r} no encontró clientes")
    buscador.elegir(buscador.coincidencias[posicion].id)


def elegir_mascota(selector, nombre: str, buscar: str = "") -> None:
    """Busca al cliente (tocándolo en la lista) y elige la mascota `nombre` en el selector."""
    elegir_cliente_en_la_lista(selector.buscador, buscar or nombre)
    opcion = next(o for o in selector.lista.options if o.text.startswith(nombre))
    selector.lista.value = opcion.key
    selector._elegida()


def elegir_consulta(selector, posicion: int = 0) -> None:
    selector.lista_consultas.value = selector.lista_consultas.options[posicion].key
    selector._consulta_elegida()


def elegir(lista, texto_o_clave: str) -> None:
    """Elige en una lista desplegable la opción cuyo texto empieza con `texto_o_clave`, o con esa clave."""
    opcion = next(o for o in lista.options if o.key == texto_o_clave or (o.text or "").startswith(texto_o_clave))
    lista.value = opcion.key

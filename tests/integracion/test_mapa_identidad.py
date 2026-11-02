import pytest

from app.dominio.cliente import Cliente
from app.persistencia.identidad import MapaIdentidad, ObjetoNoGuardado
from app.persistencia.repositorio_base import Repositorio


class Contexto:  # alcanza con algo que tenga `mapa` y `conexion`
    def __init__(self):
        self.mapa = MapaIdentidad()
        self.conexion = None


def un_cliente(dni="1") -> Cliente:
    return Cliente(dni, "Ana", "Paz", "", "", "")


def test_un_objeto_nuevo_no_tiene_id():
    assert MapaIdentidad().id_de("cliente", un_cliente()) is None


def test_registrar_permite_ir_de_objeto_a_id_y_de_id_a_objeto():
    mapa, cliente = MapaIdentidad(), un_cliente()
    mapa.registrar("cliente", 7, cliente)
    assert mapa.id_de("cliente", cliente) == 7
    assert mapa.obtener("cliente", 7) is cliente


def test_dos_objetos_iguales_en_valores_siguen_siendo_dos_identidades():
    mapa = MapaIdentidad()
    a, b = un_cliente(), un_cliente()
    mapa.registrar("cliente", 1, a)
    assert mapa.id_de("cliente", b) is None


def test_el_mismo_id_en_tipos_distintos_no_se_pisa():
    mapa, cliente, otro = MapaIdentidad(), un_cliente(), un_cliente("2")
    mapa.registrar("cliente", 1, cliente)
    mapa.registrar("mascota", 1, otro)
    assert mapa.obtener("cliente", 1) is cliente
    assert mapa.obtener("mascota", 1) is otro


def test_pedir_el_id_de_algo_no_guardado_da_un_error_claro():
    repositorio = Repositorio(Contexto())
    with pytest.raises(ObjetoNoGuardado, match="cliente"):
        repositorio._id("cliente", un_cliente())

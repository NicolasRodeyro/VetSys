"""La interfaz solo habla con los servicios (CLAUDE.md §3): no importa el dominio ni la persistencia."""

import ast
from pathlib import Path

import pytest

RAIZ_UI = Path(__file__).resolve().parents[2] / "app" / "ui"
ARCHIVOS = sorted(RAIZ_UI.rglob("*.py"))
PROHIBIDOS = ("app.dominio", "app.persistencia")


def importaciones(archivo: Path) -> list[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres += [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.append(nodo.module)
    return nombres


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: str(a.relative_to(RAIZ_UI)))
def test_la_interfaz_no_importa_ni_el_dominio_ni_la_persistencia(archivo):
    malos = [n for n in importaciones(archivo) if n.startswith(PROHIBIDOS)]
    assert malos == [], f"{archivo.name} importa {malos}: tiene que pasar por servicios/"


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: str(a.relative_to(RAIZ_UI)))
def test_la_interfaz_no_tiene_sql(archivo):
    texto = archivo.read_text(encoding="utf-8").upper()
    assert "SELECT " not in texto and "INSERT INTO" not in texto and "sqlite3" not in texto.lower()

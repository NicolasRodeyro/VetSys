"""Lo que devuelve cada reporte: una tabla ya formateada, notas y los datos del gráfico.

No tiene nada de Flet ni de matplotlib: la pantalla muestra la tabla y le pasa el gráfico
a `graficos.a_png()`. Así el cálculo de un reporte se prueba sin interfaz y sin dibujar.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Grafico:
    """Un gráfico de barras agrupadas: una barra por serie en cada etiqueta del eje x."""

    titulo: str
    etiquetas: list[str]
    series: dict[str, list[float]]  # nombre de la serie -> un valor por etiqueta
    eje_y: str = ""


@dataclass(frozen=True)
class ResultadoReporte:
    titulo: str
    columnas: list[str]
    filas: list[list[str]]
    notas: list[str] = field(default_factory=list)
    grafico: Grafico | None = None

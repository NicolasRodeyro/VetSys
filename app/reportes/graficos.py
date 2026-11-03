"""Dibuja un `Grafico` como imagen PNG (bytes), que la pantalla muestra con ft.Image(src=...).

Se usa `matplotlib.figure.Figure` directamente y no `pyplot`: pyplot guarda las figuras en un
estado global y abre ventanas propias; acá solo se dibuja en memoria (backend Agg).
"""

from __future__ import annotations

from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # sin ventanas: se dibuja en memoria

from matplotlib.figure import Figure  # noqa: E402  (después de elegir el backend)

from app.reportes.resultado import Grafico  # noqa: E402

COLORES = ["#0F766E", "#1D4F91", "#8A5300", "#A1261B", "#5F6F6C", "#7FD1C3"]


def a_png(grafico: Grafico) -> bytes:
    figura = Figure(figsize=(8, 3.6), dpi=100)
    ejes = figura.add_subplot()
    cantidad = len(grafico.series)
    ancho = 0.8 / max(cantidad, 1)
    posiciones = range(len(grafico.etiquetas))
    for i, (nombre, valores) in enumerate(grafico.series.items()):
        corrimiento = (i - (cantidad - 1) / 2) * ancho
        ejes.bar([p + corrimiento for p in posiciones], valores, width=ancho, label=nombre,
                 color=COLORES[i % len(COLORES)])
    ejes.set_xticks(list(posiciones), grafico.etiquetas)
    ejes.set_title(grafico.titulo)
    ejes.set_ylabel(grafico.eje_y)
    ejes.spines[["top", "right"]].set_visible(False)
    if cantidad > 1:
        ejes.legend(frameon=False)
    figura.tight_layout()
    salida = BytesIO()
    figura.savefig(salida, format="png")
    return salida.getvalue()

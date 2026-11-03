"""Reportes: consultas SQL de solo lectura, cálculos en Python y datos para el gráfico.

Cada reporte es un módulo con `TITULO`, `DESCRIPCION` y `generar(filtro) -> ResultadoReporte`.
La pantalla de reportes los ofrece en el orden de `REPORTES`.
"""

from app.reportes import facturacion, rechazos, tiempos, vacunas

REPORTES = {
    "tiempos": tiempos,
    "rechazos": rechazos,
    "vacunas": vacunas,
    "facturacion": facturacion,
}

"""Las pantallas de la aplicación, en el orden en que aparecen en el menú."""

from app.ui.pantallas.clientes import PantallaClientes
from app.ui.pantallas.comprobantes import PantallaComprobantes
from app.ui.pantallas.conservadoras import PantallaConservadoras
from app.ui.pantallas.consultas import PantallaConsultas
from app.ui.pantallas.mascotas import PantallaMascotas
from app.ui.pantallas.muestras import PantallaMuestras
from app.ui.pantallas.recepcion import PantallaRecepcion
from app.ui.pantallas.remitos import PantallaRemitos
from app.ui.pantallas.reportes import PantallaReportes
from app.ui.pantallas.resultados import PantallaResultados
from app.ui.pantallas.turnos import PantallaTurnos

PANTALLAS = [
    # Atención
    PantallaClientes,
    PantallaMascotas,
    PantallaTurnos,
    PantallaConsultas,
    PantallaComprobantes,
    # Laboratorio
    PantallaMuestras,
    PantallaConservadoras,
    PantallaRemitos,
    PantallaRecepcion,
    PantallaResultados,
    # Reportes
    PantallaReportes,
]

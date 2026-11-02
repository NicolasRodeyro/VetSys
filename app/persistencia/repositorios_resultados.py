"""Repositorio de los resultados de análisis."""

from __future__ import annotations

from app.dominio.muestra import Muestra
from app.dominio.resultado_analisis import ResultadoAnalisis, ValorResultado
from app.persistencia import reconstruccion
from app.persistencia.conversiones import a_datetime, a_texto
from app.persistencia.repositorio_base import Repositorio


class RepositorioResultados(Repositorio):
    """Agregado: ResultadoAnalisis con sus valores.

    Es inmutable y una muestra tiene como máximo uno: se guarda una sola vez, y la
    muestra tiene que estar guardada (con su orden) antes.
    """

    def guardar(self, resultado: ResultadoAnalisis) -> int:
        existente = self.mapa.id_de("resultado", resultado)
        if existente is not None:
            return existente
        id_ = self._insertar(
            "INSERT INTO resultados_analisis (muestra_id, responsable, fecha_hora, observaciones) "
            "VALUES (?, ?, ?, ?)",
            (self._id("muestra", resultado.muestra), resultado.responsable,
             a_texto(resultado.fecha_hora), resultado.observaciones))
        for v in resultado.valores:
            self._insertar(
                "INSERT INTO valores_resultado (resultado_id, parametro, valor, unidad, ref_min, ref_max) "
                "VALUES (?, ?, ?, ?, ?, ?)", (id_, v.parametro, v.valor, v.unidad, v.ref_min, v.ref_max))
        self.mapa.registrar("resultado", id_, resultado)
        return id_

    def obtener_de_muestra(self, muestra: Muestra) -> ResultadoAnalisis | None:
        fila = self._una("SELECT * FROM resultados_analisis WHERE muestra_id = ?", (self._id("muestra", muestra),))
        if fila is None:
            return None
        existente = self.mapa.obtener("resultado", fila["id"])
        if existente is not None:
            return existente
        valores = [
            ValorResultado(v["parametro"], v["valor"], v["unidad"], v["ref_min"], v["ref_max"])
            for v in self._todas("SELECT * FROM valores_resultado WHERE resultado_id = ? ORDER BY id", (fila["id"],))
        ]
        resultado = reconstruccion.restaurar_resultado(
            muestra, fila["responsable"], a_datetime(fila["fecha_hora"]), valores, fila["observaciones"])
        self.mapa.registrar("resultado", fila["id"], resultado)
        return resultado

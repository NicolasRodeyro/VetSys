"""Repositorios del envío de muestras: muestras (con su trazabilidad), conservadoras y remitos."""

from __future__ import annotations

from app.dominio.cambio_estado import CambioEstado
from app.dominio.conservadora import Conservadora
from app.dominio.enums import EstadoPrecinto, MotivoRechazo
from app.dominio.muestra import Muestra
from app.dominio.orden_derivacion import OrdenDerivacion
from app.dominio.precinto import Precinto
from app.dominio.recepcion import DetalleRecepcion, Recepcion
from app.dominio.remito_biologico import RemitoBiologico
from app.dominio.tramo_envio import TramoEnvio
from app.persistencia import reconstruccion
from app.persistencia.conversiones import a_datetime, a_texto
from app.persistencia.identidad import HistorialIncompleto
from app.persistencia.mapeo_estados import estado_de_muestra, estado_de_remito
from app.persistencia.repositorio_base import Repositorio


class RepositorioMuestras(Repositorio):
    """Agregado: Muestra con su historial de cambios de estado.

    La muestra se guarda dentro de su orden (RepositorioOrdenes) y se carga con ella.
    Los observadores NO se persisten: quien carga la muestra es quien suscribe los
    que necesite (CLAUDE.md §4.4). En particular hay que suscribir RegistroTrazabilidad
    antes de cambiarle el estado, o `guardar` avisa que el historial quedó incompleto.
    """

    # ---------------- guardar ----------------

    def guardar(self, muestra: Muestra, orden_id: int | None = None) -> int:
        if orden_id is None:
            orden_id = self._id("orden", muestra.orden)
        estado = muestra.estado.nombre
        historial = muestra.historial
        if not historial or historial[-1].nuevo != estado:
            raise HistorialIncompleto(
                f"El historial de la muestra no llega hasta su estado actual ({estado}). "
                "¿Se suscribió RegistroTrazabilidad antes de cambiarle el estado?"
            )

        id_ = self.mapa.id_de("muestra", muestra)
        if id_ is None:
            id_ = self._insertar("INSERT INTO muestras (orden_id, estado) VALUES (?, ?)", (orden_id, estado))
            self.mapa.registrar("muestra", id_, muestra)
        else:
            self.cx.execute("UPDATE muestras SET orden_id = ?, estado = ? WHERE id = ?", (orden_id, estado, id_))

        # La trazabilidad solo se agrega (el trigger de la base impide modificarla):
        # se inserta lo que todavía no está en la base.
        ya_guardados = self._contar("SELECT COUNT(*) FROM cambios_estado WHERE muestra_id = ?", (id_,))
        for cambio in historial[ya_guardados:]:
            self._guardar_cambio(id_, cambio)
        return id_

    def _guardar_cambio(self, muestra_id: int, cambio: CambioEstado) -> None:
        cambio_id = self._insertar(
            "INSERT INTO cambios_estado (muestra_id, anterior, nuevo, fecha_hora, responsable, "
            "ubicacion, observacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (muestra_id, cambio.anterior, cambio.nuevo, a_texto(cambio.fecha_hora),
             cambio.responsable, cambio.ubicacion, cambio.observacion))
        for motivo in cambio.motivos:
            self._insertar("INSERT INTO cambio_estado_motivos (cambio_id, motivo) VALUES (?, ?)",
                           (cambio_id, motivo.value))

    # ---------------- cargar ----------------

    def obtener(self, id_: int) -> Muestra | None:
        existente = self.mapa.obtener("muestra", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT orden_id FROM muestras WHERE id = ?", (id_,))
        if fila is None:
            return None
        # La muestra forma parte de su orden: cargar la orden trae todas sus muestras.
        self.ctx.ordenes.obtener(fila["orden_id"])
        return self.mapa.obtener("muestra", id_)

    def listar_por_estado(self, nombre_estado: str) -> list[Muestra]:
        filas = self._todas("SELECT id FROM muestras WHERE estado = ? ORDER BY id", (nombre_estado,))
        return [self.obtener(f["id"]) for f in filas]

    def reconstruir(self, fila, orden: OrdenDerivacion) -> Muestra:
        """La llama RepositorioOrdenes al cargar una orden."""
        historial = self._cargar_historial(fila["id"])
        if not historial or historial[-1].nuevo != fila["estado"]:
            raise HistorialIncompleto(
                f"La muestra {fila['id']} está {fila['estado']} pero su historial no llega hasta ahí"
            )
        # Una muestra rechazada vuelve con los motivos del último cambio.
        estado = estado_de_muestra(fila["estado"], historial[-1].motivos)
        muestra = reconstruccion.restaurar_muestra(orden, estado, historial)
        self.mapa.registrar("muestra", fila["id"], muestra)
        return muestra

    def _cargar_historial(self, muestra_id: int) -> list[CambioEstado]:
        cambios = []
        for c in self._todas("SELECT * FROM cambios_estado WHERE muestra_id = ? ORDER BY id", (muestra_id,)):
            motivos = tuple(
                MotivoRechazo(m["motivo"])
                for m in self._todas(
                    "SELECT motivo FROM cambio_estado_motivos WHERE cambio_id = ? ORDER BY rowid", (c["id"],))
            )
            cambios.append(CambioEstado(
                c["anterior"], c["nuevo"], a_datetime(c["fecha_hora"]), c["responsable"],
                c["ubicacion"], c["observacion"], motivos))
        return cambios


class RepositorioConservadoras(Repositorio):
    """Agregado: Conservadora con su precinto y las muestras que lleva.

    Las muestras se guardan con su orden (RepositorioOrdenes): para guardar una
    conservadora, sus muestras ya tienen que estar guardadas.
    """

    def guardar(self, conservadora: Conservadora) -> int:
        precinto = conservadora.precinto
        datos = (
            conservadora.codigo, conservadora.capacidad, conservadora.temp_min, conservadora.temp_max,
            None if precinto is None else precinto.numero,
            None if precinto is None else a_texto(precinto.fecha_colocacion),
            None if precinto is None else precinto.responsable,
        )
        id_ = self.mapa.id_de("conservadora", conservadora)
        if id_ is None:
            id_ = self._insertar(
                "INSERT INTO conservadoras (codigo, capacidad, temp_min, temp_max, precinto_numero, "
                "precinto_fecha, precinto_responsable) VALUES (?, ?, ?, ?, ?, ?, ?)", datos)
            self.mapa.registrar("conservadora", id_, conservadora)
        else:
            self.cx.execute(
                "UPDATE conservadoras SET codigo = ?, capacidad = ?, temp_min = ?, temp_max = ?, "
                "precinto_numero = ?, precinto_fecha = ?, precinto_responsable = ? WHERE id = ?",
                datos + (id_,))

        # Las muestras solo se agregan (no se desempaqueta): se inserta lo que todavía no está.
        ya_guardadas = self._contar(
            "SELECT COUNT(*) FROM conservadora_muestras WHERE conservadora_id = ?", (id_,))
        for muestra in conservadora.muestras[ya_guardadas:]:
            self._insertar(
                "INSERT INTO conservadora_muestras (conservadora_id, muestra_id) VALUES (?, ?)",
                (id_, self._id("muestra", muestra)))
        return id_

    def obtener(self, id_: int) -> Conservadora | None:
        existente = self.mapa.obtener("conservadora", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM conservadoras WHERE id = ?", (id_,))
        if fila is None:
            return None

        conservadora = Conservadora(fila["codigo"], fila["capacidad"], fila["temp_min"], fila["temp_max"])
        self.mapa.registrar("conservadora", id_, conservadora)
        muestras = [
            self.ctx.muestras.obtener(m["muestra_id"])
            for m in self._todas(
                "SELECT muestra_id FROM conservadora_muestras WHERE conservadora_id = ? ORDER BY id", (id_,))
        ]
        precinto = None
        if fila["precinto_numero"] is not None:
            precinto = Precinto(fila["precinto_numero"], a_datetime(fila["precinto_fecha"]),
                                fila["precinto_responsable"])
        return reconstruccion.restaurar_conservadora(conservadora, muestras, precinto)

    def obtener_por_codigo(self, codigo: str) -> Conservadora | None:
        fila = self._una("SELECT id FROM conservadoras WHERE codigo = ?", (codigo,))
        return None if fila is None else self.obtener(fila["id"])

    def listar(self) -> list[Conservadora]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM conservadoras ORDER BY codigo")]

    def esta_en_remito(self, conservadora: Conservadora) -> bool:
        return self._contar(
            "SELECT COUNT(*) FROM remito_conservadoras WHERE conservadora_id = ?",
            (self._id("conservadora", conservadora),)) > 0

    def listar_sin_remito(self) -> list[Conservadora]:
        """Las que todavía no viajan en ningún remito."""
        filas = self._todas(
            "SELECT id FROM conservadoras WHERE id NOT IN (SELECT conservadora_id FROM remito_conservadoras) "
            "ORDER BY codigo")
        return [self.obtener(f["id"]) for f in filas]


class RepositorioRemitos(Repositorio):
    """Agregado: RemitoBiologico con sus conservadoras, tramos de envío y recepción.

    Para guardar un remito, sus conservadoras ya tienen que estar guardadas.
    """

    # ---------------- guardar ----------------

    def guardar(self, remito: RemitoBiologico) -> int:
        clinica_id = self.ctx.clinicas.guardar(remito.origen)
        laboratorio_id = self.ctx.laboratorios.guardar(remito.destino)
        datos = (remito.numero, clinica_id, laboratorio_id, remito.estado.nombre)
        id_ = self.mapa.id_de("remito", remito)
        if id_ is None:
            id_ = self._insertar(
                "INSERT INTO remitos (numero, clinica_id, laboratorio_id, estado) VALUES (?, ?, ?, ?)", datos)
            self.mapa.registrar("remito", id_, remito)
        else:
            self.cx.execute(
                "UPDATE remitos SET numero = ?, clinica_id = ?, laboratorio_id = ?, estado = ? WHERE id = ?",
                datos + (id_,))

        # Mientras el remito está abierto se pueden agregar y quitar conservadoras:
        # se reemplaza el conjunto completo.
        self.cx.execute("DELETE FROM remito_conservadoras WHERE remito_id = ?", (id_,))
        for conservadora in remito.conservadoras:
            self._insertar("INSERT INTO remito_conservadoras (remito_id, conservadora_id) VALUES (?, ?)",
                           (id_, self._id("conservadora", conservadora)))

        # Los tramos solo se agregan.
        ya_guardados = self._contar("SELECT COUNT(*) FROM tramos_envio WHERE remito_id = ?", (id_,))
        for tramo in remito.tramos[ya_guardados:]:
            self._insertar(
                "INSERT INTO tramos_envio (remito_id, orden, origen, destino, transportista, salida, "
                "llegada, temperatura) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (id_, tramo.orden, tramo.origen, tramo.destino, tramo.transportista,
                 a_texto(tramo.salida), a_texto(tramo.llegada), tramo.temperatura))

        if remito.recepcion is not None:
            self._guardar_recepcion(remito.recepcion, id_)
        return id_

    def _guardar_recepcion(self, recepcion: Recepcion, remito_id: int) -> None:
        if self._contar("SELECT COUNT(*) FROM recepciones WHERE remito_id = ?", (remito_id,)):
            return  # la recepción se registra una sola vez
        recepcion_id = self._insertar(
            "INSERT INTO recepciones (remito_id, laboratorio_id, responsable, fecha_hora) VALUES (?, ?, ?, ?)",
            (remito_id, self.ctx.laboratorios.guardar(recepcion.laboratorio), recepcion.responsable,
             a_texto(recepcion.fecha_hora)))
        for detalle in recepcion.detalles:
            self._insertar(
                "INSERT INTO detalles_recepcion (recepcion_id, conservadora_id, estado_precinto, "
                "temperatura_llegada, observacion, aceptada) VALUES (?, ?, ?, ?, ?, ?)",
                (recepcion_id, self._id("conservadora", detalle.conservadora), detalle.estado_precinto.value,
                 detalle.temperatura_llegada, detalle.observacion, int(detalle.aceptada)))

    # ---------------- cargar ----------------

    def obtener(self, id_: int) -> RemitoBiologico | None:
        existente = self.mapa.obtener("remito", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM remitos WHERE id = ?", (id_,))
        if fila is None:
            return None

        remito = RemitoBiologico(
            fila["numero"], self.ctx.clinicas.obtener(fila["clinica_id"]),
            self.ctx.laboratorios.obtener(fila["laboratorio_id"]))
        self.mapa.registrar("remito", id_, remito)

        conservadoras = [
            self.ctx.conservadoras.obtener(c["conservadora_id"])
            for c in self._todas(
                "SELECT conservadora_id FROM remito_conservadoras WHERE remito_id = ? ORDER BY id", (id_,))
        ]
        tramos = [
            TramoEnvio(t["orden"], t["origen"], t["destino"], t["transportista"], a_datetime(t["salida"]),
                       a_datetime(t["llegada"]), t["temperatura"])
            for t in self._todas("SELECT * FROM tramos_envio WHERE remito_id = ? ORDER BY orden", (id_,))
        ]
        return reconstruccion.restaurar_remito(
            remito, estado_de_remito(fila["estado"]), conservadoras, tramos, self._cargar_recepcion(id_))

    def _cargar_recepcion(self, remito_id: int) -> Recepcion | None:
        fila = self._una("SELECT * FROM recepciones WHERE remito_id = ?", (remito_id,))
        if fila is None:
            return None
        detalles = [
            DetalleRecepcion(self.ctx.conservadoras.obtener(d["conservadora_id"]),
                             EstadoPrecinto(d["estado_precinto"]), d["temperatura_llegada"], d["observacion"])
            for d in self._todas("SELECT * FROM detalles_recepcion WHERE recepcion_id = ? ORDER BY id", (fila["id"],))
        ]
        return Recepcion(self.ctx.laboratorios.obtener(fila["laboratorio_id"]), fila["responsable"],
                         a_datetime(fila["fecha_hora"]), detalles)

    def obtener_por_numero(self, numero: str) -> RemitoBiologico | None:
        fila = self._una("SELECT id FROM remitos WHERE numero = ?", (numero,))
        return None if fila is None else self.obtener(fila["id"])

    def listar_por_estado(self, nombre_estado: str) -> list[RemitoBiologico]:
        filas = self._todas("SELECT id FROM remitos WHERE estado = ? ORDER BY id", (nombre_estado,))
        return [self.obtener(f["id"]) for f in filas]

    def listar(self) -> list[RemitoBiologico]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM remitos ORDER BY id DESC")]

    def proximo_numero(self) -> str:
        """Número correlativo para un remito nuevo: R-00001, R-00002, ..."""
        return f"R-{self._contar('SELECT COALESCE(MAX(id), 0) + 1 FROM remitos'):05d}"

"""Repositorios de la atención clínica: clínicas, laboratorios, veterinarios (con su agenda),
catálogo de análisis, consultas, órdenes de derivación y comprobantes."""

from __future__ import annotations

from app.dominio.clinica import Clinica
from app.dominio.comprobante import Comprobante, ItemComprobante
from app.dominio.consulta import Consulta
from app.dominio.enums import EstadoTurno, Prioridad, TipoConsulta
from app.dominio.laboratorio import Laboratorio
from app.dominio.mascota import Mascota
from app.dominio.orden_derivacion import OrdenDerivacion
from app.dominio.tipo_analisis import TipoAnalisis
from app.dominio.turno import Turno
from app.dominio.veterinario import Veterinario
from app.persistencia import reconstruccion
from app.persistencia.conversiones import a_datetime, a_decimal, a_texto
from app.persistencia.identidad import ObjetoNoGuardado
from app.persistencia.repositorio_base import Repositorio


class RepositorioClinicas(Repositorio):
    def guardar(self, clinica: Clinica) -> int:
        id_ = self.mapa.id_de("clinica", clinica)
        if id_ is None:
            id_ = self._insertar("INSERT INTO clinicas (nombre, direccion) VALUES (?, ?)",
                                 (clinica.nombre, clinica.direccion))
            self.mapa.registrar("clinica", id_, clinica)
        else:
            self.cx.execute("UPDATE clinicas SET nombre = ?, direccion = ? WHERE id = ?",
                            (clinica.nombre, clinica.direccion, id_))
        return id_

    def obtener(self, id_: int) -> Clinica | None:
        existente = self.mapa.obtener("clinica", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM clinicas WHERE id = ?", (id_,))
        if fila is None:
            return None
        clinica = Clinica(fila["nombre"], fila["direccion"])
        self.mapa.registrar("clinica", id_, clinica)
        return clinica

    def obtener_por_nombre(self, nombre: str) -> Clinica | None:
        fila = self._una("SELECT id FROM clinicas WHERE nombre = ?", (nombre,))
        return None if fila is None else self.obtener(fila["id"])

    def listar(self) -> list[Clinica]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM clinicas ORDER BY nombre")]


class RepositorioLaboratorios(Repositorio):
    def guardar(self, laboratorio: Laboratorio) -> int:
        id_ = self.mapa.id_de("laboratorio", laboratorio)
        if id_ is None:
            id_ = self._insertar("INSERT INTO laboratorios (nombre, direccion) VALUES (?, ?)",
                                 (laboratorio.nombre, laboratorio.direccion))
            self.mapa.registrar("laboratorio", id_, laboratorio)
        else:
            self.cx.execute("UPDATE laboratorios SET nombre = ?, direccion = ? WHERE id = ?",
                            (laboratorio.nombre, laboratorio.direccion, id_))
        return id_

    def obtener(self, id_: int) -> Laboratorio | None:
        existente = self.mapa.obtener("laboratorio", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM laboratorios WHERE id = ?", (id_,))
        if fila is None:
            return None
        laboratorio = Laboratorio(fila["nombre"], fila["direccion"])
        self.mapa.registrar("laboratorio", id_, laboratorio)
        return laboratorio

    def listar(self) -> list[Laboratorio]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM laboratorios ORDER BY nombre")]


class RepositorioTiposAnalisis(Repositorio):
    def guardar(self, tipo: TipoAnalisis) -> int:
        datos = (tipo.nombre, a_texto(tipo.precio), tipo.tipo_muestra, tipo.temp_min,
                 tipo.temp_max, tipo.horas_max_transito)
        id_ = self.mapa.id_de("tipo_analisis", tipo)
        if id_ is None:
            id_ = self._insertar(
                "INSERT INTO tipos_analisis (nombre, precio, tipo_muestra, temp_min, temp_max, "
                "horas_max_transito) VALUES (?, ?, ?, ?, ?, ?)", datos)
            self.mapa.registrar("tipo_analisis", id_, tipo)
        else:
            self.cx.execute(
                "UPDATE tipos_analisis SET nombre = ?, precio = ?, tipo_muestra = ?, temp_min = ?, "
                "temp_max = ?, horas_max_transito = ? WHERE id = ?", datos + (id_,))
        return id_

    def obtener(self, id_: int) -> TipoAnalisis | None:
        existente = self.mapa.obtener("tipo_analisis", id_)
        if existente is not None:
            return existente
        f = self._una("SELECT * FROM tipos_analisis WHERE id = ?", (id_,))
        if f is None:
            return None
        tipo = TipoAnalisis(f["nombre"], a_decimal(f["precio"]), f["tipo_muestra"],
                            f["temp_min"], f["temp_max"], f["horas_max_transito"])
        self.mapa.registrar("tipo_analisis", id_, tipo)
        return tipo

    def obtener_por_nombre(self, nombre: str) -> TipoAnalisis | None:
        fila = self._una("SELECT id FROM tipos_analisis WHERE nombre = ?", (nombre,))
        return None if fila is None else self.obtener(fila["id"])

    def listar(self) -> list[TipoAnalisis]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM tipos_analisis ORDER BY nombre")]


class RepositorioVeterinarios(Repositorio):
    """Agregado: Veterinario con su agenda de turnos.

    OJO con la agenda: `obtener()` la carga por defecto, porque para reservar un turno
    (`agregar_turno`) hace falta tener TODOS los turnos del veterinario y así detectar
    superposiciones. Se puede pedir sin agenda (con_agenda=False) cuando solo interesa
    el veterinario, como al cargar una consulta.
    """

    def __init__(self, contexto) -> None:
        super().__init__(contexto)
        self._agendas_cargadas: set[int] = set()

    # ---------------- guardar ----------------

    def guardar(self, veterinario: Veterinario) -> int:
        clinica_id = self.ctx.clinicas.guardar(veterinario.clinica)
        datos = (veterinario.matricula, veterinario.nombre, veterinario.apellido, clinica_id)
        id_ = self.mapa.id_de("veterinario", veterinario)
        if id_ is None:
            id_ = self._insertar(
                "INSERT INTO veterinarios (matricula, nombre, apellido, clinica_id) VALUES (?, ?, ?, ?)", datos)
            self.mapa.registrar("veterinario", id_, veterinario)
        else:
            self.cx.execute(
                "UPDATE veterinarios SET matricula = ?, nombre = ?, apellido = ?, clinica_id = ? WHERE id = ?",
                datos + (id_,))
        for turno in veterinario.turnos:
            self._guardar_turno(turno, id_)
        return id_

    def _guardar_turno(self, turno: Turno, veterinario_id: int) -> None:
        datos = (veterinario_id, self._id("mascota", turno.mascota), a_texto(turno.inicio),
                 turno.duracion_minutos, turno.estado.value)
        turno_id = self.mapa.id_de("turno", turno)
        if turno_id is None:
            turno_id = self._insertar(
                "INSERT INTO turnos (veterinario_id, mascota_id, inicio, duracion_minutos, estado) "
                "VALUES (?, ?, ?, ?, ?)", datos)
            self.mapa.registrar("turno", turno_id, turno)
        else:
            self.cx.execute(
                "UPDATE turnos SET veterinario_id = ?, mascota_id = ?, inicio = ?, duracion_minutos = ?, "
                "estado = ? WHERE id = ?", datos + (turno_id,))

    # ---------------- cargar ----------------

    def obtener(self, id_: int, con_agenda: bool = True) -> Veterinario | None:
        veterinario = self.mapa.obtener("veterinario", id_)
        if veterinario is None:
            fila = self._una("SELECT * FROM veterinarios WHERE id = ?", (id_,))
            if fila is None:
                return None
            clinica = self.ctx.clinicas.obtener(fila["clinica_id"])
            veterinario = Veterinario(fila["matricula"], fila["nombre"], fila["apellido"], clinica)
            self.mapa.registrar("veterinario", id_, veterinario)
        if con_agenda:
            self.cargar_agenda(veterinario)
        return veterinario

    def de_turno(self, turno_id: int) -> Veterinario | None:
        """El veterinario dueño del turno, con su agenda (y por lo tanto el turno) cargada."""
        fila = self._una("SELECT veterinario_id FROM turnos WHERE id = ?", (turno_id,))
        return None if fila is None else self.obtener(fila["veterinario_id"])

    def obtener_por_matricula(self, matricula: str, con_agenda: bool = True) -> Veterinario | None:
        fila = self._una("SELECT id FROM veterinarios WHERE matricula = ?", (matricula,))
        return None if fila is None else self.obtener(fila["id"], con_agenda)

    def listar_de_clinica(self, clinica: Clinica, con_agenda: bool = False) -> list[Veterinario]:
        clinica_id = self._id("clinica", clinica)
        filas = self._todas("SELECT id FROM veterinarios WHERE clinica_id = ? ORDER BY apellido, nombre",
                            (clinica_id,))
        return [self.obtener(f["id"], con_agenda) for f in filas]

    def cargar_agenda(self, veterinario: Veterinario) -> None:
        id_ = self._id("veterinario", veterinario)
        if id_ in self._agendas_cargadas:
            return
        self._agendas_cargadas.add(id_)
        filas = self._todas("SELECT * FROM turnos WHERE veterinario_id = ? ORDER BY id", (id_,))
        reconstruccion.cargar_agenda(veterinario, [self._turno(f) for f in filas])

    def turno_por_id(self, turno_id: int) -> Turno | None:
        fila = self._una("SELECT * FROM turnos WHERE id = ?", (turno_id,))
        return None if fila is None else self._turno(fila)

    def _turno(self, fila) -> Turno:
        existente = self.mapa.obtener("turno", fila["id"])
        if existente is not None:
            return existente
        mascota = self.ctx.clientes.mascota_por_id(fila["mascota_id"])
        turno = Turno(a_datetime(fila["inicio"]), fila["duracion_minutos"], mascota)
        if EstadoTurno(fila["estado"]) is EstadoTurno.CANCELADO:
            turno.cancelar()
        self.mapa.registrar("turno", fila["id"], turno)
        return turno


class RepositorioConsultas(Repositorio):
    """Agregado: Consulta con sus advertencias, órdenes de derivación (y sus muestras)
    y su comprobante."""

    def guardar(self, consulta: Consulta) -> int:
        mascota_id = self._id("mascota", consulta.mascota)
        veterinario_id = self.ctx.veterinarios.guardar(consulta.veterinario)
        turno_id = None if consulta.turno is None else self._id("turno", consulta.turno)
        datos = (consulta.tipo.value, a_texto(consulta.fecha_hora), mascota_id, veterinario_id,
                 turno_id, consulta.diagnostico, consulta.tratamiento)

        id_ = self.mapa.id_de("consulta", consulta)
        if id_ is None:
            id_ = self._insertar(
                "INSERT INTO consultas (tipo, fecha_hora, mascota_id, veterinario_id, turno_id, "
                "diagnostico, tratamiento) VALUES (?, ?, ?, ?, ?, ?, ?)", datos)
            self.mapa.registrar("consulta", id_, consulta)
        else:
            self.cx.execute(
                "UPDATE consultas SET tipo = ?, fecha_hora = ?, mascota_id = ?, veterinario_id = ?, "
                "turno_id = ?, diagnostico = ?, tratamiento = ? WHERE id = ?", datos + (id_,))

        # Las advertencias solo se agregan: se inserta lo que todavía no está en la base.
        ya_guardadas = self._contar(
            "SELECT COUNT(*) FROM consulta_advertencias WHERE consulta_id = ?", (id_,))
        for texto in consulta.advertencias[ya_guardadas:]:
            self._insertar("INSERT INTO consulta_advertencias (consulta_id, texto) VALUES (?, ?)", (id_, texto))

        for orden in consulta.ordenes:
            self.ctx.ordenes.guardar(orden, id_)
        if consulta.comprobante is not None:
            self.ctx.comprobantes.guardar(consulta.comprobante, id_)
        return id_

    def obtener(self, id_: int) -> Consulta | None:
        existente = self.mapa.obtener("consulta", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT mascota_id FROM consultas WHERE id = ?", (id_,))
        if fila is None:
            return None
        # La consulta forma parte de la historia de su mascota: cargar a la mascota la trae.
        self.ctx.clientes.mascota_por_id(fila["mascota_id"])
        return self.mapa.obtener("consulta", id_)

    def de_orden(self, orden: OrdenDerivacion) -> Consulta | None:
        """La consulta en la que se emitió la orden (la orden no la conoce)."""
        fila = self._una("SELECT consulta_id FROM ordenes_derivacion WHERE id = ?", (self._id("orden", orden),))
        return None if fila is None else self.obtener(fila["consulta_id"])

    def turno_tiene_consulta(self, turno: Turno) -> bool:
        return self._contar("SELECT COUNT(*) FROM consultas WHERE turno_id = ?", (self._id("turno", turno),)) > 0

    def cargar_de_mascota(self, mascota: Mascota) -> None:
        """Carga las consultas de la mascota y las agrega a su historia clínica."""
        filas = self._todas("SELECT * FROM consultas WHERE mascota_id = ? ORDER BY id",
                            (self._id("mascota", mascota),))
        for fila in filas:
            consulta = self._reconstruir(fila, mascota)
            reconstruccion.adjuntar_consulta(mascota.historia_clinica, consulta)

    def _reconstruir(self, fila, mascota: Mascota) -> Consulta:
        veterinario = self.ctx.veterinarios.obtener(fila["veterinario_id"], con_agenda=False)
        turno = None if fila["turno_id"] is None else self.ctx.veterinarios.turno_por_id(fila["turno_id"])
        consulta = reconstruccion.restaurar_consulta(
            TipoConsulta(fila["tipo"]), a_datetime(fila["fecha_hora"]), mascota, veterinario, turno,
            fila["diagnostico"], fila["tratamiento"])
        self.mapa.registrar("consulta", fila["id"], consulta)

        for a in self._todas("SELECT texto FROM consulta_advertencias WHERE consulta_id = ? ORDER BY id",
                             (fila["id"],)):
            consulta.agregar_advertencia(a["texto"])
        for o in self._todas("SELECT id FROM ordenes_derivacion WHERE consulta_id = ? ORDER BY id", (fila["id"],)):
            reconstruccion.adjuntar_orden(consulta, self.ctx.ordenes.obtener(o["id"]))
        self.ctx.comprobantes.cargar(consulta, fila["id"])
        return consulta


class RepositorioOrdenes(Repositorio):
    """Agregado: OrdenDerivacion con sus muestras (una activa a la vez, más las rechazadas)."""

    def guardar(self, orden: OrdenDerivacion, consulta_id: int | None = None) -> int:
        """`consulta_id` solo hace falta la primera vez: una orden nueva nace dentro de una
        consulta (por eso se guarda junto con ella). Las ya guardadas no lo necesitan."""
        tipo_id = self.ctx.tipos_analisis.guardar(orden.tipo_analisis)
        id_ = self.mapa.id_de("orden", orden)
        if id_ is None:
            if consulta_id is None:
                raise ObjetoNoGuardado("Una orden nueva se guarda junto con su consulta")
            id_ = self._insertar(
                "INSERT INTO ordenes_derivacion (consulta_id, tipo_analisis_id, prioridad) VALUES (?, ?, ?)",
                (consulta_id, tipo_id, orden.prioridad.value))
            self.mapa.registrar("orden", id_, orden)
        else:
            self.cx.execute(
                "UPDATE ordenes_derivacion SET tipo_analisis_id = ?, prioridad = ? WHERE id = ?",
                (tipo_id, orden.prioridad.value, id_))
        for muestra in orden.muestras:
            self.ctx.muestras.guardar(muestra, id_)
        return id_

    def obtener(self, id_: int) -> OrdenDerivacion | None:
        existente = self.mapa.obtener("orden", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM ordenes_derivacion WHERE id = ?", (id_,))
        if fila is None:
            return None
        tipo = self.ctx.tipos_analisis.obtener(fila["tipo_analisis_id"])
        orden = OrdenDerivacion(tipo, Prioridad(fila["prioridad"]))
        self.mapa.registrar("orden", id_, orden)
        for m in self._todas("SELECT * FROM muestras WHERE orden_id = ? ORDER BY id", (id_,)):
            self.ctx.muestras.reconstruir(m, orden)
        return orden


class RepositorioComprobantes(Repositorio):
    """El comprobante es inmutable: se guarda una sola vez, al cerrar la consulta."""

    def guardar(self, comprobante: Comprobante, consulta_id: int) -> None:
        if self._contar("SELECT COUNT(*) FROM comprobantes WHERE consulta_id = ?", (consulta_id,)):
            return
        comprobante_id = self._insertar(
            "INSERT INTO comprobantes (consulta_id, fecha_hora) VALUES (?, ?)",
            (consulta_id, a_texto(comprobante.fecha_hora)))
        for item in comprobante.items:
            self._insertar(
                "INSERT INTO items_comprobante (comprobante_id, descripcion, monto, es_laboratorio) "
                "VALUES (?, ?, ?, ?)",
                (comprobante_id, item.descripcion, a_texto(item.monto), int(item.es_laboratorio)))

    def cargar(self, consulta: Consulta, consulta_id: int) -> None:
        """Si la consulta tiene comprobante, lo carga tal como se emitió (sin recalcular precios)."""
        fila = self._una("SELECT * FROM comprobantes WHERE consulta_id = ?", (consulta_id,))
        if fila is None:
            return
        items = [
            ItemComprobante(i["descripcion"], a_decimal(i["monto"]), bool(i["es_laboratorio"]))
            for i in self._todas("SELECT * FROM items_comprobante WHERE comprobante_id = ? ORDER BY id", (fila["id"],))
        ]
        reconstruccion.asignar_comprobante(consulta, Comprobante(consulta, a_datetime(fila["fecha_hora"]), items))

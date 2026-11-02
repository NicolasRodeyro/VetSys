"""Repositorios de especies, clientes, mascotas e historias clínicas."""

from __future__ import annotations

from app.dominio.cliente import Cliente
from app.dominio.enums import Sexo
from app.dominio.especie import Especie, VacunaObligatoria
from app.dominio.mascota import Mascota
from app.persistencia import reconstruccion
from app.persistencia.conversiones import a_fecha, a_texto
from app.persistencia.repositorio_base import Repositorio


class RepositorioEspecies(Repositorio):
    """Agregado: Especie con su esquema de vacunas obligatorias."""

    def guardar(self, especie: Especie) -> int:
        id_ = self.mapa.id_de("especie", especie)
        if id_ is None:
            id_ = self._insertar("INSERT INTO especies (nombre) VALUES (?)", (especie.nombre,))
            self.mapa.registrar("especie", id_, especie)
        else:
            self.cx.execute("UPDATE especies SET nombre = ? WHERE id = ?", (especie.nombre, id_))

        for vacuna in especie.esquema_vacunas:
            if self.mapa.id_de("vacuna", vacuna) is None:
                vacuna_id = self._insertar(
                    "INSERT INTO vacunas_obligatorias "
                    "(especie_id, nombre, edad_aplicacion_meses, refuerzo_cada_meses) VALUES (?, ?, ?, ?)",
                    (id_, vacuna.nombre, vacuna.edad_aplicacion_meses, vacuna.refuerzo_cada_meses),
                )
                self.mapa.registrar("vacuna", vacuna_id, vacuna)
        return id_

    def obtener(self, id_: int) -> Especie | None:
        existente = self.mapa.obtener("especie", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM especies WHERE id = ?", (id_,))
        if fila is None:
            return None
        especie = Especie(fila["nombre"])
        self.mapa.registrar("especie", id_, especie)
        for v in self._todas("SELECT * FROM vacunas_obligatorias WHERE especie_id = ? ORDER BY id", (id_,)):
            vacuna = VacunaObligatoria(v["nombre"], v["edad_aplicacion_meses"], v["refuerzo_cada_meses"])
            especie.agregar_vacuna_obligatoria(vacuna)
            self.mapa.registrar("vacuna", v["id"], vacuna)
        return especie

    def obtener_por_nombre(self, nombre: str) -> Especie | None:
        fila = self._una("SELECT id FROM especies WHERE nombre = ?", (nombre,))
        return None if fila is None else self.obtener(fila["id"])

    def listar(self) -> list[Especie]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM especies ORDER BY nombre")]

    def vacuna_por_id(self, vacuna_id: int) -> VacunaObligatoria:
        vacuna = self.mapa.obtener("vacuna", vacuna_id)
        if vacuna is None:
            fila = self._una("SELECT especie_id FROM vacunas_obligatorias WHERE id = ?", (vacuna_id,))
            self.obtener(fila["especie_id"])  # al cargar la especie se registran sus vacunas
            vacuna = self.mapa.obtener("vacuna", vacuna_id)
        return vacuna


class RepositorioClientes(Repositorio):
    """Agregado: Cliente con sus mascotas, la historia clínica de cada una y sus vacunas
    aplicadas. Las consultas de la historia las guarda RepositorioConsultas, pero se
    cargan junto con la mascota."""

    # ---------------- guardar ----------------

    def guardar(self, cliente: Cliente) -> int:
        datos = (cliente.dni, cliente.nombre, cliente.apellido, cliente.telefono,
                 cliente.email, cliente.direccion, int(cliente.activo))
        id_ = self.mapa.id_de("cliente", cliente)
        if id_ is None:
            id_ = self._insertar(
                "INSERT INTO clientes (dni, nombre, apellido, telefono, email, direccion, activo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", datos)
            self.mapa.registrar("cliente", id_, cliente)
        else:
            self.cx.execute(
                "UPDATE clientes SET dni = ?, nombre = ?, apellido = ?, telefono = ?, email = ?, "
                "direccion = ?, activo = ? WHERE id = ?", datos + (id_,))
        for mascota in cliente.mascotas:
            self._guardar_mascota(mascota, id_)
        return id_

    def _guardar_mascota(self, mascota: Mascota, cliente_id: int) -> None:
        especie_id = self.ctx.especies.guardar(mascota.especie)
        datos = (cliente_id, especie_id, mascota.nombre, mascota.sexo.value,
                 a_texto(mascota.fecha_nacimiento), int(mascota.activa))
        mascota_id = self.mapa.id_de("mascota", mascota)
        if mascota_id is None:
            mascota_id = self._insertar(
                "INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento, activa) "
                "VALUES (?, ?, ?, ?, ?, ?)", datos)
            self.mapa.registrar("mascota", mascota_id, mascota)
        else:
            self.cx.execute(
                "UPDATE mascotas SET cliente_id = ?, especie_id = ?, nombre = ?, sexo = ?, "
                "fecha_nacimiento = ?, activa = ? WHERE id = ?", datos + (mascota_id,))

        historia = mascota.historia_clinica
        historia_id = self.mapa.id_de("historia", historia)
        if historia_id is None:
            historia_id = self._insertar(
                "INSERT INTO historias_clinicas (mascota_id, alergias, antecedentes) VALUES (?, ?, ?)",
                (mascota_id, historia.alergias, historia.antecedentes))
            self.mapa.registrar("historia", historia_id, historia)
        else:
            self.cx.execute(
                "UPDATE historias_clinicas SET alergias = ?, antecedentes = ? WHERE id = ?",
                (historia.alergias, historia.antecedentes, historia_id))

        # Las vacunas aplicadas solo se agregan: se inserta lo que todavía no está en la base.
        ya_guardadas = self._contar(
            "SELECT COUNT(*) FROM vacunas_aplicadas WHERE historia_id = ?", (historia_id,))
        for aplicada in historia.vacunas_aplicadas[ya_guardadas:]:
            self._insertar(
                "INSERT INTO vacunas_aplicadas (historia_id, vacuna_id, fecha) VALUES (?, ?, ?)",
                (historia_id, self._id("vacuna", aplicada.vacuna), a_texto(aplicada.fecha)))

    # ---------------- cargar ----------------

    def obtener(self, id_: int) -> Cliente | None:
        existente = self.mapa.obtener("cliente", id_)
        if existente is not None:
            return existente
        fila = self._una("SELECT * FROM clientes WHERE id = ?", (id_,))
        return None if fila is None else self._cargar(fila)

    def obtener_por_dni(self, dni: str) -> Cliente | None:
        fila = self._una("SELECT id FROM clientes WHERE dni = ?", (dni,))
        return None if fila is None else self.obtener(fila["id"])

    def listar(self) -> list[Cliente]:
        return [self.obtener(f["id"]) for f in self._todas("SELECT id FROM clientes ORDER BY apellido, nombre")]

    def buscar(self, texto: str = "", incluir_inactivos: bool = False) -> list[Cliente]:
        """Clientes cuyo DNI, apellido o nombre contienen `texto` (sin distinguir mayúsculas).
        Por defecto solo los activos."""
        # Los comodines de LIKE que tipee el usuario (% y _) se escapan: se busca el texto literal.
        literal = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patron = "%" + literal + "%"
        filas = self._todas(
            "SELECT id FROM clientes WHERE (dni LIKE ? ESCAPE '\\' OR apellido LIKE ? ESCAPE '\\' "
            "OR nombre LIKE ? ESCAPE '\\') AND (activo = 1 OR ?) ORDER BY apellido, nombre",
            (patron, patron, patron, int(incluir_inactivos)))
        return [self.obtener(f["id"]) for f in filas]

    def mascota_por_id(self, mascota_id: int) -> Mascota | None:
        """Cargar una mascota carga a su cliente (el agregado completo)."""
        existente = self.mapa.obtener("mascota", mascota_id)
        if existente is None:
            fila = self._una("SELECT cliente_id FROM mascotas WHERE id = ?", (mascota_id,))
            if fila is None:
                return None
            self.obtener(fila["cliente_id"])
            existente = self.mapa.obtener("mascota", mascota_id)
        return existente

    def _cargar(self, fila) -> Cliente:
        cliente = Cliente(fila["dni"], fila["nombre"], fila["apellido"], fila["telefono"],
                          fila["email"], fila["direccion"])
        self.mapa.registrar("cliente", fila["id"], cliente)
        for m in self._todas("SELECT * FROM mascotas WHERE cliente_id = ? ORDER BY id", (fila["id"],)):
            self._cargar_mascota(m, cliente)
        # La baja se restaura al final: un cliente dado de baja no admite mascotas nuevas.
        reconstruccion.fijar_activo(cliente, bool(fila["activo"]))
        return cliente

    def _cargar_mascota(self, fila, cliente: Cliente) -> None:
        especie = self.ctx.especies.obtener(fila["especie_id"])
        # El constructor de Mascota la agrega a cliente.mascotas y le crea su historia.
        mascota = Mascota(fila["nombre"], especie, Sexo(fila["sexo"]),
                          a_fecha(fila["fecha_nacimiento"]), cliente)
        self.mapa.registrar("mascota", fila["id"], mascota)
        reconstruccion.fijar_activo(mascota, bool(fila["activa"]))

        historia = mascota.historia_clinica
        h = self._una("SELECT * FROM historias_clinicas WHERE mascota_id = ?", (fila["id"],))
        if h is not None:
            self.mapa.registrar("historia", h["id"], historia)
            historia.alergias = h["alergias"]
            historia.antecedentes = h["antecedentes"]
            for v in self._todas("SELECT * FROM vacunas_aplicadas WHERE historia_id = ? ORDER BY id", (h["id"],)):
                historia.registrar_vacuna(self.ctx.especies.vacuna_por_id(v["vacuna_id"]), a_fecha(v["fecha"]))

        # Las consultas forman parte de la historia: se cargan con la mascota ya registrada.
        self.ctx.consultas.cargar_de_mascota(mascota)

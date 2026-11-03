# PLAN.md — Plan de implementación

Ejecutar **en orden**, una fase por vez. Marcar `[x]` al terminar cada tarea.
Reglas y decisiones de diseño: ver `CLAUDE.md`.

Leyenda: 🧪 = requiere tests · ❓ = requiere decisión del autor antes de implementar

---

## Fase 0 — Setup del proyecto

- [x] Crear la estructura de carpetas de `CLAUDE.md` §3 con `__init__.py`.
- [x] `requirements.txt`: flask, python-dotenv, pytest, matplotlib.
- [x] `.env.example` con `DATABASE_PATH` y `FLASK_SECRET_KEY`; `.gitignore` (incluye `.env`, `__pycache__`, `.venv`).
- [x] `app/__init__.py` con app factory de Flask y una ruta `/` de prueba.
- [x] `app/persistencia/conexion.py`: obtener conexión SQLite (`DATABASE_PATH`), context manager de transacción (commit/rollback).
- [x] `scripts/migrar.py`: aplica en orden los archivos de `db/migraciones/` que no se aplicaron (tabla `migraciones_aplicadas`).
- [x] `app/dominio/excepciones.py` con `ReglaNegocio` y `TransicionInvalida`.
- [x] `README.md` con cómo instalar, configurar `.env`, migrar y correr.

**Aceptación:** `flask run` levanta, `pytest` corre (aunque no haya tests), `scripts/migrar.py` crea la base SQLite.

---

## Fase 0.1 — Persistencia en SQLite

Cambio posterior al análisis del material de la cátedra (semana 8: `sqlite3`; el TP se entrega comprimido y debe correr sin servidor).

- [x] `conexion.py` con `sqlite3`: `obtener_conexion()` (row_factory, `PRAGMA foreign_keys = ON`) y `transaccion()` (commit/rollback).
- [x] `scripts/migrar.py` para SQLite: transaccional por archivo, soporta triggers.
- [x] Tests de integración: commit, rollback, claves foráneas, migraciones (aplica, idempotente, atómica, triggers).
- [x] `requirements.txt` sin psycopg; `.env.example`, `.gitignore`, `README.md` y `CLAUDE.md` actualizados.

---

## Fase 1 — Dominio: clientes y mascotas 🧪

- [x] Enums: `Sexo`.
- [x] `Cliente` (dni, nombre, apellido, telefono, email, direccion, mascotas).
- [x] `Especie` y `VacunaObligatoria` (nombre, edad_aplicacion_meses, refuerzo_cada_meses opcional).
- [x] `Mascota` (responsable **obligatorio**, especie, fecha_nacimiento, `edad_en_meses(fecha)`).
- [x] `VacunaAplicada` y `HistoriaClinica` (alergias, antecedentes, vacunas aplicadas, consultas).
- [x] `HistoriaClinica.vacunas_pendientes(fecha)`: compara el esquema de la especie con la edad y las vacunas aplicadas (incluye refuerzos vencidos).
- [x] Tests: mascota sin responsable falla; vacunas pendientes para cachorro sin vacunas, con vacunas al día y con refuerzo vencido.

**Aceptación:** tests de la fase en verde; `dominio/` no importa nada externo.

---

## Fase 2 — Dominio: atención clínica 🧪

- [x] Enums: `TipoConsulta`, `EstadoTurno`, `Prioridad`.
- [x] `Clinica`, `Veterinario`, `Turno` (inicio, duracion_minutos, `se_superpone_con(otro)`).
- [x] `Veterinario.agregar_turno()`: rechaza superposición; ignora turnos cancelados.
- [x] `TipoAnalisis` (nombre, precio `Decimal`, tipo_muestra, temp_min, temp_max, horas_max_transito).
- [x] `Consulta` (turno opcional para urgencias, diagnóstico, tratamiento, advertencias).
- [x] Registrar consulta en la historia: **advierte** vacunas pendientes, guarda las advertencias y registra igual.
- [x] `OrdenDerivacion` (tipo_analisis, prioridad, lista de muestras, `agregar_muestra()` con regla de una sola activa, `muestra_activa()`).
- [x] Tests: turnos superpuestos / contiguos / con cancelado; urgencia sin turno; consulta con vacunas pendientes se registra con advertencia; orden rechaza segunda muestra activa y acepta re-extracción tras rechazo.

---

## Fase 3 — Dominio: Muestra con State + Observer 🧪

- [x] `EstadoMuestra` abstracta: `empaquetar`, `despachar`, `recibir(aceptada, motivos)`, `analizar`, `es_final`, `nombre` (por defecto lanzan `TransicionInvalida`).
- [x] Estados concretos: `Extraida`, `Empaquetada`, `EnTransito`, `Recibida`, `Analizada`, `Rechazada` (guarda motivos).
- [x] Enum `MotivoRechazo`.
- [x] `CambioEstado` (anterior, nuevo, fecha_hora, responsable, ubicacion, observacion) — inmutable (`dataclass(frozen=True)`).
- [x] `ObservadorMuestra` + `RegistroTrazabilidad`, `AlertaRechazo`, `NotificadorCliente`.
- [x] `Muestra`: delega en el estado; `cambiar_estado()` notifica a los observadores; `esta_activa()`; historial de solo lectura hacia afuera.
- [x] Tests: recorrido completo feliz; rechazo desde En tránsito; cada transición inválida lanza `TransicionInvalida`; el historial registra cada cambio en orden; `AlertaRechazo` solo reacciona a Rechazada.

**Aceptación:** la clase `Muestra` no contiene ningún `if` sobre el estado.

---

## Fase 4 — Dominio: conservadora, remito con State, envío y recepción 🧪

- [x] `Precinto` (numero, fecha_colocacion, responsable) y enum `EstadoPrecinto`.
- [x] `Conservadora` (capacidad, temp_min, temp_max, muestras, precinto): `agregar_muestra()` valida estado Extraída, compatibilidad de temperatura con el `TipoAnalisis` y capacidad; luego llama a `muestra.empaquetar()`. `precintar()`.
- [x] `Laboratorio`, `TramoEnvio` (orden, origen, destino, transportista, salida, llegada, temperatura).
- [x] `EstadoRemito` abstracta + `Abierto`, `Cerrado`, `EnTransito`, `Recibido`, `RecibidoParcial`, `Rechazado`.
- [x] `RemitoBiologico`: delega en el estado (agregar/quitar conservadora, cerrar, despachar, registrar tramo, registrar recepción).
- [x] `Recepcion` y `DetalleRecepcion`: el detalle evalúa precinto y temperatura de llegada contra el rango de la conservadora y calcula `aceptada` y `motivos`.
- [x] Tests: cerrar sin conservadoras / con una sin precinto falla; despachar propaga En tránsito; recepción total OK, parcial y total rechazada; agregar conservadora a remito cerrado falla; muestra incompatible en conservadora falla.

---

## Fase 5 — Dominio: resultados y comprobante 🧪

- [x] `ResultadoAnalisis` y `ValorResultado` (parametro, valor, unidad, ref_min, ref_max, `fuera_de_rango()`).
- [x] Registrar resultado → `muestra.analizar()`.
- [x] `Comprobante` e `ItemComprobante`: se genera al cerrar la consulta con un ítem por la consulta y uno por cada orden de derivación (precio del `TipoAnalisis`). Total con `Decimal`.
- [x] Tests: resultado sobre muestra no recibida falla; comprobante con y sin derivación; re-extracción no genera nuevo cargo.

**Aceptación de las fases 1–5:** todo el dominio testeado sin base de datos.

---

## Fase 6 — Base de datos y repositorios

- [x] `db/migraciones/001_inicial.sql`: tablas para todas las entidades, FKs, `CHECK`s de estados, índices en FKs y fechas.
- [x] `002_trazabilidad_inmutable.sql`: trigger (`RAISE(ABORT, ...)`) que impide UPDATE/DELETE sobre `cambios_estado`.
- [x] Repositorios: clientes/mascotas (con historia y vacunas), especies, clínicas/veterinarios/turnos, tipos de análisis, consultas/órdenes, muestras (con historial), conservadoras, remitos (con tramos), recepciones, resultados, comprobantes.
- [x] Mapeo de estados texto ↔ clase en un solo lugar por State.
- [x] `db/seed.sql`: 2 clínicas, 1 laboratorio, 4 veterinarios, especies con esquema de vacunas, 5 tipos de análisis, 10 clientes con mascotas.
- [x] Tests de integración: guardar y recuperar una muestra con su historial y estado; el trigger bloquea UPDATE en `cambios_estado`.

---

## Fase 7 — Servicios (casos de uso)

Cada uno en una transacción; suscriben los observadores al cargar muestras.

- [x] Clientes y mascotas (alta, baja lógica, modificación, búsqueda).
- [x] Turnos (reservar, cancelar).
- [x] Registrar consulta (con advertencias de vacunas), emitir orden, cerrar consulta y emitir comprobante.
- [x] Registrar extracción de muestra.
- [x] Empaquetar muestra en conservadora, precintar.
- [x] Remito: crear, agregar conservadora, cerrar, despachar, registrar tramo.
- [x] Registrar recepción.
- [x] Registrar resultado.
- [x] Re-extracción de una muestra rechazada.
- [x] Además, para cubrir los procesos obligatorios desde la interfaz: historia clínica y vacunas aplicadas, actualizar la consulta, catálogos y consultas de lectura (listados, trazabilidad de una muestra).
- [x] Sanitización de entradas: validar y normalizar los datos que llegan de la interfaz (DNI, email, fechas, campos vacíos) antes de pasarlos al dominio.

---

## Fase 8 — Interfaz (Flet)

**Decisión tomada: Flet** (Unidad 3 de la cátedra, guía de Flet). La interfaz solo llama a `servicios/` y `reportes/`; una clase por pantalla.

- [x] Reemplazar Flask por Flet: `requirements.txt`, `app/web/` pasa a `app/ui/`, archivo de arranque (`main.py`), `README.md` y `.env.example` (sin `FLASK_SECRET_KEY`).
- [x] Ventana principal con navegación por proceso y mensajes al usuario (SnackBar o diálogo) para los errores de `ReglaNegocio` / `TransicionInvalida` / `EntradaInvalida`.
- [x] Pantallas: clientes, mascotas (con historia clínica y advertencias de vacunas), agenda/turnos, consultas, muestras, remitos, recepción, resultados, comprobantes.
- [x] Pantalla de **trazabilidad de una muestra**: línea de tiempo del historial.
- [x] Pantalla de remito: estado actual y solo los botones de las operaciones permitidas en ese estado.

**Aceptación:** se puede recorrer el flujo completo desde la UI: consulta → orden → muestra → conservadora → remito → envío → recepción → resultado; y el flujo de rechazo con re-extracción.

---

## Fase 9 — Reportes

**Decisión tomada:** se implementan los cuatro primeros candidatos (la consigna pide al menos 4 no triviales).
`horas_max_transito` **se usa**: el reporte de tiempos cuenta las muestras «fuera de plazo». Superar el plazo no rechaza la muestra.

Cada reporte es un módulo de `app/reportes/` con `TITULO`, `DESCRIPCION` y `generar(filtro) -> ResultadoReporte`, y una sola pantalla
(«Reportes») los ofrece. Criterio «no trivial»: calculan algo que no está guardado.

- [x] Infraestructura común: filtros (rango de fechas y clínica), resultado (tabla, notas, gráfico y una tabla de detalle opcional), formato, mediana y percentil, gráficos con matplotlib.
- [x] Tiempos de tránsito y procesamiento desde el historial: mediana y P90 por clínica y transportista (SQLite no tiene `PERCENTILE_CONT`: se obtienen los tiempos con SQL y la mediana y el P90 se calculan en Python), con muestras fuera de plazo.
- [x] Tasa de rechazo por clínica, por motivo y por transportista, con el detalle de cada muestra rechazada (precinto y temperatura de llegada).
- [x] Vacunas pendientes por mascota con días de atraso y responsable de contacto (reutiliza `vacunas_pendientes_con_vencimiento` del dominio).
- [x] Facturación por clínica y servicio con comparación mes contra mes y variación %.
- [ ] (Alternativo, no se implementó) Ratio de derivación por veterinario/clínica y su evolución mensual.
- [x] Pantalla «Reportes»: filtros (rango de fechas, clínica), tabla, gráfico y tabla de detalle.

---

## Fase 10 — Entrega y defensa

- [x] Diagrama de clases (dominio + State + Observer) y diagramas de estado de muestra y remito: `docs/diseno.md`.
- [x] Documento de decisiones de diseño (justificar: comprobante al cierre de consulta, una muestra activa por orden, no desempaquetar, State en remito, advertencia de vacunas): `docs/diseno.md`.
- [x] Guion de demo: flujo feliz + flujo con precinto roto y re-extracción: `docs/demo-y-coloquio.md`.
- [ ] Entrega: archivo comprimido con el código fuente (sin `.env`, `.venv` ni `vetsys.db`), que corra en una máquina limpia siguiendo el `README.md`: instalar, `python scripts/migrar.py`, datos de prueba y correr.
- [ ] Preparar el coloquio: todos los integrantes presentes y capaces de explicar cualquier parte del código.

La guía de preguntas está preparada en `docs/demo-y-coloquio.md`; la presencia y preparación efectiva de los integrantes se verifica con el equipo.

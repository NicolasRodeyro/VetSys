# PLAN.md — Plan de implementación

Ejecutar **en orden**, una fase por vez. Marcar `[x]` al terminar cada tarea.
Reglas y decisiones de diseño: ver `CLAUDE.md`.

Leyenda: 🧪 = requiere tests · ❓ = requiere decisión del autor antes de implementar

---

## Fase 0 — Setup del proyecto

- [x] Crear la estructura de carpetas de `CLAUDE.md` §3 con `__init__.py`.
- [x] `requirements.txt`: flask, psycopg[binary], python-dotenv, pytest, matplotlib.
- [x] `.env.example` con `DATABASE_URL` y `FLASK_SECRET_KEY`; `.gitignore` (incluye `.env`, `__pycache__`, `.venv`).
- [x] `app/__init__.py` con app factory de Flask y una ruta `/` de prueba.
- [ ] `app/persistencia/conexion.py`: obtener conexión desde `DATABASE_URL`, context manager de transacción (commit/rollback).
- [ ] `scripts/migrar.py`: aplica en orden los archivos de `db/migraciones/` que no se aplicaron (tabla `migraciones_aplicadas`).
- [ ] `app/dominio/excepciones.py` con `ReglaNegocio` y `TransicionInvalida`.
- [ ] `README.md` con cómo instalar, configurar `.env`, migrar y correr.

**Aceptación:** `flask run` levanta, `pytest` corre (aunque no haya tests), `scripts/migrar.py` conecta a Supabase.

---

## Fase 1 — Dominio: clientes y mascotas 🧪

- [ ] Enums: `Sexo`.
- [ ] `Cliente` (dni, nombre, apellido, telefono, email, direccion, mascotas).
- [ ] `Especie` y `VacunaObligatoria` (nombre, edad_aplicacion_meses, refuerzo_cada_meses opcional).
- [ ] `Mascota` (responsable **obligatorio**, especie, fecha_nacimiento, `edad_en_meses(fecha)`).
- [ ] `VacunaAplicada` y `HistoriaClinica` (alergias, antecedentes, vacunas aplicadas, consultas).
- [ ] `HistoriaClinica.vacunas_pendientes(fecha)`: compara el esquema de la especie con la edad y las vacunas aplicadas (incluye refuerzos vencidos).
- [ ] Tests: mascota sin responsable falla; vacunas pendientes para cachorro sin vacunas, con vacunas al día y con refuerzo vencido.

**Aceptación:** tests de la fase en verde; `dominio/` no importa nada externo.

---

## Fase 2 — Dominio: atención clínica 🧪

- [ ] Enums: `TipoConsulta`, `EstadoTurno`, `Prioridad`.
- [ ] `Clinica`, `Veterinario`, `Turno` (inicio, duracion_minutos, `se_superpone_con(otro)`).
- [ ] `Veterinario.agregar_turno()`: rechaza superposición; ignora turnos cancelados.
- [ ] `TipoAnalisis` (nombre, precio `Decimal`, tipo_muestra, temp_min, temp_max, horas_max_transito).
- [ ] `Consulta` (turno opcional para urgencias, diagnóstico, tratamiento, advertencias).
- [ ] Registrar consulta en la historia: **advierte** vacunas pendientes, guarda las advertencias y registra igual.
- [ ] `OrdenDerivacion` (tipo_analisis, prioridad, lista de muestras, `agregar_muestra()` con regla de una sola activa, `muestra_activa()`).
- [ ] Tests: turnos superpuestos / contiguos / con cancelado; urgencia sin turno; consulta con vacunas pendientes se registra con advertencia; orden rechaza segunda muestra activa y acepta re-extracción tras rechazo.

---

## Fase 3 — Dominio: Muestra con State + Observer 🧪

- [ ] `EstadoMuestra` abstracta: `empaquetar`, `despachar`, `recibir(aceptada, motivos)`, `analizar`, `es_final`, `nombre` (por defecto lanzan `TransicionInvalida`).
- [ ] Estados concretos: `Extraida`, `Empaquetada`, `EnTransito`, `Recibida`, `Analizada`, `Rechazada` (guarda motivos).
- [ ] Enum `MotivoRechazo`.
- [ ] `CambioEstado` (anterior, nuevo, fecha_hora, responsable, ubicacion, observacion) — inmutable (`dataclass(frozen=True)`).
- [ ] `ObservadorMuestra` + `RegistroTrazabilidad`, `AlertaRechazo`, `NotificadorCliente`.
- [ ] `Muestra`: delega en el estado; `cambiar_estado()` notifica a los observadores; `esta_activa()`; historial de solo lectura hacia afuera.
- [ ] Tests: recorrido completo feliz; rechazo desde En tránsito; cada transición inválida lanza `TransicionInvalida`; el historial registra cada cambio en orden; `AlertaRechazo` solo reacciona a Rechazada.

**Aceptación:** la clase `Muestra` no contiene ningún `if` sobre el estado.

---

## Fase 4 — Dominio: conservadora, remito con State, envío y recepción 🧪

- [ ] `Precinto` (numero, fecha_colocacion, responsable) y enum `EstadoPrecinto`.
- [ ] `Conservadora` (capacidad, temp_min, temp_max, muestras, precinto): `agregar_muestra()` valida estado Extraída, compatibilidad de temperatura con el `TipoAnalisis` y capacidad; luego llama a `muestra.empaquetar()`. `precintar()`.
- [ ] `Laboratorio`, `TramoEnvio` (orden, origen, destino, transportista, salida, llegada, temperatura).
- [ ] `EstadoRemito` abstracta + `Abierto`, `Cerrado`, `EnTransito`, `Recibido`, `RecibidoParcial`, `Rechazado`.
- [ ] `RemitoBiologico`: delega en el estado (agregar/quitar conservadora, cerrar, despachar, registrar tramo, registrar recepción).
- [ ] `Recepcion` y `DetalleRecepcion`: el detalle evalúa precinto y temperatura de llegada contra el rango de la conservadora y calcula `aceptada` y `motivos`.
- [ ] Tests: cerrar sin conservadoras / con una sin precinto falla; despachar propaga En tránsito; recepción total OK, parcial y total rechazada; agregar conservadora a remito cerrado falla; muestra incompatible en conservadora falla.

---

## Fase 5 — Dominio: resultados y comprobante 🧪

- [ ] `ResultadoAnalisis` y `ValorResultado` (parametro, valor, unidad, ref_min, ref_max, `fuera_de_rango()`).
- [ ] Registrar resultado → `muestra.analizar()`.
- [ ] `Comprobante` e `ItemComprobante`: se genera al cerrar la consulta con un ítem por la consulta y uno por cada orden de derivación (precio del `TipoAnalisis`). Total con `Decimal`.
- [ ] Tests: resultado sobre muestra no recibida falla; comprobante con y sin derivación; re-extracción no genera nuevo cargo.

**Aceptación de las fases 1–5:** todo el dominio testeado sin base de datos.

---

## Fase 6 — Base de datos y repositorios

- [ ] `db/migraciones/001_inicial.sql`: tablas para todas las entidades, FKs, `CHECK`s de estados, índices en FKs y fechas.
- [ ] `002_trazabilidad_inmutable.sql`: trigger que impide UPDATE/DELETE sobre `cambios_estado`.
- [ ] Repositorios: clientes/mascotas (con historia y vacunas), especies, clínicas/veterinarios/turnos, tipos de análisis, consultas/órdenes, muestras (con historial), conservadoras, remitos (con tramos), recepciones, resultados, comprobantes.
- [ ] Mapeo de estados texto ↔ clase en un solo lugar por State.
- [ ] `db/seed.sql`: 2 clínicas, 1 laboratorio, 4 veterinarios, especies con esquema de vacunas, 5 tipos de análisis, 10 clientes con mascotas.
- [ ] Tests de integración: guardar y recuperar una muestra con su historial y estado; el trigger bloquea UPDATE en `cambios_estado`.

---

## Fase 7 — Servicios (casos de uso)

Cada uno en una transacción; suscriben los observadores al cargar muestras.

- [ ] Clientes y mascotas (alta, baja lógica, modificación, búsqueda).
- [ ] Turnos (reservar, cancelar).
- [ ] Registrar consulta (con advertencias de vacunas), emitir orden, cerrar consulta y emitir comprobante.
- [ ] Registrar extracción de muestra.
- [ ] Empaquetar muestra en conservadora, precintar.
- [ ] Remito: crear, agregar conservadora, cerrar, despachar, registrar tramo.
- [ ] Registrar recepción.
- [ ] Registrar resultado.
- [ ] Re-extracción de una muestra rechazada.

---

## Fase 8 — Interfaz web (Flask)

- [ ] Layout base (Jinja2) con navegación por proceso y mensajes flash para errores de `ReglaNegocio` / `TransicionInvalida`.
- [ ] Blueprints: clientes, mascotas (con historia clínica y advertencias de vacunas), agenda/turnos, consultas, muestras, remitos, recepción, resultados, comprobantes.
- [ ] Vista de **trazabilidad de una muestra**: línea de tiempo del historial.
- [ ] Vista de remito: estado actual y solo los botones de las operaciones permitidas en ese estado.

**Aceptación:** se puede recorrer el flujo completo desde la UI: consulta → orden → muestra → conservadora → remito → envío → recepción → resultado; y el flujo de rechazo con re-extracción.

---

## Fase 9 — Reportes ❓

Antes de empezar, el autor confirma cuáles 4 implementar y qué hacer con `horas_max_transito` (usarlo en un reporte o eliminarlo).

Candidatos (criterio "no trivial": calculan algo que no está guardado):

- [ ] Tiempos de tránsito y procesamiento desde el historial: mediana y P90 (`PERCENTILE_CONT`) por clínica y transportista, con muestras fuera de rango.
- [ ] Tasa de rechazo por clínica, por motivo y por tramo de la cadena de envío.
- [ ] Vacunas pendientes por mascota con días de atraso y responsable de contacto (reutiliza `vacunas_pendientes`).
- [ ] Facturación por clínica y servicio con comparación mes contra mes y variación %.
- [ ] (Alternativo) Ratio de derivación por veterinario/clínica y su evolución mensual.

Para cada uno: filtros (rango de fechas, clínica), tabla y gráfico.

---

## Fase 10 — Entrega y defensa

- [ ] Diagrama de clases (dominio + State + Observer) y diagramas de estado de muestra y remito.
- [ ] Documento de decisiones de diseño (justificar: comprobante al cierre de consulta, una muestra activa por orden, no desempaquetar, State en remito, advertencia de vacunas).
- [ ] Guion de demo: flujo feliz + flujo con precinto roto y re-extracción.
- [ ] Plan B para la defensa: correr con Postgres local cambiando `DATABASE_URL`.

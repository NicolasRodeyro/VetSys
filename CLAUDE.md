# CLAUDE.md — TP Integrador DAO 2026: Veterinaria (Tema 2)

Sistema para una red de clínicas veterinarias que integra la atención clínica con la derivación de muestras biológicas a un laboratorio central, garantizando **trazabilidad completa** desde la extracción hasta el resultado.

Materia: Desarrollo de Aplicaciones con Objetos (DAO) — Ingeniería en Sistemas de Información, UTN.
El plan de trabajo está en `PLAN.md`. **Leelo antes de empezar cualquier tarea.**

---

## 1. Cómo trabajar en este repo

- **Seguí `PLAN.md` en orden.** Trabajá una fase por vez. No adelantes tareas de fases futuras.
- Al terminar una tarea, marcala con `[x]` en `PLAN.md`. Al terminar una fase, verificá sus criterios de aceptación y corré los tests.
- **Las decisiones de diseño de la sección 4 ya están tomadas.** No las cambies por tu cuenta. Si encontrás un problema con alguna, frená y explicalo antes de modificar nada.
- Si algo no está definido acá ni en el plan, **preguntá** antes de inventar reglas de negocio.
- Esto es un TP universitario que el autor tiene que **defender oralmente**. Por eso:
  - Preferí código simple y explícito sobre código "ingenioso".
  - Al cerrar cada tarea, explicá brevemente **qué hiciste y por qué** (qué patrón o principio aplica).
  - No agregues librerías, capas ni abstracciones que no estén en este documento.
- Commits chicos, uno por tarea, en español: `feat(dominio): estados de la muestra con patrón State`.

---

## 2. Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12, con type hints |
| Interfaz | Flet (ventanas, controles y grillas, como en la guía de la cátedra) |
| Base de datos | SQLite (archivo `vetsys.db`) |
| Acceso a datos | módulo `sqlite3` de la biblioteca estándar, con SQL escrito a mano |
| Tests | pytest |
| Config | `python-dotenv` (archivo `.env` opcional, nunca commiteado) |
| Reportes | SQL (SQLite) + matplotlib (gráficos) |

**Prohibido:**
- ORMs (SQLAlchemy ORM, Django ORM, Peewee, etc.).
- Motores de base de datos con servidor (Postgres, MySQL, etc.) y servicios en la nube (Supabase, etc.).
- Credenciales en el código o en el repo.

**Por qué SQLite:** es el motor que enseña la cátedra (semana 8) y el TP se entrega como un archivo comprimido con el código fuente: tiene que correr en cualquier máquina sin instalar un servidor ni configurar credenciales.

Conexión: `sqlite3.connect()` sobre el archivo indicado por `DATABASE_PATH` (opcional, en `.env`; por defecto `vetsys.db` en la raíz del repo). En cada conexión se activa `PRAGMA foreign_keys = ON`.

---

## 3. Arquitectura en capas

```
app/
├── ui/             # Flet: una clase por pantalla (presentación)
├── servicios/      # Casos de uso (registrar_recepcion, despachar_remito, ...)
├── dominio/        # Clases puras: entidades, estados (State), observadores (Observer)
├── persistencia/   # Conexión, repositorios, mapeo fila <-> objeto
└── reportes/       # Consultas de reportes y generación de gráficos
db/
├── migraciones/    # 001_inicial.sql, 002_..., en orden
└── seed.sql        # Datos de prueba
tests/
├── dominio/        # Tests sin base de datos
└── integracion/    # Tests con base de datos
```

**Reglas de dependencia (obligatorias):**

- `dominio/` **no importa nada** de `web/`, `servicios/`, `persistencia/` ni de Flet o sqlite3. Es Python puro.
- `servicios/` usa `dominio/` y `persistencia/`. Orquesta: carga objetos, llama métodos de dominio, guarda y maneja la transacción.
- `ui/` solo llama a `servicios/` y `reportes/`. **No hay lógica de negocio en las pantallas ni SQL en la capa de interfaz.**
- `persistencia/` conoce al dominio (para construir objetos) pero el dominio no la conoce.
- Las reglas de negocio viven en el **dominio**, en la clase experta (GRASP Experto), no en los servicios.
- **Servicios** (`servicios/`): cada función pública es un caso de uso y corre en **una transacción** (`caso_de_uso()`). Recibe ids o datos simples (lo que maneja la interfaz) y devuelve objetos del dominio. Antes de llegar al dominio, las entradas se validan y normalizan con `validaciones.py` (**sanitización**). Al cargar muestras, suscriben `RegistroTrazabilidad`. Sus errores (`EntradaInvalida`, `NoEncontrado`) heredan de `ReglaNegocio`, así la interfaz atrapa todo con un solo `except ReglaNegocio`. Para tener datos con que probar: `python scripts/sembrar.py` (o el botón «Cargar datos de prueba» de la ventana).
- **Reportes** (`reportes/`): solo lectura, calculan algo que no está guardado. Cada uno es un módulo con `TITULO`, `DESCRIPCION` y `generar(filtro: FiltroReporte) -> ResultadoReporte` (sin nada de Flet), registrado en `REPORTES`; una sola pantalla los muestra. Estructura de un reporte: lectura con SQL parametrizado, cálculo en **Python puro** (se prueba sin base) y armado del resultado. Los montos (TEXT/Decimal) se suman con `Decimal` en Python, nunca con `SUM()` de SQL. La mediana y el P90 se calculan en Python (`estadistica.percentil`, interpolación lineal). Una muestra cuenta una vez por cada transportista que intervino en su remito. El rango de fechas se aplica a la fecha que cada reporte indica en su descripción. Los tests de los que dependen del historial insertan las fechas con SQL (`tests/reportes/datos.py`): los servicios sellan con la hora real. Los valores esperados se calculan a mano.
- **Interfaz** (`ui/`): una clase por pantalla (`Pantalla`), con `build()` y los controles como atributos. Solo llama a `servicios/` (un test lo verifica: no importa dominio ni persistencia y no tiene SQL). Todo manejador de evento lleva `@manejador` (garantiza el redibujado: Flet no redibuja solo si durante el evento se mostró un mensaje) y los botones creados en bucles usan `functools.partial`, nunca un `lambda` con valor por defecto (Flet le pasaría el evento). Los errores se atrapan en un solo lugar, `Pantalla.ejecutar()`, con un único `except ReglaNegocio`. El «Operador» del encabezado es el responsable de cada operación. Los botones de cada remito/muestra salen de `estado.operaciones_permitidas`, no de una tabla duplicada.

---

## 4. Decisiones de diseño (ya tomadas)

### 4.1 Modelo de dominio

**Clientes y mascotas:** Cliente, Mascota, Especie, VacunaObligatoria, HistoriaClinica, VacunaAplicada
**Atención clínica:** Clinica, Veterinario, Turno, Consulta, OrdenDerivacion, TipoAnalisis
**Empaquetado y envío:** Muestra, CambioEstado, Conservadora, Precinto, RemitoBiologico, TramoEnvio, Laboratorio, Recepcion, DetalleRecepcion
**Resultados y cobro:** ResultadoAnalisis, ValorResultado, Comprobante, ItemComprobante

Relaciones y decisiones clave:

- **Mascota tiene exactamente un responsable** (Cliente), obligatorio en el constructor.
- **Baja lógica** de Cliente y Mascota (nada se borra: conservan sus consultas, muestras y comprobantes). No se da de baja a un cliente con mascotas activas, no se le agregan mascotas a un cliente de baja, y una mascota de baja no se atiende ni recibe turnos.
- **HistoriaClinica es clase propia**: alergias, antecedentes, vacunas aplicadas y consultas. Es la experta en el estado sanitario (`vacunas_pendientes(fecha)`).
- **El esquema de vacunas cuelga de Especie** (lista de VacunaObligatoria con edad de aplicación y refuerzo).
- **TipoAnalisis es una clase** (no enum): nombre, precio, tipo de muestra, rango de temperatura (min, max), horas máximas de tránsito. Es un catálogo.
- **Consulta** tiene tipo (Control, Consulta, Urgencia). El turno es opcional (las urgencias no tienen turno).
- **OrdenDerivacion 1..* Muestra, con una sola muestra activa** (no rechazada) a la vez. Permite re-extracción.
- **Conservadora 1..* Muestra.** Una conservadora puede llevar muestras de distintas órdenes.
- **RemitoBiologico 1..* Conservadora.** Un remito tiene una lista de TramoEnvio.
- **El precinto es de la conservadora**, no de la muestra. `EstadoPrecinto` (INTACTO / ROTO) es el estado en que lo encuentra el laboratorio al recibir: se registra en el `DetalleRecepcion`.
- **Recepcion 1..* DetalleRecepcion**: un detalle por conservadora (estado del precinto, temperatura de llegada, aceptada, motivos de rechazo).
- **Comprobante único, emitido al cerrar la consulta**: incluye la consulta y los análisis derivados (precio desde TipoAnalisis). El cliente paga al irse de la clínica. Los honorarios de la consulta se cargan al cerrarla (`Consulta.cerrar(honorarios, fecha_hora)`); se cobra una vez por orden, no por muestra. Una consulta cerrada ya no admite nuevas órdenes. Cada `ItemComprobante` indica si es un servicio de laboratorio (para el reporte de facturación).
- **La muestra no vuelve a la clínica.** Vuelve el resultado (informe).
- `ResultadoAnalisis` **no tiene estados propios**. Registrarlo pasa la muestra a *Analizada*.

### 4.2 Ciclo de vida de la muestra

```
[Extraída] → [Empaquetada] → [En tránsito] → [Recibida] → [Analizada]
                                   └──────────→ [Rechazada]
```

| Transición | Evento | Quién |
|---|---|---|
| Extraída → Empaquetada | Se agrega a una conservadora | Clínica |
| Empaquetada → En tránsito | Se despacha el remito | Clínica |
| En tránsito → Recibida | Recepción OK de su conservadora | Laboratorio |
| En tránsito → Rechazada | Precinto roto o temperatura fuera de rango | Laboratorio |
| Recibida → Analizada | Se registra el resultado | Bioquímico |

- **No se puede desempaquetar** (no existe Empaquetada → Extraída).
- **El rechazo solo ocurre en la recepción del laboratorio.**
- Analizada y Rechazada son estados finales.
- Muestra rechazada → **re-extracción sin cargo**: nueva muestra en la misma orden; el comprobante no cambia.

### 4.3 Ciclo de vida del remito (6 estados, sin Anulado)

```
[Abierto] → [Cerrado] → [En tránsito] ─┬→ [Recibido]          (todas aceptadas)
                                       ├→ [Recibido parcial]  (algunas rechazadas)
                                       └→ [Rechazado]         (todas rechazadas)
```

| Estado | Operaciones permitidas |
|---|---|
| Abierto | agregar/quitar conservadora, cerrar |
| Cerrado | despachar |
| En tránsito | registrar tramo, registrar recepción |
| Recibido / RecibidoParcial / Rechazado | ninguna (finales) |

- **Cerrar** exige al menos una conservadora y que **todas tengan precinto**.
- **Despachar** llama a `despachar()` en cada muestra.
- **Registrar recepción** llama a `recibir(aceptada, motivos)` en cada muestra según el detalle de su conservadora, y calcula el estado final a partir de los detalles.
- Quitar una conservadora del remito (en Abierto) **no es desempaquetar**: las muestras siguen en la conservadora.

### 4.4 Patrones de diseño

**1. State — en Muestra y en RemitoBiologico.**
- Clase abstracta (`EstadoMuestra`, `EstadoRemito`) que implementa **todas** las operaciones lanzando `TransicionInvalida`.
- Cada estado concreto **sobrescribe solo las operaciones que permite**.
- La entidad **delega** en su estado actual. **Nada de `if estado == ...` en la entidad.**
- Como en la guía de la cátedra, los métodos del estado reciben la muestra (o el remito) y es el estado quien llama a `cambiar_estado(...)`.
- Los dos State colaboran: el remito no cambia el estado de las muestras, les pide `despachar()` / `recibir()`, y el estado de cada muestra valida la transición.

**2. Observer — la Muestra es el sujeto.**
- `ObservadorMuestra.actualizar(muestra, cambio)`: `cambio` es un `CambioEstado` con el estado anterior y el nuevo, la fecha, el responsable, la ubicación, la observación y los motivos de rechazo. Así el observador recibe todo lo que necesita (como en el ejemplo de la cátedra, donde el sujeto le pasa los datos al observador).
- Observadores concretos:
  - `RegistroTrazabilidad`: agrega un `CambioEstado` al historial (obligatorio).
  - `AlertaRechazo`: si pasa a Rechazada, avisa a la clínica para coordinar la re-extracción (obligatorio).
  - `NotificadorCliente`: si pasa a Analizada, avisa al responsable (opcional).
- State y Observer se juntan en `Muestra.cambiar_estado()`: el estado decide la transición y `cambiar_estado()` notifica.
- Los observadores **no se persisten**: los suscribe la capa de servicios al cargar la muestra.

**3. Repository** — un repositorio por agregado en `persistencia/`. Las clases que solo existen dentro de otra (`CambioEstado`, `ValorResultado`, `ItemComprobante`, `DetalleRecepcion`, `VacunaAplicada`) se guardan con su dueña.

### 4.5 Validaciones de negocio y dónde viven

| Validación | Dónde |
|---|---|
| Toda mascota tiene responsable | Constructor de `Mascota` |
| Sin superposición de turnos | `Veterinario.agregar_turno()`: intervalos `[inicio, inicio+duración)`; los turnos cancelados no bloquean |
| Esquema de vacunas | Al registrar una consulta: **se advierte, no se bloquea**. La consulta se registra igual y guarda las advertencias |
| Compatibilidad en conservadora | `Conservadora.agregar_muestra()`: rango de temperatura compatible (el de la conservadora debe quedar dentro del que pide el análisis), capacidad y conservadora sin precintar. Que la muestra esté en Extraída lo valida su propio State (`empaquetar()`) |
| Una muestra activa por orden | `OrdenDerivacion.agregar_muestra()` |
| Precinto roto / temperatura → Rechazada | `DetalleRecepcion` (evalúa precinto y temperatura de llegada) + `EnTransito.recibir()` de la muestra |
| Trazabilidad inmutable | Historial solo se agrega (Observer) + en la base, `cambios_estado` sin UPDATE ni DELETE |

- Motivos de rechazo: enum `MotivoRechazo` (`PRECINTO_ROTO`, `TEMPERATURA_FUERA_DE_RANGO`). Puede haber más de uno. Se guardan en el `CambioEstado`.
- El tiempo máximo de tránsito **no** es causa de rechazo (decisión explícita). `horas_max_transito` se usa en el reporte de tiempos para contar las muestras «fuera de plazo»: solo se informa.

### 4.6 Enum vs. clase

- **Enum** cuando el valor es solo una etiqueta: sexo, prioridad, tipo de consulta, estado del turno, motivo de rechazo, estado del precinto.
- **Clase** cuando tiene datos que usan las reglas de negocio (ej. `TipoAnalisis`).

---

## 5. Convenciones de código

- Nombres del dominio **en español**, `snake_case` para funciones y atributos, `PascalCase` para clases. Sin tildes ni ñ en identificadores (`recepcion`, `anio`).
- Type hints en todas las firmas públicas.
- Atributos internos con `_` y acceso mediante métodos o properties cuando haya invariantes que proteger (ej. no exponer la lista de muestras para que la modifiquen desde afuera).
- Excepciones de dominio propias en `dominio/excepciones.py`: `ReglaNegocio`, `TransicionInvalida`.
- Fechas con `datetime` (hora local, sin zona horaria). Al persistir se guardan como texto ISO 8601.
- Montos con `Decimal`, nunca `float`. Al persistir se guardan como `TEXT` (SQLite no tiene tipo decimal exacto) y el repositorio los convierte a `Decimal`.

## 6. Persistencia

- SQL parametrizado siempre (`?`), **nunca** f-strings con valores.
- Esquema versionado en `db/migraciones/NNN_descripcion.sql`, aplicado en orden con un script `scripts/migrar.py`.
- Los estados se guardan como texto (`'EN_TRANSITO'`) y el repositorio los reconstruye con un diccionario `nombre → clase de estado`.
- Cada caso de uso de `servicios/` corre en **una sola transacción** (si falla algo, rollback de todo).
- La tabla `cambios_estado` tiene un trigger que impide UPDATE y DELETE (`RAISE(ABORT, ...)`).
- Las migraciones se aplican sentencia por sentencia dentro de una transacción; `scripts/migrar.py` ya soporta triggers.
- **Un `Contexto` por caso de uso** (`persistencia/contexto.py`): una conexión (una transacción) más un mapa de identidad compartido por todos los repositorios, que se piden unos a otros lo que necesitan. Uso: `with transaccion() as conexion: ctx = Contexto(conexion)`.
- **Las entidades tienen un atributo `id`** (`None` hasta que se guardan) que asigna la persistencia, para que la interfaz pueda referirse a ellas (una mascota, una consulta, una muestra). El dominio no lo usa en ninguna regla. El mapa de identidad (`persistencia/identidad.py`) relaciona cada objeto con su fila: decide INSERT o UPDATE al guardar, y garantiza que dentro de un contexto cada fila sea un único objeto.
- **Reconstruir no es crear.** Al cargar no se repiten las reglas de creación (una muestra no se vuelve a registrar en su orden, un comprobante no se recalcula con los precios de hoy). `persistencia/reconstruccion.py` es el único módulo que arma objetos salteando sus constructores; los tests de guardar y volver a cargar avisan si el dominio cambia y quedó desfasado.
- **Las listas que solo crecen** (vacunas aplicadas, advertencias, historial de la muestra, tramos, muestras de una conservadora) se guardan insertando únicamente lo nuevo. El historial no se actualiza nunca: el trigger lo impide.
- **Los observadores no se persisten.** Quien carga una muestra suscribe `RegistroTrazabilidad` antes de cambiarle el estado; si no, `guardar` lanza `HistorialIncompleto` en lugar de dejar un historial con huecos.
- La agenda del veterinario se carga por defecto (hace falta completa para detectar superposiciones); `con_agenda=False` solo cuando interesa el veterinario, como al cargar una consulta.

## 7. Tests

- Todo el dominio se testea **sin base de datos** (`tests/dominio/`).
- Los tests de integración usan un archivo SQLite temporal (`tmp_path` de pytest), nunca `vetsys.db`.
- Por cada transición válida, un test. Por cada transición inválida relevante, un test que espere `TransicionInvalida`.
- Por cada validación de negocio, al menos un test del caso OK y uno del caso que falla.
- Correr `pytest` antes de marcar una fase como terminada.

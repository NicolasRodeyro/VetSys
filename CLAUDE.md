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
| Web | Flask (app factory + blueprints) + Jinja2 |
| Base de datos | PostgreSQL alojado en Supabase |
| Acceso a datos | `psycopg` (v3) con SQL escrito a mano |
| Tests | pytest |
| Config | `python-dotenv` (archivo `.env`, nunca commiteado) |
| Reportes | SQL de Postgres + matplotlib (gráficos) |

**Prohibido:**
- ORMs (SQLAlchemy ORM, Django ORM, Peewee, etc.).
- `supabase-py`, la API REST de Supabase o Supabase Auth. Supabase se usa **solo como un Postgres**.
- Credenciales en el código o en el repo.

Conexión: usar la cadena del **Session pooler** de Supabase (`DATABASE_URL` en `.env`). Debe poder apuntarse a un Postgres local cambiando solo esa variable.

---

## 3. Arquitectura en capas

```
app/
├── web/            # Flask: blueprints, rutas, formularios, templates
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

- `dominio/` **no importa nada** de `web/`, `servicios/`, `persistencia/` ni de Flask o psycopg. Es Python puro.
- `servicios/` usa `dominio/` y `persistencia/`. Orquesta: carga objetos, llama métodos de dominio, guarda y maneja la transacción.
- `web/` solo llama a `servicios/` y `reportes/`. **No hay lógica de negocio en las rutas ni SQL en la capa web.**
- `persistencia/` conoce al dominio (para construir objetos) pero el dominio no la conoce.
- Las reglas de negocio viven en el **dominio**, en la clase experta (GRASP Experto), no en los servicios.

---

## 4. Decisiones de diseño (ya tomadas)

### 4.1 Modelo de dominio

**Clientes y mascotas:** Cliente, Mascota, Especie, VacunaObligatoria, HistoriaClinica, VacunaAplicada
**Atención clínica:** Clinica, Veterinario, Turno, Consulta, OrdenDerivacion, TipoAnalisis
**Empaquetado y envío:** Muestra, CambioEstado, Conservadora, Precinto, RemitoBiologico, TramoEnvio, Laboratorio, Recepcion, DetalleRecepcion
**Resultados y cobro:** ResultadoAnalisis, ValorResultado, Comprobante, ItemComprobante

Relaciones y decisiones clave:

- **Mascota tiene exactamente un responsable** (Cliente), obligatorio en el constructor.
- **HistoriaClinica es clase propia**: alergias, antecedentes, vacunas aplicadas y consultas. Es la experta en el estado sanitario (`vacunas_pendientes(fecha)`).
- **El esquema de vacunas cuelga de Especie** (lista de VacunaObligatoria con edad de aplicación y refuerzo).
- **TipoAnalisis es una clase** (no enum): nombre, precio, tipo de muestra, rango de temperatura (min, max), horas máximas de tránsito. Es un catálogo.
- **Consulta** tiene tipo (Control, Consulta, Urgencia). El turno es opcional (las urgencias no tienen turno).
- **OrdenDerivacion 1..* Muestra, con una sola muestra activa** (no rechazada) a la vez. Permite re-extracción.
- **Conservadora 1..* Muestra.** Una conservadora puede llevar muestras de distintas órdenes.
- **RemitoBiologico 1..* Conservadora.** Un remito tiene una lista de TramoEnvio.
- **El precinto es de la conservadora**, no de la muestra.
- **Recepcion 1..* DetalleRecepcion**: un detalle por conservadora (estado del precinto, temperatura de llegada, aceptada, motivos de rechazo).
- **Comprobante único, emitido al cerrar la consulta**: incluye la consulta y los análisis derivados (precio desde TipoAnalisis). El cliente paga al irse de la clínica.
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
- Los dos State colaboran: el remito no cambia el estado de las muestras, les pide `despachar()` / `recibir()`, y el estado de cada muestra valida la transición.

**2. Observer — la Muestra es el sujeto.**
- `ObservadorMuestra.actualizar(muestra, estado_anterior, estado_nuevo)`.
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
| Compatibilidad en conservadora | `Conservadora.agregar_muestra()`: muestra en Extraída, rango de temperatura compatible, capacidad |
| Una muestra activa por orden | `OrdenDerivacion.agregar_muestra()` |
| Precinto roto / temperatura → Rechazada | Recepción por conservadora + `EnTransito.recibir()` |
| Trazabilidad inmutable | Historial solo se agrega (Observer) + en la base, `cambios_estado` sin UPDATE ni DELETE |

- Motivos de rechazo: enum `MotivoRechazo` (`PRECINTO_ROTO`, `TEMPERATURA_FUERA_DE_RANGO`). Puede haber más de uno. Se guardan en el `CambioEstado`.
- El tiempo máximo de tránsito **no** es causa de rechazo (decisión explícita). `horas_max_transito` se revisa en la fase de reportes.

### 4.6 Enum vs. clase

- **Enum** cuando el valor es solo una etiqueta: sexo, prioridad, tipo de consulta, estado del turno, motivo de rechazo, estado del precinto.
- **Clase** cuando tiene datos que usan las reglas de negocio (ej. `TipoAnalisis`).

---

## 5. Convenciones de código

- Nombres del dominio **en español**, `snake_case` para funciones y atributos, `PascalCase` para clases. Sin tildes ni ñ en identificadores (`recepcion`, `anio`).
- Type hints en todas las firmas públicas.
- Atributos internos con `_` y acceso mediante métodos o properties cuando haya invariantes que proteger (ej. no exponer la lista de muestras para que la modifiquen desde afuera).
- Excepciones de dominio propias en `dominio/excepciones.py`: `ReglaNegocio`, `TransicionInvalida`.
- Fechas con `datetime` (con zona horaria `America/Argentina/Cordoba` al persistir).
- Montos con `Decimal`, nunca `float`.

## 6. Persistencia

- SQL parametrizado siempre (`%s`), **nunca** f-strings con valores.
- Esquema versionado en `db/migraciones/NNN_descripcion.sql`, aplicado en orden con un script `scripts/migrar.py`.
- Los estados se guardan como texto (`'EN_TRANSITO'`) y el repositorio los reconstruye con un diccionario `nombre → clase de estado`.
- Cada caso de uso de `servicios/` corre en **una sola transacción** (si falla algo, rollback de todo).
- La tabla `cambios_estado` tiene un trigger que impide UPDATE y DELETE.

## 7. Tests

- Todo el dominio se testea **sin base de datos** (`tests/dominio/`).
- Por cada transición válida, un test. Por cada transición inválida relevante, un test que espere `TransicionInvalida`.
- Por cada validación de negocio, al menos un test del caso OK y uno del caso que falla.
- Correr `pytest` antes de marcar una fase como terminada.

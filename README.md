# VetSys

Sistema para una red de clínicas veterinarias con derivación de muestras a un laboratorio central.
TP Integrador de Desarrollo de Aplicaciones con Objetos (UTN).

Stack: Python 3.12 · Flet 1.0.4 (interfaz) · SQLite (`sqlite3`) · pytest.

## 1. Instalación

Desde la raíz del repo (Windows / PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En Linux/macOS, activar con `source .venv/bin/activate`.

> **La primera vez que se abre la aplicación**, Flet descarga su cliente de escritorio
> (una sola vez, necesita internet). Conviene abrirla una vez con conexión antes de una demostración.

## 2. Usar la aplicación

```powershell
python main.py
```

- La primera vez **crea la base de datos** sola (`vetsys.db`, un archivo SQLite; no hace falta ningún servidor).
- Si la base está vacía, la ventana avisa y ofrece **«Cargar datos de prueba»**: 2 clínicas, 1 laboratorio,
  4 veterinarios, 3 especies con su esquema de vacunas, 5 tipos de análisis y 10 clientes con mascotas.
- Arriba a la derecha está el campo **Operador**: la persona que usa el sistema. Queda registrada como
  responsable de cada operación (extracción, empaquetado, despacho, recepción...).

El menú tiene tres grupos:

| Atención | Laboratorio | Reportes |
|---|---|---|
| Clientes, Mascotas, Turnos, Consultas, Comprobantes | Muestras, Conservadoras, Remitos, Recepción, Resultados | Reportes |

Para empezar un recorrido completo: **Consultas** (registrar consulta y emitir una orden de análisis) →
**Muestras** (extracción) → **Conservadoras** (empaquetar y precintar) → **Remitos** (crear, cerrar, despachar)
→ **Recepción** (el laboratorio constata precinto y temperatura) → **Resultados** → **Comprobantes**.
Si el precinto llega roto, la muestra se rechaza y se re-extrae desde **Muestras**.

### Reportes

La pantalla **Reportes** calcula, al pedirlo, cuatro análisis sobre la operación. Cada uno tiene filtros (rango de fechas y
clínica), una tabla y un gráfico:

| Reporte | Qué muestra |
|---|---|
| Tiempos de tránsito y procesamiento | Mediana y P90 en horas por clínica de origen y por transportista, y cuántas muestras superaron el plazo de su análisis |
| Tasa de rechazo de muestras | Rechazadas sobre las que llegaron, por clínica, transportista y motivo, con el detalle de cada rechazo |
| Vacunas pendientes y días de atraso | Qué vacunas le faltan a cada mascota, hace cuántos días vencieron y cómo contactar al responsable |
| Facturación por clínica y servicio | Lo facturado por mes, clínica y servicio, con la variación contra el mes anterior |

Con los datos de prueba, algunos reportes salen vacíos porque dependen de muestras ya recibidas o de consultas cerradas:
para verlos con movimiento, hay que recorrer el circuito de arriba. El de vacunas pendientes funciona de inmediato.

## 3. Configuración (opcional)

La base es un archivo y no necesita credenciales. Con los valores por defecto no hace falta ningún `.env`.
Para cambiar algo:

```powershell
copy .env.example .env
```

- `DATABASE_PATH`: ruta del archivo de la base (por defecto `vetsys.db` en la raíz del repo).

El archivo `.env` está en `.gitignore` y **nunca se commitea**.

## 4. Scripts de línea de comandos (opcionales)

La aplicación crea la base y ofrece cargar datos de prueba si está vacía. También se puede hacer a mano:

```powershell
python scripts/migrar.py     # crea la base / aplica las migraciones de db/migraciones/ que falten
python scripts/sembrar.py    # carga los datos de prueba (no hace nada si ya hay datos)
```

Para empezar de cero, borrar `vetsys.db`.

## 5. Tests

```powershell
pytest
```

Los tests de `dominio/` no usan base de datos. Los de integración, servicios e interfaz usan un archivo
SQLite temporal, nunca `vetsys.db`. Los de la interfaz prueban la lógica de cada pantalla sin abrir una ventana.

## Diseño y defensa

- [Diagramas y decisiones de diseño](docs/diseno.md).
- [Guion de demostración y preguntas para el coloquio](docs/demo-y-coloquio.md).

## Estructura

```
main.py             # Arranque de la aplicación
app/
├── ui/             # Flet: una clase por pantalla (presentación)
├── servicios/      # Casos de uso, cada uno en una transacción; sanitización de entradas
├── dominio/        # Clases puras (entidades, State, Observer)
├── persistencia/   # Conexión, migraciones y repositorios (SQL a mano)
└── reportes/       # Reportes y gráficos
db/migraciones/     # Esquema versionado
scripts/            # migrar.py, sembrar.py
tests/              # dominio/, integracion/, servicios/ y ui/
```

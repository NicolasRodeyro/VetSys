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

El menú tiene dos grupos:

| Atención | Laboratorio | Reportes |
|---|---|---|
| Clientes, Mascotas, Turnos, Consultas, Comprobantes | Muestras, Conservadoras, Remitos, Recepción, Resultados | Facturación, Tiempos, Rechazo, Vacunas pendientes |

Para empezar un recorrido completo: **Consultas** (registrar consulta y emitir una orden de análisis) →
**Muestras** (extracción) → **Conservadoras** (empaquetar y precintar) → **Remitos** (crear, cerrar, despachar)
→ **Recepción** (el laboratorio constata precinto y temperatura) → **Resultados** → **Comprobantes**.
Si el precinto llega roto, la muestra se rechaza y se re-extrae desde **Muestras**.

## 3. Configuración (opcional)

La base es un archivo y no necesita credenciales. Con los valores por defecto no hace falta ningún `.env`.
Para cambiar algo:

```powershell
copy .env.example .env
```

- `DATABASE_PATH`: ruta del archivo de la base (por defecto `vetsys.db` en la raíz del repo).

El archivo `.env` está en `.gitignore` y **nunca se commitea**.

## 4. Scripts de línea de comandos (opcionales)

La aplicación ya crea la base y carga los datos de prueba sola, pero se puede hacer a mano:

```powershell
python scripts/migrar.py               # crea la base / aplica las migraciones de db/migraciones/ que falten
python scripts/sembrar.py              # carga los datos de prueba (clínicas, clientes, mascotas...)
python scripts/sembrar_operaciones.py  # OPCIONAL: carga consultas, muestras y remitos de demostración
```

El tercer script es solo para **ver los reportes con datos**: agrega un historial de unos meses
(consultas con comprobantes, muestras que viajan y se procesan, y algunas rechazadas) para que los
reportes de facturación, tiempos y rechazo no salgan vacíos. No hace falta para usar el sistema.

Para empezar de cero, borrar `vetsys.db`.

## 5. Tests

```powershell
pytest
```

Los tests de `dominio/` no usan base de datos. Los de integración, servicios e interfaz usan un archivo
SQLite temporal, nunca `vetsys.db`. Los de la interfaz prueban la lógica de cada pantalla sin abrir una ventana.

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

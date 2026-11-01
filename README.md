# VetSys

Sistema para una red de clínicas veterinarias con derivación de muestras a un laboratorio central.
TP Integrador de Desarrollo de Aplicaciones con Objetos (UTN).

Stack: Python 3.12 · Flask · PostgreSQL (Supabase) · psycopg 3 · pytest.

## 1. Instalación

Desde la raíz del repo (Windows / PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En Linux/macOS, activar con `source .venv/bin/activate`.

## 2. Configurar `.env`

```powershell
copy .env.example .env
```

Completar en `.env`:

- `DATABASE_URL`: cadena de conexión a Postgres (ver abajo).
- `FLASK_SECRET_KEY`: cualquier texto largo. Se puede generar con
  `python -c "import secrets; print(secrets.token_hex(32))"`.

El archivo `.env` está en `.gitignore` y **nunca se commitea**.

### Obtener la cadena de Supabase

1. Entrar al proyecto en [supabase.com](https://supabase.com/dashboard).
2. Botón **Connect** (arriba en la página del proyecto).
3. Pestaña **Connection string** → tipo **URI** → elegir **Session pooler**.
4. Copiar la cadena. Tiene esta forma:
   `postgresql://postgres.<id-proyecto>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres`
5. Reemplazar `[YOUR-PASSWORD]` por la contraseña de la base (sin los corchetes).
   Si no la recordás: **Project Settings → Database → Reset database password**.
   Si la contraseña tiene caracteres como `@`, `:`, `/` o `#`, hay que escaparlos
   (ej. `@` → `%40`) o elegir una contraseña sin esos caracteres.

Se usa el **Session pooler** (puerto 5432) porque funciona en redes IPv4 y
mantiene una sesión por conexión, como un Postgres normal.

### Plan B: Postgres local

Cambiar solo `DATABASE_URL`, por ejemplo:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vetsys
```

## 3. Migrar la base

```powershell
python scripts/migrar.py
```

Aplica en orden los archivos de `db/migraciones/` que todavía no se aplicaron
(se registran en la tabla `migraciones_aplicadas`). Se puede correr las veces
que haga falta.

## 4. Correr

```powershell
flask run          # http://127.0.0.1:5000
pytest             # tests
```

## Estructura

```
app/
├── web/            # Flask: blueprints, rutas, templates
├── servicios/      # Casos de uso
├── dominio/        # Clases puras (entidades, State, Observer)
├── persistencia/   # Conexión y repositorios (SQL a mano)
└── reportes/       # Reportes y gráficos
db/migraciones/     # Esquema versionado
scripts/migrar.py   # Aplica migraciones
tests/              # dominio/ (sin base) e integracion/ (con base)
```

# Instalación del Sistema del Consultorio

Guía paso a paso para montar el sistema desde cero, tanto en la PC de
desarrollo como en el servidor del consultorio.

---

## 1. Requisitos previos

| Componente | Versión mínima | Para qué |
|---|---|---|
| Python | 3.12 o superior | Ejecutar Django |
| PostgreSQL | 13 o superior | Base de datos |
| pip | incluido en Python | Instalar dependencias |
| git (opcional) | cualquiera | Control de versiones |

**Verifica lo que tienes instalado:**

```bash
python3 --version
psql --version
```

**En Linux (Debian/Ubuntu) instala lo que haga falta:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev \
                    postgresql postgresql-contrib \
                    libpq-dev build-essential
```

> En Windows: instala Python desde python.org y PostgreSQL desde
> postgresql.org. Las librerías `libpq-dev`/`build-essential` no aplican.

---

## 2. Crear el entorno virtual

```bash
cd /ruta/del/proyecto/clinica
python3 -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
```

Para saber que está activo, el prompt debe empezar con `(venv)`.

---

## 3. Instalar las dependencias de Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Esto instala: Django, psycopg (driver de PostgreSQL), openpyxl (Excel),
reportlab (PDF), pillow (imágenes), gunicorn y whitenoise (servidor de
producción).

---

## 4. Crear la base de datos

```bash
sudo -u postgres psql
```

Dentro de psql:

```sql
CREATE DATABASE clinica;
CREATE USER clinica_user WITH PASSWORD 'PON_AQUI_TU_CLAVE';
GRANT ALL PRIVILEGES ON DATABASE clinica TO clinica_user;
ALTER DATABASE clinica OWNER TO clinica_user;
\q
```

---

## 5. Crear el esquema `clinica` (las tablas)

El proyecto incluye el SQL con todas las tablas. Ejecuta **en este orden**:

```bash
# 1. Esquema completo (si tienes el archivo del esquema oficial)
psql -U clinica_user -d clinica -h localhost -f sql/esquema_clinica.sql

# 2. Parche: columna valor de enfermedad y ajustes NOT NULL
psql -U clinica_user -d clinica -h localhost -f sql/parche_enfermedad_valor.sql

# 3. Parche: columna telefono de persona
psql -U clinica_user -d clinica -h localhost -f sql/parche_telefono.sql
```

> Si tu base de datos ya tiene las tablas (porque vienes de la versión
> anterior), salta el paso 1 y ejecuta solo los parches 2 y 3.

**Verifica que las tablas existan:**

```bash
psql -U clinica_user -d clinica -h localhost -c \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='clinica' ORDER BY table_name;"
```

---

## 6. Configurar la conexión (`config/settings.py`)

Busca el bloque `DATABASES` y ajústalo:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'clinica',
        'USER': 'clinica_user',
        'PASSWORD': 'PON_AQUI_TU_CLAVE',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

## 7. Bootstrap y los iconos (ya vienen en el proyecto)

El proyecto usa **Bootstrap 5.3** y **Bootstrap Icons** desde archivos
locales en la carpeta `static/`, así el sistema funciona aunque el
servidor del consultorio no tenga internet.

Si esa carpeta no está (porque clonaste el proyecto sin ella), descárgala:

```bash
mkdir -p static/css static/js static/webfonts

# Bootstrap CSS
curl -L -o static/css/bootstrap.min.css \
  https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css

# Bootstrap JS
curl -L -o static/js/bootstrap.bundle.min.js \
  https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js

# Bootstrap Icons (CSS)
curl -L -o static/css/bootstrap-icons.css \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css

# Bootstrap Icons (fuentes)
curl -L -o static/webfonts/bootstrap-icons.woff2 \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/fonts/bootstrap-icons.woff2
curl -L -o static/webfonts/bootstrap-icons.woff \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/fonts/bootstrap-icons.woff

# Ajustar la ruta de las fuentes dentro del CSS de iconos
sed -i 's|url("./fonts/|url("../webfonts/|g' static/css/bootstrap-icons.css
```

También se usa la tipografía **Inter** de Google Fonts. Es opcional: si no
hay internet, el sistema usa la fuente del navegador y se ve igual de bien.

---

## 8. Preparar las migraciones

Las tablas se crearon con el SQL, por eso las migraciones solo se
**registran** (no se ejecutan de nuevo):

```bash
python manage.py migrate --fake-initial
```

Si Django se queja con un error del estado migratorio (porque las
migraciones `0001_initial` estaban vacías), repáralo así:

```bash
python manage.py shell
```

```python
import datetime
from django.db import connection
migs = [
    ('identificacion', '0002_initial'), ('citas', '0002_initial'),
    ('diagnostico', '0002_initial'), ('antecedentes', '0002_initial'),
    ('mediciones', '0002_initial'), ('usuarios', '0002_initial'),
    ('identificacion', '0003_persona_telefono'),
    ('auth', '0002_alter_permission_name_max_length'),
    ('auth', '0003_alter_user_email_max_length'),
    ('auth', '0004_alter_user_username_opts'),
    ('auth', '0005_alter_user_last_login_null'),
    ('auth', '0006_require_contenttypes_0002'),
    ('auth', '0007_alter_validators_add_error_messages'),
    ('auth', '0008_alter_user_username_max_length'),
    ('auth', '0009_alter_user_last_name_max_length'),
    ('auth', '0010_alter_group_name_max_length'),
    ('auth', '0011_update_proxy_permissions'),
    ('auth', '0012_alter_user_first_name_max_length'),
]
with connection.cursor() as cur:
    for app, name in migs:
        cur.execute("SELECT 1 FROM django_migrations WHERE app=%s AND name=%s", [app, name])
        if not cur.fetchone():
            cur.execute("INSERT INTO django_migrations (app, name, applied) VALUES (%s,%s,%s)",
                        [app, name, datetime.datetime.now(datetime.timezone.utc)])
print('Migraciones registradas')
```

---

## 9. Crear el usuario administrador

```bash
python manage.py createsuperuser
```

Te pedirá usuario, correo y contraseña. Guarda bien la contraseña.

Luego asígnale el rol de SuperAdmin (entra a
`http://127.0.0.1:8000/usuarios/usuarios/` o créalo desde el admin de
Django en `/admin/`), porque la pantalla de **Configuración** solo la ve
el rol `SuperAdmin`.

---

## 10. Verificar que todo esté correcto

```bash
python manage.py check
python manage.py makemigrations --check --dry-run     # debe decir "No changes detected"
python manage.py showmigrations                        # todo marcado con [X]
```

---

## 11. Levantar el servidor

```bash
python manage.py runserver
```

Abre en el navegador: **http://127.0.0.1:8000/**  
Te redirige al login. Entra con el superusuario.

---

## 12. Archivos estáticos (solo producción)

En desarrollo Django sirve los estáticos solo. En producción hay que
recopilarlos:

```bash
python manage.py collectstatic --noinput
```

Esto junta todo en la carpeta `staticfiles/`. Para servirlos se usa
`whitenoise` (ya instalado y configurado en `settings.py`).

---

## 13. Puesta en producción (servidor del consultorio)

Antes de subirlo al servidor real, en `config/settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['ip-del-servidor', 'dominio.com', 'localhost']
SECRET_KEY = 'genera-una-clave-larga-y-secreta'
```

Genera una `SECRET_KEY` nueva:

```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Levantar con gunicorn:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

**Copia de seguridad de la base de datos (hazla periódicamente):**

```bash
pg_dump -U clinica_user -h localhost clinica > respaldo_$(date +%Y%m%d).sql
```

Para restaurarla:

```bash
psql -U clinica_user -h localhost -d clinica < respaldo_20260101.sql
```

---

## Estructura de carpetas

```
clinica/
├── apps/                  Aplicaciones del sistema
│   ├── antecedentes/      Antecedentes médicos
│   ├── citas/             Citas
│   ├── diagnostico/       Diagnóstico, conductas, catálogo
│   ├── estadistica/       Reportes Excel/PDF
│   ├── identificacion/    Pacientes, médicos, direcciones
│   ├── mediciones/        Equipos, parámetros, mediciones
│   └── usuarios/          Login, roles, permisos
├── config/                Configuración de Django
├── docs/                  Esta guía
├── sql/                   Esquema y parches de la base de datos
├── static/                Bootstrap, iconos, fuentes (local)
├── staticfiles/           Se genera con collectstatic
├── templates/             Plantillas base
├── manage.py
└── requirements.txt
```

---

## Problemas frecuentes

| Error | Solución |
|---|---|
| `ModuleNotFoundError: psycopg` | `pip install -r requirements.txt` |
| `could not connect to server` (PostgreSQL) | Revisa `HOST`, `PORT` y que el servicio esté activo: `sudo systemctl start postgresql` |
| Los estilos no cargan | Ejecuta `collectstatic` o revisa que exista la carpeta `static/` |
| `no such table: clinica.X` | Falta ejecutar el SQL del esquema o los parches |
| Los iconos salen como cuadros | Falta la carpeta `static/webfonts/` con las fuentes de Bootstrap Icons |
| `The field admin.LogEntry.user was declared with a lazy reference` | Repara las migraciones con el script del paso 8 |

---

## Seguridad: usuarios, roles y permisos

La seguridad del sistema es **propia** (no depende del esquema clínico) y se
organiza por **módulos**: cada opción del sidebar es un módulo y cada módulo
tiene submódulos (ver, crear, editar y, solo para el administrador, eliminar).

### Módulos definidos

| Módulo | Submódulos |
|---|---|
| pacientes | ver, crear, editar, eliminar |
| registrar | crear |
| medicos | ver, crear, editar, eliminar |
| especialidades | ver, crear, editar, eliminar |
| direcciones | ver, crear, editar, eliminar |
| identificacion | ver, crear, editar |
| catalogos (etnia, sangre, discapacidad) | ver, crear, editar |
| citas | ver, crear, editar, eliminar |
| **mediciones** | ver, crear, editar |
| **antecedentes** | ver, crear, editar |
| **diagnostico** | ver, crear, editar |
| catalogo-enfermedades | ver, crear, editar, eliminar |
| config-mediciones | ver, crear, editar, eliminar |
| estadisticas | ver, exportar |
| usuarios | ver, crear, editar, eliminar |
| roles | ver, crear, editar |
| configuracion | ver |

> El módulo de **diagnóstico** se separa en tres partes: mediciones,
> antecedentes y diagnóstico. Cada pestaña de la pantalla "Atender cita"
> valida su propio permiso, así una enfermera puede tomar mediciones y
> antecedentes sin necesidad de permiso de diagnóstico.

### Reglas

- **Solo el administrador puede eliminar.** El permiso `*.eliminar` se
  descarta siempre que el rol destino no sea `SuperAdmin`, incluso si se
  manipula el formulario.
- Los **roles son predefinidos**: SuperAdmin, Medico, Enfermera, Recepcion.
- Al crear un usuario se **copian los permisos de su rol**; después se
  ajustan uno por uno en la misma pantalla.
- El sidebar **solo muestra** los módulos que el usuario puede ver.

### Sembrar permisos y roles

```bash
python manage.py sembrar_permisos
```

Crea los 54 permisos y los 4 roles con sus permisos predefinidos. Es
idempotente: puedes ejecutarlo cuando quieras.

### Pantalla de Usuarios

Todo está en **una sola pantalla** (`/usuarios/usuarios/`):

- Datos: nombre, apellido, cédula, teléfono, sexo, rol, usuario, contraseña
- Debajo: los **permisos por módulo** con sus casillas
- Al elegir el rol se pre-cargan sus permisos automáticamente
- Los botones Eliminar solo aparecen para el administrador

---

## AlertifyJS: notificaciones del sistema

El proyecto usa **AlertifyJS 1.14.0** para los mensajes en pantalla (éxito,
error, información y diálogos de confirmación). Los archivos son locales
(`static/alertify/`), así que funcionan sin internet en el servidor.

### Archivos incluidos

```
static/alertify/alertify.min.css      (24K)
static/alertify/bootstrap.min.css     (4K, tema)
static/alertify/alertify.min.js       (40K)
static/js/notificar.js                (helper propio)
```

### Cómo usarlo

El helper `static/js/notificar.js` expone cuatro funciones globales:

```js
notify.ok('Paciente registrado correctamente');
notify.error('No se pudo guardar');
notify.info('Revise los datos antes de continuar');

notify.confirmar('¿Eliminar el registro?', function () {
    document.getElementById('form').submit();
});
```

Los mensajes de Django (`messages.success`, `messages.error`) se muestran
automáticamente como notificaciones: las plantillas los marcan con
`data-notify` y `base.html` los lee al cargar la página.

### Si falta la carpeta

```bash
mkdir -p static/alertify
curl -L -o static/alertify/alertify.min.css   https://cdn.jsdelivr.net/npm/alertifyjs@1.14.0/build/css/alertify.min.css
curl -L -o static/alertify/bootstrap.min.css  https://cdn.jsdelivr.net/npm/alertifyjs@1.14.0/build/css/themes/bootstrap.min.css
curl -L -o static/alertify/alertify.min.js    https://cdn.jsdelivr.net/npm/alertifyjs@1.14.0/build/alertify.min.js

python manage.py collectstatic --noinput
```

Referencia: <https://alertifyjs.com/>

---

## Tipo de cita

Cada cita guarda **por qué se agenda**: primera vez, rutina, seguimiento,
control o emergencia. Se almacena en `cita.tipo_cita`
(`varchar(20)`, opcional).

### Valores del sistema

| Código | Etiqueta | Cuándo se usa |
|---|---|---|
| `PRIMERA` | Primera Vez | El paciente nunca ha venido |
| `RUTINA` | Rutina | Chequeo periódico programado |
| `SEGUIMIENTO` | Seguimiento | Continuación de un tratamiento |
| `CONTROL` | Control | Revisión de algo ya tratado |
| `EMERGENCIA` | Emergencia | Atención urgente |

### Parche de base de datos

`sql/parche_tipo_cita.sql`:
- crea la columna `tipo_cita` si no existe
- marca las citas antiguas sin tipo como `RUTINA`
- crea el índice `idx_cita_tipo` para los reportes

```bash
psql -U clinica_user -d clinica -h localhost -f sql/parche_tipo_cita.sql
```

### Dónde se usa

- **Registrar paciente** → pestaña "Agendar Cita": selector *Tipo de Cita*
- **Lista de citas** → columna *Tipo*
- **API de búsqueda** → campo `tipo` con la etiqueta legible
  ("Primera Vez" en lugar de "PRIMERA")

### Añadir un tipo nuevo

Se cambia en **un solo lugar**, `apps/citas/models.py`:

```python
class TipoCita(models.TextChoices):
    PRIMERA = 'PRIMERA', 'Primera Vez'
    RUTINA = 'RUTINA', 'Rutina'
    ...
    INTERCONSULTA = 'INTERCONSULTA', 'Interconsulta'   # <- nuevo
```

No hace falta tocar la base de datos: la columna acepta cualquier texto de
hasta 20 caracteres.

---

## Estadísticas y reportes

Todo está en `/estadistica/` y se filtra por **Desde / Hasta** y por
**nombre o cédula** del paciente. Los botones de Excel y PDF conservan los
filtros activos.

### 1. Visitas por edad y sexo

Tabla con los rangos pedidos, contando **visitas atendidas**:

| Rango | | Rango |
|---|---|---|
| 0-11 meses | | 13-17 años |
| 1-3 años | | 18-25 años |
| 4-6 años | | 26-35 años |
| 7-9 años | | 36-59 años |
| 10-12 años | | 60 años o más |

Columnas: Masculino, Femenino, Otro y Total.

### 2. Visitas por edad y especialidad

Tabla cruzada: filas = rango de edad, columnas = especialidad del médico
que atendió, más el total por fila y la fila de totales.

### 3. Registros históricos de atención

Una fila por visita atendida con:

`Fecha · Nombre · Apellido · Edad · Sexo · Cédula · Dirección · Teléfono ·
Fecha Nacimiento · Diagnóstico · Conducta`

> **La edad se calcula a la fecha de atención, no a la de hoy.**
> Si a un paciente se le diagnosticó cáncer de próstata a los 55 años,
> ese registro aparece con 55 aunque hoy tenga 58.

También se puede exportar solo este reporte:
`/estadistica/historico/excel/` y `/estadistica/historico/pdf/`

### 4. Pacientes por ubicación

Arranca en **Monagas** y permite bajar por la jerarquía:

```
/estadistica/ubicacion/          -> municipios de Monagas
/estadistica/ubicacion/<id>/     -> parroquias del municipio
/estadistica/ubicacion/<id>/     -> sectores de la parroquia
```

Al final de la cadena se listan los **pacientes** de ese lugar. Si se pide
un id que no cuelga de Monagas, la vista vuelve a la raíz.

Si tu consultorio está en otro estado, cámbialo en
`apps/estadistica/services.py`:

```python
ESTADO_RAIZ = 'Monagas'
```

### Sección eliminada

Se quitó **"Promedio de mediciones"**: el esquema clínico no la necesitaba
y confundía con la configuración de equipos y parámetros.

---

## Estructura de ancla en las tablas circulares

Las tablas con estructura de árbol usan **la misma regla en todas**, tomada
del ejemplo de direcciones:

| id | dsc | depid | tipo |
|---|---|---|---|
| 0 | NINGUNO | 0 | 0 |
| 1 | MONAGAS | 0 | 1 |
| 2 | MATURIN | 1 | 2 |
| 3 | PALO NEGRO | 2 | 3 |
| 4 | LA CRUZ | 2 | 3 |

### Reglas

1. **`id = 0` es la fila ancla `NINGUNO`.** Nunca se edita ni se borra; solo
   existe para que ninguna fila quede huérfana.
2. **`tipo` indica el nivel.** 1 = raíz del árbol (Estado, Documento,
   Categoría), y sube desde ahí.
3. **El padre apunta SIEMPRE a una fila**: a `0` (NINGUNO) si es raíz, o al
   id del nivel inmediatamente superior. Nunca NULL.
4. **El selector de padre solo ofrece el nivel anterior.** Si registras una
   parroquia, el desplegable solo tiene municipios; no puedes colgarla de un
   sector por error.

### Niveles por tabla

| Tabla | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `direccion` | Estado | Municipio | Parroquia | Calle / Sector |
| `identificacion` | Documento | Subtipo | | |
| `enfermedad` | Categoría | Enfermedad | | |
| `sintomas` | Categoría | Síntoma | | |
| `antecedentes_salud` | Categoría | Antecedente | | |

### Parche

`sql/parche_arboles.sql`:

1. Quita las llaves foráneas (si no, no se puede insertar la ancla)
2. Crea la fila `id = 0` con `NINGUNO`
3. Convierte los huérfanos (`NULL`) en `0`
4. Deduce el `tipo` de los datos existentes
5. Pone `NOT NULL` + `DEFAULT 0` en la columna del padre
6. Recrea las llaves y añade índices

```bash
psql -U clinica_user -d clinica -h localhost -f sql/parche_arboles.sql
```

### Añadir un nivel nuevo

Si más adelante necesitas otro nivel (por ejemplo `Zona` entre Parroquia y
Calle), se cambia en un solo lugar, `apps/catalog.py`:

```python
TIPOS_DIRECCION = [(1, 'Estado'), (2, 'Municipio'),
                   (3, 'Parroquia'), (4, 'Zona'), (5, 'Calle / Sector')]
```

El formulario, el selector de padre y los reportes lo toman automáticamente.

---

## Reporte: Especialidad x Edad x Sexo

Formato de doble cabecera, tal como se pidió:

```
especialidad     0-11 meses   1-3 años   4-6 años  ...  60 años o más    Totales
                   m  f        m  f       m  f              m  f        m  f  tot
Medicina interna   0  2        0  2       0  2              0  2        .  .   .
Ginecología        0  1        0  1       0  1              0  1        .  .   .
Pediatría          0  3        0  3       0  3              0  3        .  .   .
```

- **Filas**: cada especialidad que atendió al menos una visita
- **Columnas**: los 10 rangos de edad, cada uno dividido en **m** y **f**
- **Últimas 3 columnas**: totales por sexo y total general
- **Fila final**: totales por rango

### Reglas

- Se cuentan **visitas atendidas**: si un paciente vino tres veces, cuenta tres
- La edad se calcula a la **fecha de atención**, no a la de hoy
- El sexo "Otro" se incluye en el total general

### Dónde aparece

| Medio | Ruta |
|---|---|
| Pantalla | `/estadistica/` (sección "Visitas por especialidad, edad y sexo") |
| Excel | hoja `Esp x Edad x Sexo` (cabecera combinada, paneles inmovilizados) |
| PDF | sección "Visitas por Especialidad, Edad y Sexo" |

Los filtros **Desde / Hasta** de la pantalla se aplican también a la exportación.

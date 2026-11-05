# Instalación del Sistema

> **Guía rápida para administradores.** Si solo quieres instalar y arrancar,
> lee la sección "En 3 pasos" y listo. El resto del documento es la
> referencia técnica, para cuando algo haya que revisar.

---

# En 3 pasos

## Paso 1 — Instalar lo que el sistema necesita

Solo se hace **una vez** por equipo.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql
```

## Paso 2 — Ejecutar el instalador

```bash
cd /ruta/del/proyecto/clinica
./instalar.sh
```

El instalador pregunta solo 5 cosas (usuario y contraseña de PostgreSQL,
nombre de la base de datos, servidor y puerto) y hace el resto:

| Hace | Qué es |
|---|---|
| Crea el entorno virtual | `venv/` con todo lo de Python |
| Instala dependencias | Django, PostgreSQL, reportes... |
| Escribe el archivo `.env` | la configuración del sistema |
| Crea la base de datos | si no existe |
| Aplica los parches SQL | tablas, columnas y estructura de árbol |
| Registra las migraciones | para que Django reconozca las tablas |
| Siembra permisos y roles | la seguridad del sistema |
| Crea el administrador | el usuario con el que entras |
| Recopila los estilos | Bootstrap e iconos |

Si lo ejecutas otra vez, detecta lo que ya está hecho y no lo repite.

## Paso 3 — Arrancar

```bash
./iniciar.sh
```

Abre en el navegador: **http://127.0.0.1:8000/** y entra con el administrador
que creaste.

---

# Comprobar que todo está bien

```bash
./verificar.sh
```

Revisa programas, carpetas, conexión a la base de datos, tablas, permisos y
usuario administrador. Te dice en rojo lo que falla y cómo arreglarlo.

---

# Actualizar el sistema

Cuando llegues con una versión nueva del código:

```bash
./actualizar.sh
```

Hace **copia de seguridad de la base de datos antes de tocar nada**, instala
dependencias nuevas, aplica parches, migraciones y permisos, y verifica.

---

# El archivo `.env`

Toda la configuración variable está en un solo archivo. El instalador lo
crea por ti; si lo pierdes, cópialo de `.env.example`:

```bash
cp .env.example .env
```

| Variable | Para qué | Ejemplo |
|---|---|---|
| `DB_NAME` | Nombre de la base de datos | `clinica` |
| `DB_USER` | Usuario de PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña de PostgreSQL | `miclave` |
| `DB_HOST` | Servidor. **Vacío = este equipo** | *(vacío)* |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DJANGO_SECRET_KEY` | Clave secreta del sistema | texto largo |
| `DJANGO_DEBUG` | `True` solo en desarrollo | `False` |
| `DJANGO_ALLOWED_HOSTS` | IPs/dominios permitidos, separados por coma | `localhost,192.168.1.50` |

> **En el servidor del consultorio** pon `DJANGO_DEBUG=False` y la IP real en
> `DJANGO_ALLOWED_HOSTS`. En `True` el sistema muestra errores internos a
> cualquiera que entre.

---

# Instalación en el servidor del consultorio

Es la misma instalación, con tres cosas distintas:

```bash
# 1. Ejecutar el instalador (igual que en tu PC)
./instalar.sh

# 2. Poner el sistema en modo producción
#    edita .env y cambia:
#      DJANGO_DEBUG=False
#      DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,IP-DEL-SERVIDOR

# 3. Arrancar en modo producción
./iniciar.sh --prod
```

### Si otros equipos deben entrar

```bash
./iniciar.sh 0.0.0.0:8000
```

Y en el `.env` agrega la IP del servidor a `DJANGO_ALLOWED_HOSTS`.

### Copias de seguridad

```bash
# Una vez al día, por ejemplo con cron (0 2 * * *)
pg_dump -U postgres -h localhost --schema=clinica clinica > respaldo_$(date +%Y%m%d).sql
```

`./actualizar.sh` también hace copia antes de cada cambio.

---

# Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `./instalar.sh` dice que falta Python | No está instalado | `sudo apt install python3 python3-venv python3-pip` |
| Dice que falta PostgreSQL | No está instalado | `sudo apt install postgresql` |
| Error al crear la base de datos | Usuario sin permiso | `sudo -u postgres createdb clinica` |
| Error de conexión | Datos mal en `.env` | Revisa `DB_USER`, `DB_PASSWORD`, `DB_HOST` |
| La página sale sin estilos | Falta `static/` | Descarga Bootstrap (ver referencia) |
| Los iconos salen como cuadros | Faltan las fuentes | Descarga Bootstrap Icons (ver referencia) |
| `403 Forbidden` | La IP no está permitida | Agrégala a `DJANGO_ALLOWED_HOSTS` |
| Se ve un error interno en pantalla | `DEBUG=True` en producción | Pon `DJANGO_DEBUG=False` |

---

# Referencia técnica

La guía detallada paso a paso (instalación manual, reparación de
migraciones, Bootstrap local, informes, estructura de árbol) quedó en:

**`docs/INSTALACION_referencia.md`**

Ahí está, entre otras cosas:

- Cómo instalar **sin el script**, a mano
- Cómo **reparar las migraciones** si el estado quedó inconsistente
- Los comandos `curl` para descargar **Bootstrap, iconos y AlertifyJS**
- Cómo se calculan los **informes y las estadísticas**
- La **estructura de ancla** (id 0 = NINGUNO) de las tablas circulares
- Los **parches SQL** y qué hace cada uno

---

# Resumen de archivos

| Archivo | Para qué |
|---|---|
| `instalar.sh` | Instala todo desde cero |
| `iniciar.sh` | Arranca el sistema (`--prod` para producción) |
| `verificar.sh` | Comprueba que todo esté en orden |
| `actualizar.sh` | Actualiza con copia de seguridad |
| `.env` | Tu configuración (no se comparte) |
| `.env.example` | Plantilla de configuración |
| `requirements.txt` | Dependencias y pasos documentados |
| `sql/` | Esquema y parches de la base de datos |
| `sql/respaldos/` | Copias de seguridad automáticas |
| `docs/INSTALACION.md` | Esta guía |
| `docs/INSTALACION_referencia.md` | Guía técnica detallada |

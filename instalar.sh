#!/usr/bin/env bash
# =====================================================================
#  INSTALADOR DEL SISTEMA DE CITAS MÉDICAS
# =====================================================================
#  Uso:
#      ./instalar.sh
#
#  Hace todo lo necesario en un solo comando:
#    1. Revisa que estén Python y PostgreSQL
#    2. Crea el entorno virtual e instala las dependencias
#    3. Configura la base de datos (pregunta los datos)
#    4. Crea las tablas y aplica los parches
#    5. Registra las migraciones y siembra permisos/roles
#    6. Crea el usuario administrador
#    7. Recopila los archivos estáticos
#    8. Verifica que todo quede funcionando
#
#  Se puede ejecutar las veces que haga falta: lo ya hecho lo detecta
#  y lo salta.
# =====================================================================

# --- Colores y ayuda visual ---
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
CYAN='\033[0;36m'
NEGRITA='\033[1m'
SIN='\033[0m'

paso() { echo -e "\n${AZUL}${NEGRITA}▶ $1${SIN}"; }
ok()   { echo -e "  ${VERDE}✓${SIN} $1"; }
aviso(){ echo -e "  ${AMARILLO}!${SIN} $1"; }
error(){ echo -e "  ${ROJO}✗${SIN} $1"; }
info() { echo -e "  ${CYAN}→${SIN} $1"; }

# Salir si algo falla
set -e

cd "$(dirname "$0")"
RAIZ=$(pwd)

echo -e "${NEGRITA}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   INSTALACIÓN DEL SISTEMA DE CITAS MÉDICAS      ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${SIN}"
echo "  Carpeta del proyecto: $RAIZ"
echo "  Fecha: $(date '+%d/%m/%Y %H:%M')"

# =====================================================================
#  1. REVISAR REQUISITOS
# =====================================================================
paso "1 de 8 — Revisando requisitos"

if ! command -v python3 >/dev/null 2>&1; then
    error "No se encontró Python 3."
    echo "       Instálalo con:  sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
ok "Python $(python3 --version | cut -d' ' -f2)"

if ! command -v psql >/dev/null 2>&1; then
    error "No se encontró PostgreSQL (comando psql)."
    echo "       Instálalo con:  sudo apt install postgresql"
    exit 1
fi
ok "PostgreSQL $(psql --version | cut -d' ' -f3)"

# =====================================================================
#  2. ENTORNO VIRTUAL Y DEPENDENCIAS
# =====================================================================
paso "2 de 8 — Preparando el entorno virtual"

if [ ! -d "venv" ]; then
    info "Creando el entorno virtual (venv)..."
    python3 -m venv venv
    ok "Entorno virtual creado"
else
    ok "El entorno virtual ya existía"
fi

# shellcheck disable=SC1091
source venv/bin/activate

info "Instalando dependencias de Python..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Dependencias instaladas"

# =====================================================================
#  3. CONFIGURACIÓN (.env)
# =====================================================================
paso "3 de 8 — Configuración"

# Cancela una lectura con Ctrl+C de forma ordenada
trap 'echo; error "Instalación cancelada."; exit 130' INT

DB_NOMBRE="clinica"
DB_USUARIO="postgres"
DB_CLAVE=""
DB_HOST="localhost"
DB_PUERTO="5432"

if [ -f ".env" ]; then
    ok "Ya existe un archivo .env, se conserva"
    # Leer los valores actuales
    DB_NOMBRE=$(grep -s '^DB_NAME=' .env | cut -d= -f2)
    DB_USUARIO=$(grep -s '^DB_USER=' .env | cut -d= -f2)
    DB_CLAVE=$(grep -s '^DB_PASSWORD=' .env | cut -d= -f2)
    DB_HOST=$(grep -s '^DB_HOST=' .env | cut -d= -f2)
    DB_PUERTO=$(grep -s '^DB_PORT=' .env | cut -d= -f2)
else
    echo
    info "Vamos a configurar la conexión a PostgreSQL."
    info "Si no sabes un dato, pulsa ENTER para usar el valor entre paréntesis."
    echo

    read -r -p "  Nombre de la base de datos [$DB_NOMBRE]: " r; DB_NOMBRE="${r:-$DB_NOMBRE}"
    read -r -p "  Usuario de PostgreSQL [$DB_USUARIO]: " r; DB_USUARIO="${r:-$DB_USUARIO}"
    read -r -s -p "  Contraseña de PostgreSQL: " r; echo; DB_CLAVE="${r:-postgres}"
    read -r -p "  Servidor (ENTER = este equipo) [$DB_HOST]: " r; DB_HOST="${r:-$DB_HOST}"
    read -r -p "  Puerto [$DB_PUERTO]: " r; DB_PUERTO="${r:-$DB_PUERTO}"

    # Generar una clave secreta
    CLAVE=$(python3 - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
)

    cat > .env <<EOF
# Configuración generada por instalar.sh
DB_NAME=$DB_NOMBRE
DB_USER=$DB_USUARIO
DB_PASSWORD=$DB_CLAVE
DB_HOST=$DB_HOST
DB_PORT=$DB_PUERTO

DJANGO_SECRET_KEY=$CLAVE
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
EOF
    ok "Archivo .env creado"
fi

export PGPASSWORD="$DB_CLAVE"

# Si el host está vacío se conecta por socket local (sin -h).
# Así funciona tanto en este equipo como en un servidor remoto.
if [ -n "$DB_HOST" ]; then
    HOST_ARG="-h $DB_HOST"
else
    HOST_ARG=""
fi
PSQL="psql -U $DB_USUARIO $HOST_ARG -p $DB_PUERTO -d $DB_NOMBRE"
PSQL_ADMIN="psql -U $DB_USUARIO $HOST_ARG -p $DB_PUERTO -d postgres"

# =====================================================================
#  4. BASE DE DATOS
# =====================================================================
paso "4 de 8 — Base de datos"

if $PSQL -c 'SELECT 1' >/dev/null 2>&1; then
    ok "La base de datos '$DB_NOMBRE' ya existe y responde"
else
    info "Creando la base de datos '$DB_NOMBRE'..."
    if $PSQL_ADMIN -c "CREATE DATABASE $DB_NOMBRE" >/dev/null 2>&1; then
        ok "Base de datos creada"
    else
        error "No se pudo crear la base de datos."
        echo
        echo "  Revisa en el archivo .env:"
        echo "    • DB_USER y DB_PASSWORD correctos"
        echo "    • Que el usuario tenga permiso para crear bases"
        echo
        echo "  O créala a mano:"
        echo "    sudo -u postgres createdb $DB_NOMBRE"
        exit 1
    fi
fi

# Crear el esquema clinica
info "Creando el esquema clinica..."
$PSQL -c 'CREATE SCHEMA IF NOT EXISTS clinica' >/dev/null 2>&1
ok "Esquema clinica listo"

# =====================================================================
#  5. TABLAS Y PARCHES
# =====================================================================
paso "5 de 8 — Tablas y ajustes"

# ¿Ya hay tablas?
TIENE_TABLAS=$($PSQL -tAc "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema='clinica' AND table_type='BASE TABLE'" 2>/dev/null || echo 0)

if [ "$TIENE_TABLAS" -gt 0 ]; then
    info "Ya hay $TIENE_TABLAS tablas. Se aplican solo los ajustes."
else
    info "Creando las tablas..."
    for archivo in sql/esquema_clinica.sql; do
        [ -f "$archivo" ] && $PSQL -q -f "$archivo" && ok "Esquema creado"
    done
fi

for parche in sql/parche_enfermedad_valor.sql \
              sql/parche_telefono.sql \
              sql/parche_tipo_cita.sql \
              sql/parche_arboles.sql; do
    if [ -f "$parche" ]; then
        info "Aplicando $(basename "$parche")..."
        if $PSQL -q -f "$parche" 2>/dev/null; then
            ok "$(basename "$parche") aplicado"
        else
            aviso "$(basename "$parche") tuvo avisos (puede ser normal si ya estaba aplicado)"
        fi
    fi
done

# =====================================================================
#  6. MIGRACIONES Y PERMISOS
# =====================================================================
paso "6 de 8 — Migraciones y permisos"

python3 manage.py migrate --fake-initial >/dev/null 2>&1 && ok "Migraciones registradas" \
    || { aviso "Reintentando migraciones..."; python3 manage.py migrate --fake-initial; }

python3 manage.py sembrar_permisos

# =====================================================================
#  7. USUARIO ADMINISTRADOR
# =====================================================================
paso "7 de 8 — Usuario administrador"

ADMIN_EXISTE=$(python3 - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.usuarios.models import Usuario
print('si' if Usuario.objects.filter(is_superuser=True).exists() else 'no')
PY
)

if [ "$ADMIN_EXISTE" = "si" ]; then
    ok "Ya existe un administrador"
else
    info "Creando el usuario administrador..."
    echo
    python3 - <<'PY'
import os, django, getpass
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.usuarios.models import Usuario, Rol
from apps.usuarios.modulos import sembrar_permisos_y_roles

sembrar_permisos_y_roles()
rol = Rol.objects.filter(nombre='SuperAdmin').first()

username = input("  Usuario administrador [admin]: ").strip() or 'admin'
correo = input("  Correo (opcional): ").strip()
while True:
    clave = getpass.getpass("  Contraseña: ")
    clave2 = getpass.getpass("  Repite la contraseña: ")
    if clave != clave2:
        print("  Las contraseñas no coinciden. Intenta de nuevo.")
        continue
    if len(clave) < 4:
        print("  La contraseña debe tener al menos 4 caracteres.")
        continue
    break

Usuario.objects.create_user(
    username=username, password=clave, email=correo,
    rol=rol, is_staff=True, is_superuser=True)
print(f"  Administrador '{username}' creado.")
PY
    ok "Administrador listo"
fi

# =====================================================================
#  8. ARCHIVOS ESTÁTICOS Y VERIFICACIÓN
# =====================================================================
paso "8 de 8 — Archivos estáticos"

python3 manage.py collectstatic --noinput >/dev/null 2>&1 \
    && ok "Archivos estáticos recopilados" \
    || aviso "No se pudieron recopilar (revisa más tarde)"

echo
echo -e "${NEGRITA}  Verificando la instalación...${SIN}"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo
echo -e "${VERDE}${NEGRITA}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║            INSTALACIÓN COMPLETADA               ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${SIN}"
echo "  Para abrir el sistema:"
echo
echo "      ./iniciar.sh"
echo
echo "  O manualmente:"
echo "      source venv/bin/activate"
echo "      python3 manage.py runserver"
echo
echo "  Luego abre en el navegador:  http://127.0.0.1:8000/"
echo
echo "  Si el servidor del consultorio no tiene internet, los estilos ya"
echo "  están incluidos en la carpeta static/ (Bootstrap e iconos)."
echo

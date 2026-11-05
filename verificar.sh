#!/usr/bin/env bash
# =====================================================================
#  VERIFICAR LA INSTALACIÓN
# =====================================================================
#  Revisa que todo lo necesario esté en su sitio, sin cambiar nada.
#  Uso:  ./verificar.sh
# =====================================================================

VERDE='\033[0;32m'; ROJO='\033[0;31m'; AMARILLO='\033[1;33m'
AZUL='\033[0;34m'; NEGRITA='\033[1m'; SIN='\033[0m'

cd "$(dirname "$0")"

BIEN=0
MAL=0
AVISOS=0

revisar() {  # revisar "descripción" comando...
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo -e "  ${VERDE}✓${SIN} $desc"; BIEN=$((BIEN+1))
    else
        echo -e "  ${ROJO}✗${SIN} $desc"; MAL=$((MAL+1))
    fi
}

avisar() {
    echo -e "  ${AMARILLO}!${SIN} $1"; AVISOS=$((AVISOS+1))
}

echo -e "${AZUL}${NEGRITA}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        VERIFICACIÓN DE LA INSTALACIÓN           ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${SIN}"

# --- Programas ---
echo -e "\n${NEGRITA}Programas${SIN}"
revisar "Python 3 instalado" python3 --version
revisar "PostgreSQL instalado" psql --version

# --- Carpetas del proyecto ---
echo -e "\n${NEGRITA}Proyecto${SIN}"
revisar "Entorno virtual (venv/)" test -d venv
revisar "Archivo de configuración (.env)" test -f .env
revisar "Dependencias (requirements.txt)" test -f requirements.txt
revisar "Carpeta de estáticos (static/)" test -d static
revisar "Bootstrap local" test -f static/css/bootstrap.min.css
revisar "Iconos Bootstrap" test -f static/css/bootstrap-icons.css
revisar "AlertifyJS" test -f static/alertify/alertify.min.js
revisar "Carpeta de parches SQL (sql/)" test -d sql

# --- Comprobaciones de Django ---
echo -e "\n${NEGRITA}Sistema${SIN}"

if [ -d venv ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate

    revisar "Django arranca sin errores" python3 manage.py check
    revisar "Migraciones al día" python3 manage.py makemigrations --check --dry-run

    python3 - <<'PY'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

verde = '\033[0;32m'; rojo = '\033[0;31m'
amarillo = '\033[1;33m'; negrita = '\033[1m'; sin = '\033[0m'

def msg(ok_, texto):
    marca = verde + '✓' + sin if ok_ else rojo + '✗' + sin
    print('  ' + marca + ' ' + texto)

from django.db import connection
from apps.usuarios.models import Usuario, Rol, Permiso

# Conexión a la base de datos
try:
    with connection.cursor() as cur:
        cur.execute('SELECT 1')
    msg(True, "Conexión a la base de datos")
except Exception as e:
    msg(False, f"Conexión a la base de datos: {e}")

# Usuario administrador
admins = Usuario.objects.filter(is_superuser=True).count()
msg(admins > 0, f"Usuario administrador ({admins})")

# Roles y permisos
roles = Rol.objects.count()
perms = Permiso.objects.count()
msg(roles > 0, f"Roles definidos ({roles})")
msg(perms > 0, f"Permisos definidos ({perms})")

# Tablas del esquema clinica
with connection.cursor() as cur:
    cur.execute("""SELECT COUNT(*) FROM information_schema.tables
                   WHERE table_schema='clinica' AND table_type='BASE TABLE'""")
    tablas = cur.fetchone()[0]
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='clinica' AND table_name='enfermedad'
                   AND column_name='tipo'""")
    tiene_tipo = cur.fetchone() is not None
msg(tablas >= 20, f"Tablas del esquema clinica ({tablas})")
msg(tiene_tipo, "Estructura de árbol (columna tipo)")
PY
fi

# --- Resumen ---
echo -e "\n${NEGRITA}Resumen${SIN}"
echo -e "  Correcto: ${VERDE}$BIEN${SIN}   Con problemas: ${ROJO}$MAL${SIN}   Avisos: ${AMARILLO}$AVISOS${SIN}"

if [ "$MAL" -gt 0 ]; then
    echo
    echo -e "${AMARILLO}Hay cosas que revisar.${SIN} Soluciones habituales:"
    echo "  • Falta venv/ o .env    → ejecuta  ./instalar.sh"
    echo "  • Error de conexión     → revisa los datos del .env"
    echo "  • Faltan estáticos      → descarga Bootstrap (ver docs/INSTALACION.md)"
    exit 1
fi

echo
echo -e "${VERDE}Todo está en orden. Puedes iniciar con ./iniciar.sh${SIN}"

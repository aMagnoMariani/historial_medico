#!/usr/bin/env bash
# =====================================================================
#  ACTUALIZAR EL SISTEMA
# =====================================================================
#  Úsalo cuando llegues con una versión nueva del código.
#  Hace una copia de la base de datos antes de tocar nada.
#
#  Uso:
#      ./actualizar.sh
# =====================================================================

AZUL='\033[0;34m'; VERDE='\033[0;32m'; AMARILLO='\033[1;33m'
ROJO='\033[0;31m'; NEGRITA='\033[1m'; SIN='\033[0m'

info() { echo -e "  ${CYAN}→${SIN} $1"; }
CYAN='\033[0;36m'
ok()   { echo -e "  ${VERDE}✓${SIN} $1"; }
aviso(){ echo -e "  ${AMARILLO}!${SIN} $1"; }
error(){ echo -e "  ${ROJO}✗${SIN} $1"; }

set -e
cd "$(dirname "$0")"

echo -e "${AZUL}${NEGRITA}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        ACTUALIZACIÓN DEL SISTEMA                ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${SIN}"

[ -d venv ] || { error "No hay entorno virtual. Ejecuta ./instalar.sh"; exit 1; }
# shellcheck disable=SC1091
source venv/bin/activate

# --- Leer la configuración ---
DB_NOMBRE=$(grep -s '^DB_NAME=' .env | cut -d= -f2); DB_NOMBRE="${DB_NOMBRE:-clinica}"
DB_USUARIO=$(grep -s '^DB_USER=' .env | cut -d= -f2); DB_USUARIO="${DB_USUARIO:-postgres}"
DB_CLAVE=$(grep -s '^DB_PASSWORD=' .env | cut -d= -f2)
DB_HOST=$(grep -s '^DB_HOST=' .env | cut -d= -f2)
DB_PUERTO=$(grep -s '^DB_PORT=' .env | cut -d= -f2); DB_PUERTO="${DB_PUERTO:-5432}"

if [ -n "$DB_HOST" ]; then HOST_ARG="-h $DB_HOST"; else HOST_ARG=""; fi

# --- 1. Copia de seguridad ---
echo -e "\n${NEGRITA}1. Copia de seguridad${SIN}"
mkdir -p sql/respaldos
FECHA=$(date +%Y%m%d_%H%M%S)
COPIA="sql/respaldos/antes_de_actualizar_$FECHA.sql"
info "Guardando copia en $COPIA ..."
export PGPASSWORD="$DB_CLAVE"
if pg_dump -U "$DB_USUARIO" $HOST_ARG -p "$DB_PUERTO" --schema=clinica \
        "$DB_NOMBRE" > "$COPIA" 2>/dev/null; then
    ok "Copia creada ($(du -h "$COPIA" | cut -f1))"
else
    aviso "No se pudo hacer la copia. Puedes continuar, pero con riesgo."
    rm -f "$COPIA"
fi

# --- 2. Dependencias ---
echo -e "\n${NEGRITA}2. Dependencias${SIN}"
info "Revisando requirements.txt..."
pip install --quiet -r requirements.txt
ok "Dependencias al día"

# --- 3. Parches de base de datos ---
echo -e "\n${NEGRITA}3. Ajustes de base de datos${SIN}"
for parche in sql/parche_*.sql; do
    [ -f "$parche" ] || continue
    info "Aplicando $(basename "$parche")..."
    if psql -U "$DB_USUARIO" $HOST_ARG -p "$DB_PUERTO" -q \
            -d "$DB_NOMBRE" -f "$parche" 2>/dev/null; then
        ok "$(basename "$parche")"
    else
        aviso "$(basename "$parche") tuvo avisos"
    fi
done

# --- 4. Migraciones y permisos ---
echo -e "\n${NEGRITA}4. Migraciones${SIN}"
python3 manage.py migrate --fake-initial
python3 manage.py sembrar_permisos

# --- 5. Estáticos ---
echo -e "\n${NEGRITA}5. Archivos estáticos${SIN}"
python3 manage.py collectstatic --noinput >/dev/null 2>&1 && ok "Recopilados" \
    || aviso "No se pudieron recopilar"

# --- 6. Verificación ---
echo -e "\n${NEGRITA}6. Verificación${SIN}"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo
echo -e "${VERDE}${NEGRITA}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║            ACTUALIZACIÓN COMPLETADA             ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${SIN}"
[ -f "$COPIA" ] && echo "  Copia de seguridad: $COPIA"
echo "  Reinicia el sistema con:  ./iniciar.sh"
echo

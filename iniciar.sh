#!/usr/bin/env bash
# =====================================================================
#  INICIAR EL SISTEMA
# =====================================================================
#  Uso:
#      ./iniciar.sh              -> abre en este equipo (desarrollo)
#      ./iniciar.sh 0.0.0.0:8000 -> abre para otros equipos de la red
#      ./iniciar.sh --prod       -> modo producción (DEBUG=False)
# =====================================================================

AZUL='\033[0;34m'; VERDE='\033[0;32m'; AMARILLO='\033[1;33m'
ROJO='\033[0;31m'; NEGRITA='\033[1m'; SIN='\033[0m'

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo -e "${ROJO}No se encontró el entorno virtual.${SIN}"
    echo "Ejecuta primero:  ./instalar.sh"
    exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

DIRECCION="127.0.0.1:8000"
MODO="desarrollo"

for arg in "$@"; do
    case "$arg" in
        --prod) MODO="producción" ;;
        *) DIRECCION="$arg" ;;
    esac
done

if [ "$MODO" = "producción" ]; then
    export DJANGO_DEBUG=False
    aviso_prod="(modo producción)"
else
    aviso_prod=""
fi

echo -e "${AZUL}${NEGRITA}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        SISTEMA DE CITAS MÉDICAS                 ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${SIN}"
echo "  Modo:      $MODO $aviso_prod"
echo "  Dirección: http://$DIRECCION/"
echo
echo "  Para detenerlo pulsa Ctrl+C"
echo

exec python3 manage.py runserver "$DIRECCION"

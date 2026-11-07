# Sistema de Historial Médico

Sistema de gestión clínica completo, en producción en una clínica privada de Monagas, Venezuela. Registra **1.440 citas y registros mensuales** a través de 8 módulos integrados.

## Stack

- **Backend**: Django 6.1 · Python 3.14
- **Base de datos**: PostgreSQL (esquema propio, migraciones versionadas)
- **Frontend**: Bootstrap 5 · JavaScript vanilla · Select2 · Alertify
- **Despliegue**: On-premise (Linux), scripts de instalación y verificación incluidos

## Módulos

| Módulo | Descripción |
|--------|-------------|
| `citas` | Agendamiento, tipos de cita (primera vez, rutina, seguimiento, control, emergencia), calendario |
| `diagnostico` | Registro y seguimiento de diagnósticos por paciente |
| `antecedentes` | Historial clínico, alergias, cirugías, antecedentes familiares |
| `mediciones` | Signos vitales, antropometría, evolución temporal |
| `estadistica` | Dashboards y reportes sobre actividad clínica |
| `usuarios` | Roles, permisos, autenticación |
| `identificacion` | Datos demográficos y de contacto del paciente |
| `catalog` | Catálogos maestros (CIE-10, medicamentos, especialidades, etc.) |

## Instalación rápida

```bash
# 1. Clonar
git clone https://github.com/aMagnoMariani/historial_medico.git
cd historial_medico

# 2. Entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Base de datos (PostgreSQL)
sudo -u postgres psql -c "CREATE DATABASE clinica;"
sudo -u postgres psql -c "CREATE USER clinica_user WITH PASSWORD 'tu_clave';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE clinica TO clinica_user;"

# 5. Esquema
psql -U clinica_user -d clinica -h localhost -f sql/esquema_clinica.sql

# 6. Parche tipo de cita (si aplica)
psql -U clinica_user -d clinica -h localhost -f sql/parche_tipo_cita.sql

# 7. Ejecutar
python manage.py runserver 0.0.0.0:8000
```

Los scripts `instalar.sh`, `verificar.sh` y `actualizar.sh` automatizan el proceso completo en el servidor de la clínica.

## Estructura del proyecto

```
historial_medico/
├── apps/                 # 8 apps Django
│   ├── citas/
│   ├── diagnostico/
│   ├── antecedentes/
│   ├── mediciones/
│   ├── estadistica/
│   ├── usuarios/
│   ├── identificacion/
│   └── catalog/
├── sql/                  # Esquema y migraciones SQL puras
├── templates/            # Plantillas base y por app
├── staticfiles/          # Bootstrap, Select2, Alertify (offline)
├── requirements.txt
├── manage.py
└── *.sh                  # Scripts de despliegue
```

## Tests y calidad

- Migraciones Django versionadas (`apps/*/migrations/`)
- Esquema SQL documentado y reproducible
- Sin dependencias externas en runtime (assets embebidos en `staticfiles/`)

## Autor

**Alejandro Mariani** — Desarrollador Full-Stack  
📍 Venezuela · Remoto (UTC-4)  
✉️ amariani.monagas@gmail.com  
🔗 [GitHub](https://github.com/aMagnoMariani) · [LinkedIn](https://www.linkedin.com/in/alejandro-mariani-03b535351)

---

*Proyecto en producción activa. Último deploy: noviembre 2026.*

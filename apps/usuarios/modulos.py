"""Definición central de módulos, permisos y roles predefinidos.

La seguridad del sistema es propia (no depende del esquema clínico). Se
organiza por MÓDULOS, que se corresponden con las opciones del sidebar, y
cada módulo tiene submódulos (las acciones que se pueden hacer).

Reglas:
  - El permiso de eliminar SOLO lo tiene el administrador.
  - Los roles son predefinidos, pero sus permisos se pueden ajustar por
    usuario al crearlo o editarlo.
"""

# ---------------------------------------------------------------------
# MÓDULOS DEL SISTEMA  (clave, nombre para mostrar)
#
# Los submódulos del módulo "diagnostico" se separan en tres partes:
# mediciones, antecedentes y diagnostico, tal como se atiende una cita.
# ---------------------------------------------------------------------
MODULOS = [
    ('pacientes', 'Pacientes'),
    ('registrar', 'Registrar paciente'),
    ('medicos', 'Médicos'),
    ('especialidades', 'Especialidades'),
    ('direcciones', 'Direcciones'),
    ('identificacion', 'Tipos de identificación'),
    ('catalogos', 'Catálogos (etnia, sangre, discapacidad)'),
    ('citas', 'Citas'),
    ('mediciones', 'Mediciones'),
    ('antecedentes', 'Antecedentes'),
    ('diagnostico', 'Diagnóstico'),
    ('catalogo-enfermedades', 'Catálogo de enfermedades y síntomas'),
    ('config-mediciones', 'Configuración de mediciones'),
    ('estadisticas', 'Estadísticas y reportes'),
    ('usuarios', 'Usuarios'),
    ('roles', 'Roles y permisos'),
    ('configuracion', 'Configuración del sistema'),
]

# Acciones disponibles. "eliminar" es exclusiva del administrador.
ACCIONES = [
    ('ver', 'Ver'),
    ('crear', 'Crear'),
    ('editar', 'Editar'),
    ('eliminar', 'Eliminar'),
]

# Submódulos permitidos por módulo (si no se lista, se usan los 4 básicos)
SUBMODULOS = {
    'pacientes': ['ver', 'crear', 'editar', 'eliminar'],
    'registrar': ['crear'],
    'medicos': ['ver', 'crear', 'editar', 'eliminar'],
    'especialidades': ['ver', 'crear', 'editar', 'eliminar'],
    'direcciones': ['ver', 'crear', 'editar', 'eliminar'],
    'identificacion': ['ver', 'crear', 'editar'],
    'catalogos': ['ver', 'crear', 'editar'],
    'citas': ['ver', 'crear', 'editar', 'eliminar'],
    'mediciones': ['ver', 'crear', 'editar'],
    'antecedentes': ['ver', 'crear', 'editar'],
    'diagnostico': ['ver', 'crear', 'editar'],
    'catalogo-enfermedades': ['ver', 'crear', 'editar', 'eliminar'],
    'config-mediciones': ['ver', 'crear', 'editar', 'eliminar'],
    'estadisticas': ['ver', 'exportar'],
    'usuarios': ['ver', 'crear', 'editar', 'eliminar'],
    'roles': ['ver', 'crear', 'editar'],
    'configuracion': ['ver'],
}

NOMBRE_MODULOS = dict(MODULOS)
NOMBRE_ACCIONES = dict(ACCIONES)

# Módulos que se administran desde la pantalla de Configuración.
# Quien tenga el permiso 'ver' de cualquiera de ellos puede entrar.
MODULOS_CONFIGURACION = [
    'usuarios',
    'roles',
    'identificacion',
    'direcciones',
    'catalogos',
    'medicos',
    'especialidades',
    'catalogo-enfermedades',
    'config-mediciones',
    'estadisticas',
]


def tiene_acceso_configuracion(usuario):
    """True si el usuario puede entrar al Centro de Configuración."""
    if usuario.is_superuser:
        return True
    return any(usuario.tiene_permiso(f'{m}.ver') for m in MODULOS_CONFIGURACION)


def codigo(modulo, accion):
    """Código único del permiso: 'pacientes.ver'."""
    return f'{modulo}.{accion}'


def todos_los_permisos():
    """Lista de (codigo, modulo, accion, descripcion) para sembrar la BD."""
    resultado = []
    for mod, _ in MODULOS:
        for acc in SUBMODULOS.get(mod, [a for a, _ in ACCIONES]):
            resultado.append((
                codigo(mod, acc),
                mod,
                acc,
                f'{NOMBRE_ACCIONES.get(acc, acc)} en {NOMBRE_MODULOS.get(mod, mod)}',
            ))
    return resultado


def permisos_de_rol(nombre_rol):
    """Permisos predefinidos de cada rol."""
    nombre = (nombre_rol or '').strip().lower()

    # SuperAdmin: absolutamente todo (incluye eliminar en todos los módulos)
    if 'superadmin' in nombre or nombre in ('admin', 'administrador'):
        return [c for c, _, _, _ in todos_los_permisos()]

    if 'medico' in nombre or 'médico' in nombre:
        return [
            'pacientes.ver', 'pacientes.crear', 'pacientes.editar',
            'citas.ver', 'citas.editar',
            'mediciones.ver', 'mediciones.crear', 'mediciones.editar',
            'antecedentes.ver', 'antecedentes.crear', 'antecedentes.editar',
            'diagnostico.ver', 'diagnostico.crear', 'diagnostico.editar',
            'catalogo-enfermedades.ver',
            'medicos.ver', 'especialidades.ver', 'direcciones.ver',
            'estadisticas.ver',
        ]

    if 'enfermer' in nombre:
        return [
            'pacientes.ver', 'pacientes.crear', 'pacientes.editar',
            'citas.ver', 'citas.editar',
            'mediciones.ver', 'mediciones.crear', 'mediciones.editar',
            'antecedentes.ver', 'antecedentes.crear', 'antecedentes.editar',
            'medicos.ver', 'especialidades.ver', 'direcciones.ver',
        ]

    if 'recepc' in nombre or 'secretar' in nombre or 'asistente' in nombre:
        return [
            'pacientes.ver', 'pacientes.crear', 'pacientes.editar',
            'registrar.crear',
            'citas.ver', 'citas.crear', 'citas.editar',
            'medicos.ver', 'especialidades.ver', 'direcciones.ver',
            'direcciones.crear',
        ]

    # Rol sin definir: solo lectura de lo básico
    return ['citas.ver', 'pacientes.ver']


# ---------------------------------------------------------------------
# ROLES PREDEFINIDOS  (nombre, descripción)
# ---------------------------------------------------------------------
ROLES_PREDEFINIDOS = [
    ('SuperAdmin', 'Administrador del sistema, acceso total y únicos permisos de eliminar'),
    ('Medico', 'Personal médico: atiende citas, mediciones, antecedentes y diagnóstico'),
    ('Enfermera', 'Personal de enfermería: mediciones y antecedentes'),
    ('Recepcion', 'Recepción: registro de pacientes y agenda de citas'),
]


def sembrar_permisos_y_roles():
    """Crea los permisos y los roles predefinidos si no existen.

    Devuelve (permisos_creados, roles_creados).
    """
    from .models import Permiso, Rol, RolPermiso

    creados_perm = 0
    for c, mod, acc, desc in todos_los_permisos():
        _, creado = Permiso.objects.get_or_create(
            codigo=c,
            defaults={'modulo': mod, 'accion': acc, 'descripcion': desc})
        creados_perm += 1 if creado else 0

    creados_rol = 0
    for nombre, descripcion in ROLES_PREDEFINIDOS:
        rol, creado = Rol.objects.get_or_create(
            nombre=nombre,
            defaults={'descripcion': descripcion, 'estado': True})
        creados_rol += 1 if creado else 0
        # Asignar los permisos predefinidos del rol
        for c in permisos_de_rol(nombre):
            permiso = Permiso.objects.filter(codigo=c).first()
            if permiso:
                RolPermiso.objects.get_or_create(rol=rol, permiso=permiso)

    return creados_perm, creados_rol

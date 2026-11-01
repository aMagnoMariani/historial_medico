from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from datetime import date

from apps.identificacion.models import (
    Paciente, Medico, Especialidad, Etnia, Sangre, Discapacidad, Direccion,
    Identificacion, Nombres, Persona,
)
from apps.citas.models import Cita
from apps.usuarios.permissions import permiso_requerido, sin_permiso, valida_accion
from apps.usuarios.modulos import (
    MODULOS, ACCIONES, SUBMODULOS, ROLES_PREDEFINIDOS, NOMBRE_ACCIONES,
    codigo, sembrar_permisos_y_roles, permisos_de_rol,
    tiene_acceso_configuracion,
)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('usuarios:home')
    
    if request.method == 'POST':
        from django.contrib.auth.forms import AuthenticationForm
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('usuarios:home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    else:
        from django.contrib.auth.forms import AuthenticationForm
        form = AuthenticationForm()
        
    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('usuarios:login')

@login_required
def home(request):
    user = request.user

    if user.es_admin():
        # Datos para el administrador
        contexto = {
            'rol': 'Admin',
            'total_pacientes': Paciente.objects.count(),
            'pacientes_espera': Cita.objects.filter(estado_cita_id=1).count(),
            'total_medicos': Medico.objects.count(),
            'total_especialidades': Especialidad.objects.count(),
        }
        return render(request, 'usuarios/home_admin.html', contexto)

    # Personal de salud: ve lo que sus permisos le permiten
    hoy = date.today()
    contexto = {
        'rol': 'Salud',
        'espera_hoy': Cita.objects.filter(fecha_atencion=hoy, estado_cita_id=1).count()
                     if user.tiene_permiso('citas.ver') else 0,
        'atendidos_hoy': Cita.objects.filter(fecha_atencion=hoy, estado_cita_id=2).count()
                        if user.tiene_permiso('citas.ver') else 0,
        'hoy': hoy,
    }
    return render(request, 'usuarios/home_staff.html', contexto)

@login_required
def configuracion(request):
    """Centro de configuración.

    Entra quien tenga el permiso 'ver' de alguno de los módulos que se
    administran aquí (usuarios, direcciones, catálogos, etc.).
    """
    if not tiene_acceso_configuracion(request.user):
        return redirect('usuarios:home')
    return render(request, 'usuarios/configuracion.html')


@login_required
@permiso_requerido('usuarios.ver')
def gestion_usuarios(request):
    """Usuarios del sistema: datos personales + rol + permisos por módulo.

    Unifica en una sola pantalla lo que antes eran "Roles y Permisos" y
    "Usuarios". Los roles son predefinidos y cada usuario recibe sus propios
    permisos (copiados del rol al crearlo y ajustables después).
    """
    from apps.usuarios.models import Usuario, Rol, Permiso, RolPermiso, UsuarioPermiso
    from apps import catalog

    # Asegurar que existan los permisos y roles predefinidos
    sembrar_permisos_y_roles()

    if request.method == 'POST':
        action = request.POST.get('action')

        # ------------------------------------------------------ CREAR
        if action == 'crear':
            nombre_obj, _ = Nombres.objects.get_or_create(
                tipo='NOMBRE', descripcion=request.POST.get('nombre') or 'Sin nombre')
            apellido_obj, _ = Nombres.objects.get_or_create(
                tipo='APELLIDO', descripcion=request.POST.get('apellido') or 'Sin apellido')
            dir_id = request.POST.get('direccion_id') or catalog.direccion_default()

            fecha_nac = request.POST.get('fecha_nacimiento')
            if not fecha_nac:
                try:
                    edad = int(request.POST.get('edad') or 0)
                except (TypeError, ValueError):
                    edad = 0
                from datetime import date, timedelta
                fecha_nac = (date.today() - timedelta(days=edad * 365)) if edad else '1990-01-01'

            persona = Persona.objects.create(
                nombre=nombre_obj,
                apellido=apellido_obj,
                fecha_nacimiento=fecha_nac,
                direccion_id=dir_id,
                sexo=request.POST.get('sexo') or 'O',
                etnia_id=request.POST.get('etnia_id') or catalog.etnia_default(),
                sangre_id=request.POST.get('sangre_id') or catalog.sangre_default(),
                discapacidad_id=request.POST.get('discapacidad_id') or catalog.discapacidad_default(),
                telefono=request.POST.get('telefono') or None,
            )
            tipo_ident = request.POST.get('identificacion_tipo_id')
            Identificacion.objects.create(
                persona=persona,
                descripcion=request.POST.get('identificacion_tipo_desc') or 'Cedula',
                descripcion_id=tipo_ident or None,
                valor=request.POST.get('cedula') or 'S/N',
            )

            rol = Rol.objects.filter(pk=request.POST.get('rol_id') or None).first()
            user = Usuario.objects.create_user(
                username=request.POST.get('usuario'),
                password=request.POST.get('clave'),
                rol=rol,
                persona=persona,
                is_staff=True,
            )
            user.is_active = True
            user.save()

            # Permisos: si se marcaron en el formulario se usan esos;
            # si no, se copian los del rol elegido.
            marcados = [c for c in request.POST.getlist('permisos') if c]
            if not marcados and rol:
                marcados = list(RolPermiso.objects.filter(rol=rol)
                                .values_list('permiso__codigo', flat=True))
            # El permiso de eliminar SOLO lo puede tener el administrador.
            # Se comprueba el rol destino para que no se pueda colar ni
            # manipulando el formulario.
            destino_es_admin = bool(rol and rol.nombre.lower() == 'superadmin')
            if not destino_es_admin:
                marcados = [c for c in marcados if not c.endswith('.eliminar')]
            for c in marcados:
                permiso = Permiso.objects.filter(codigo=c).first()
                if permiso:
                    UsuarioPermiso.objects.get_or_create(usuario=user, permiso=permiso)

        # ------------------------------------------------------ EDITAR
        elif action == 'editar':
            user = Usuario.objects.get(pk=request.POST.get('id'))
            persona = user.persona
            if persona:
                nombre_val = request.POST.get('nombre')
                apellido_val = request.POST.get('apellido')
                if nombre_val:
                    obj, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion=nombre_val)
                    persona.nombre = obj
                if apellido_val:
                    obj, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion=apellido_val)
                    persona.apellido = obj
                if request.POST.get('direccion_id'):
                    persona.direccion_id = request.POST.get('direccion_id')
                if request.POST.get('sexo'):
                    persona.sexo = request.POST.get('sexo')
                if request.POST.get('etnia_id'):
                    persona.etnia_id = request.POST.get('etnia_id')
                if request.POST.get('sangre_id'):
                    persona.sangre_id = request.POST.get('sangre_id')
                if request.POST.get('discapacidad_id'):
                    persona.discapacidad_id = request.POST.get('discapacidad_id')
                fecha_nac = request.POST.get('fecha_nacimiento')
                if fecha_nac:
                    persona.fecha_nacimiento = fecha_nac
                persona.telefono = request.POST.get('telefono') or persona.telefono
                persona.save()

                # Cédula
                ident = persona.identificaciones.first()
                if ident:
                    ident.valor = request.POST.get('cedula') or ident.valor
                    ident.save()
                elif request.POST.get('cedula'):
                    Identificacion.objects.create(
                        persona=persona,
                        descripcion=request.POST.get('identificacion_tipo_desc') or 'Cedula',
                        descripcion_id=(request.POST.get('identificacion_tipo_id')
                                        or None),
                        tipo=2,
                        valor=request.POST.get('cedula'),
                    )

            rol = Rol.objects.filter(pk=request.POST.get('rol_id') or None).first()
            user.rol = rol
            user.username = request.POST.get('usuario') or user.username
            clave = request.POST.get('clave')
            if clave:
                user.set_password(clave)
            user.save()

            # Permisos del usuario
            UsuarioPermiso.objects.filter(usuario=user).delete()
            marcados = [c for c in request.POST.getlist('permisos') if c]
            if not marcados and rol:
                marcados = list(RolPermiso.objects.filter(rol=rol)
                                .values_list('permiso__codigo', flat=True))
            destino_es_admin = bool(rol and rol.nombre.lower() == 'superadmin')
            if not destino_es_admin:
                marcados = [c for c in marcados if not c.endswith('.eliminar')]
            for c in marcados:
                permiso = Permiso.objects.filter(codigo=c).first()
                if permiso:
                    UsuarioPermiso.objects.get_or_create(usuario=user, permiso=permiso)

        # ------------------------------------------------ ACTIVAR/DESACTIVAR
        elif action == 'activar':
            Usuario.objects.filter(pk=request.POST.get('id')).update(is_active=True)
        elif action == 'desactivar':
            Usuario.objects.filter(pk=request.POST.get('id')).update(is_active=False)

        # ------------------------------------------------------ ROLES
        elif action == 'crear_rol':
            rechazo = sin_permiso(request, 'roles.crear')
            if rechazo:
                return rechazo
            nombre = (request.POST.get('nombre_rol') or '').strip()
            if nombre and not Rol.objects.filter(nombre__iexact=nombre).exists():
                rol = Rol.objects.create(
                    nombre=nombre,
                    descripcion=(request.POST.get('descripcion_rol') or '').strip(),
                    estado=True,
                    predefinido=False,
                )
                # El permiso de eliminar solo lo tiene el administrador
                marcados = [c for c in request.POST.getlist('permisos')
                            if not c.endswith('.eliminar')]
                for c in marcados:
                    permiso = Permiso.objects.filter(codigo=c).first()
                    if permiso:
                        RolPermiso.objects.get_or_create(rol=rol, permiso=permiso)
                messages.success(request, f'Rol "{nombre}" creado.')
            else:
                messages.error(request, 'Ese nombre de rol ya existe.')

        elif action == 'editar_rol':
            rechazo = sin_permiso(request, 'roles.editar')
            if rechazo:
                return rechazo
            rol = Rol.objects.filter(pk=request.POST.get('rol_id')).first()
            if rol:
                nombre = (request.POST.get('nombre_rol') or '').strip()
                # Los roles predefinidos no se renombran
                if nombre and not rol.predefinido:
                    if not Rol.objects.filter(nombre__iexact=nombre).exclude(pk=rol.pk).exists():
                        rol.nombre = nombre
                rol.descripcion = (request.POST.get('descripcion_rol') or '').strip()
                rol.save()
                messages.success(request, f'Rol "{rol.nombre}" actualizado.')

        elif action == 'guardar_permisos_rol':
            rechazo = sin_permiso(request, 'roles.editar')
            if rechazo:
                return rechazo
            rol = Rol.objects.filter(pk=request.POST.get('rol_id')).first()
            if rol:
                # El SuperAdmin no se toca: es el rol que administra el sistema
                if rol.nombre.lower() == 'superadmin':
                    messages.error(request, 'Los permisos del SuperAdmin no se pueden modificar.')
                    return redirect('usuarios:gestion_usuarios')
                marcados = [c for c in request.POST.getlist('permisos') if c]
                # El permiso de eliminar solo lo puede tener el administrador
                marcados = [c for c in marcados if not c.endswith('.eliminar')]
                RolPermiso.objects.filter(rol=rol).delete()
                for c in marcados:
                    permiso = Permiso.objects.filter(codigo=c).first()
                    if permiso:
                        RolPermiso.objects.get_or_create(rol=rol, permiso=permiso)
                messages.success(request, f'Permisos de "{rol.nombre}" actualizados.')

        elif action == 'eliminar_rol':
            rechazo = sin_permiso(request, 'roles.editar')
            if rechazo:
                return rechazo
            rol = Rol.objects.filter(pk=request.POST.get('rol_id')).first()
            if not rol:
                messages.error(request, 'El rol no existe.')
            elif rol.predefinido:
                messages.error(request, 'Los roles predefinidos no se pueden eliminar.')
            elif rol.usuario_set.exists():
                messages.error(request, 'No se puede eliminar: hay usuarios con este rol.')
            else:
                nombre = rol.nombre
                rol.delete()
                messages.success(request, f'Rol "{nombre}" eliminado.')

        # ------------------------------------------------ ELIMINAR (solo admin)
        elif action == 'eliminar':
            if not request.user.es_admin():
                messages.error(request, 'Solo el administrador puede eliminar usuarios.')
                return redirect('usuarios:gestion_usuarios')
            Usuario.objects.filter(pk=request.POST.get('id')).delete()

        return redirect('usuarios:gestion_usuarios')

    usuarios = Usuario.objects.select_related(
        'persona__nombre', 'persona__apellido', 'rol').order_by('id')
    roles = Rol.objects.filter(estado=True).order_by('id')

    # Estructura de módulos -> submódulos para pintar los permisos
    modulos = []
    for mod, nombre_mod in MODULOS:
        subs = SUBMODULOS.get(mod, [a for a, _ in ACCIONES])
        modulos.append({
            'clave': mod,
            'nombre': nombre_mod,
            'permisos': [
                {
                    'codigo': codigo(mod, acc),
                    'nombre': NOMBRE_ACCIONES.get(acc, acc),
                    'es_eliminar': acc == 'eliminar',
                }
                for acc in subs
            ],
        })

    contexto = {
        'usuarios': usuarios,
        'roles': roles,
        'todos_los_roles': Rol.objects.prefetch_related('permisos').order_by('id'),
        'modulos': modulos,
        'roles_predefinidos': ROLES_PREDEFINIDOS,
        # (nombre, descripcion, lista de codigos) para el JavaScript
        'roles_con_permisos': [
            (nombre, desc, permisos_de_rol(nombre))
            for nombre, desc in ROLES_PREDEFINIDOS
        ],
        'etnias': Etnia.objects.all(),
        'sangre': Sangre.objects.all(),
        'discapacidades': Discapacidad.objects.all(),
        'estados': Direccion.objects.filter(divicion_politica_id=None),
        'puede_eliminar': request.user.puede_eliminar(),
    }
    return render(request, 'usuarios/gestion_usuarios.html', contexto)

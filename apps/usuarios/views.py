from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from datetime import date

from apps.identificacion.models import Paciente, Medico, Especialidad
from apps.citas.models import Cita

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
    rol_nombre = user.rol.nombre if user.rol else 'Usuario'
    
    if rol_nombre == 'SuperAdmin':
        # Datos para Admin
        contexto = {
            'rol': 'Admin',
            'total_pacientes': Paciente.objects.count(),
            'pacientes_espera': Cita.objects.filter(estado_cita_id=1).count(),
            'total_medicos': Medico.objects.count(),
            'total_especialidades': Especialidad.objects.count(),
        }
        return render(request, 'usuarios/home_admin.html', contexto)
    
    else:
        # Datos para Médicos / Enfermeras (Personal de Salud)
        hoy = date.today()
        espera_hoy = Cita.objects.filter(fecha_atencion=hoy, estado_cita_id=1).count()
        atendidos_hoy = Cita.objects.filter(fecha_atencion=hoy, estado_cita_id=2).count()
        
        contexto = {
            'rol': 'Salud',
            'espera_hoy': espera_hoy,
            'atendidos_hoy': atendidos_hoy,
            'hoy': hoy,
        }
        return render(request, 'usuarios/home_staff.html', contexto)


@login_required
def gestion_roles_permisos(request):
    from apps.usuarios.models import Rol, Permiso, RolPermiso
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'crear_rol':
            rol = Rol.objects.create(nombre=request.POST.get('nombre'), descripcion=request.POST.get('descripcion',''))
            # Asignar permisos por defecto según nombre del rol
            nombre = rol.nombre.lower()
            permisos_map = {
                'médico': ['citas.ver','citas.editar','citas.crear','pacientes.ver','pacientes.editar','medicos.ver','especialidades.ver','antecedentes.ver','antecedentes.editar','mediciones.ver','mediciones.editar','diagnostico.ver','diagnostico.editar'],
                'medico': ['citas.ver','citas.editar','citas.crear','pacientes.ver','pacientes.editar','medicos.ver','especialidades.ver','antecedentes.ver','antecedentes.editar','mediciones.ver','mediciones.editar','diagnostico.ver','diagnostico.editar'],
                'enfermero': ['citas.ver','citas.editar','pacientes.ver','antecedentes.ver','antecedentes.editar','mediciones.ver','mediciones.editar'],
                'enfermera': ['citas.ver','citas.editar','pacientes.ver','antecedentes.ver','antecedentes.editar','mediciones.ver','mediciones.editar'],
                'admin': [p.codigo for p in Permiso.objects.all()],
            }
            perms_default = []
            for key, lst in permisos_map.items():
                if key in nombre:
                    perms_default = lst
                    break
            for codigo in perms_default:
                permiso = Permiso.objects.filter(codigo=codigo).first()
                if permiso:
                    RolPermiso.objects.get_or_create(rol=rol, permiso=permiso)
        elif action == 'editar_rol':
            r = Rol.objects.get(pk=request.POST.get('id'))
            r.nombre = request.POST.get('nombre')
            r.descripcion = request.POST.get('descripcion','')
            r.save()
        elif action == 'eliminar_rol':
            Rol.objects.filter(pk=request.POST.get('id')).delete()
        elif action == 'guardar_permisos':
            rol_id = request.POST.get('rol_id')
            perms = request.POST.getlist('permisos')
            RolPermiso.objects.filter(rol_id=rol_id).delete()
            for p in perms:
                RolPermiso.objects.create(rol_id=rol_id, permiso_id=p)
        return redirect('usuarios:gestion_roles_permisos')
    
    roles = Rol.objects.prefetch_related('permisos').all()
    permisos = Permiso.objects.all()
    return render(request, 'usuarios/gestion_roles_permisos.html', {'roles': roles, 'permisos': permisos})


@login_required
def configuracion(request):
    """Hub central de configuración del sistema (solo SuperAdmin)."""
    if not request.user.rol or request.user.rol.nombre != 'SuperAdmin':
        return redirect('usuarios:home')
    return render(request, 'usuarios/configuracion.html')


@login_required
def gestion_usuarios(request):
    from apps.usuarios.models import Usuario, Rol
    from apps.identificacion.models import Nombres, Direccion, Identificacion, Persona
    from datetime import date, timedelta
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'crear':
            # Persona
            nombre_obj, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion=request.POST.get('nombre'))
            apellido_obj, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion=request.POST.get('apellido'))
            # dirección default
            direccion, _ = Direccion.objects.get_or_create(dsc='s/n', tipo=1)
            edad = int(request.POST.get('edad') or 0)
            fecha_nac = date.today() - timedelta(days=edad*365)
            persona = Persona.objects.create(
                nombre=nombre_obj,
                apellido=apellido_obj,
                fecha_nacimiento=fecha_nac,
                direccion=direccion,
                sexo='O',
                telefono=request.POST.get('telefono','')
            )
            # identificación cedula
            Identificacion.objects.create(persona=persona, dsc='Cédula', tipo=1, valor=request.POST.get('cedula',''))
            # usuario
            user = Usuario.objects.create_user(
                username=request.POST.get('usuario'),
                password=request.POST.get('clave'),
                rol_id=request.POST.get('rol_id') or None,
                persona=persona,
                is_staff=True
            )
            user.is_active = True
            user.save()
        elif action == 'editar':
            user = Usuario.objects.get(pk=request.POST.get('id'))
            # actualizar datos persona
            persona = user.persona
            if persona:
                nombre_val = request.POST.get('nombre')
                apellido_val = request.POST.get('apellido')
                if nombre_val:
                    nombre_obj, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion=nombre_val)
                    persona.nombre = nombre_obj
                if apellido_val:
                    apellido_obj, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion=apellido_val)
                    persona.apellido = apellido_obj
                edad = int(request.POST.get('edad') or 0)
                if edad:
                    persona.fecha_nacimiento = date.today() - timedelta(days=edad*365)
                persona.telefono = request.POST.get('telefono','')
                persona.save()
                # cedula
                ident = persona.identificaciones.first()
                if ident:
                    ident.valor = request.POST.get('cedula','')
                    ident.save()
            user.username = request.POST.get('usuario')
            user.rol_id = request.POST.get('rol_id') or None
            clave = request.POST.get('clave')
            if clave:
                user.set_password(clave)
            user.save()
        elif action == 'activar':
            u = Usuario.objects.get(pk=request.POST.get('id'))
            u.is_active = True
            u.save()
        elif action == 'desactivar':
            u = Usuario.objects.get(pk=request.POST.get('id'))
            u.is_active = False
            u.save()
        return redirect('usuarios:gestion_usuarios')
    
    usuarios = Usuario.objects.select_related('persona__nombre','persona__apellido','rol').all()
    roles = Rol.objects.all()
    return render(request, 'usuarios/gestion_usuarios.html', {'usuarios': usuarios, 'roles': roles})

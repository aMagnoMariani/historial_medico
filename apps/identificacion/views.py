import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from apps.usuarios.permissions import permiso_requerido
import datetime

from .models import (Persona, Paciente, Nombres, Direccion, 
                     Identificacion, Sangre, Etnia, Discapacidad)
from apps.citas.models import Cita
from apps.identificacion.models import Medico, Especialidad
from apps.antecedentes.models import AntecedenteCategoria, AntecedentesSalud

@login_required
def lista_pacientes(request):
    pacientes = Paciente.objects.all().select_related('persona__nombre', 'persona__apellido')
    return render(request, 'identificacion/lista_pacientes.html', {'pacientes': pacientes})

ESTADO_CITA_MAP = {
    1: 'En espera',
    2: 'Atendido',
    3: 'Cancelada',
}

@login_required
def detalle_paciente(request, pk):
    from apps.mediciones.models import MedicionesCabecera
    from apps.diagnostico.models import Consulta, Diagnostico, Enfermedad, Sintomas

    paciente = get_object_or_404(
        Paciente.objects.select_related('persona__nombre', 'persona__apellido',
                                        'persona__sangre', 'persona__discapacidad'),
        pk=pk)

    # Todas las visitas del paciente con su diagnóstico
    citas = (Cita.objects.filter(paciente=paciente)
             .select_related('medico__persona__nombre', 'medico__persona__apellido')
             .order_by('-fecha_atencion'))
    visitas = []
    for cita in citas:
        consulta = Consulta.objects.filter(cita=cita).first()
        enfermedades = []
        sintomas = []
        if consulta:
            diag = Diagnostico.objects.filter(consulta=consulta).first()
            if diag:
                enfermedades = list(Enfermedad.objects.filter(diagnostico=diag))
                sintomas = list(Sintomas.objects.filter(diagnostico=diag))
        visitas.append({
            'cita': cita,
            'estado': ESTADO_CITA_MAP.get(cita.estado_cita_id, 'Desconocido'),
            'enfermedades': enfermedades,
            'sintomas': sintomas,
        })

    # Todas las mediciones tomadas al paciente (con su detalle)
    mediciones = (MedicionesCabecera.objects.filter(paciente=paciente)
                  .prefetch_related('medicionesdetalles_set__equipo_parametro__equipo',
                                    'medicionesdetalles_set__equipo_parametro__parametro')
                  .order_by('-fecha_toma'))

    # Antecedentes divididos: salud / familiares
    ant_qs = (AntecedentesSalud.objects.filter(paciente=paciente)
              .select_related('antecedente_salud_id__dep_id'))
    antecedentes_salud, antecedentes_familiares = [], []
    for a in ant_qs:
        cat = a.antecedente_salud_id
        raiz = cat.dep_id if cat.dep_id_id else cat
        if raiz and raiz.dsc == 'Antecedentes Familiares':
            antecedentes_familiares.append(a)
        else:
            antecedentes_salud.append(a)

    return render(request, 'identificacion/detalle_paciente.html', {
        'paciente': paciente,
        'visitas': visitas,
        'mediciones': mediciones,
        'antecedentes_salud': antecedentes_salud,
        'antecedentes_familiares': antecedentes_familiares,
    })

@login_required
@permiso_requerido('pacientes.editar')
def registrar_paciente(request):
    if request.method == 'POST':
        try:
            # 1. Nombres y Apellidos
            nombre, _ = Nombres.objects.get_or_create(
                tipo='NOMBRE', descripcion=request.POST.get('nombre')
            )
            apellido, _ = Nombres.objects.get_or_create(
                tipo='APELLIDO', descripcion=request.POST.get('apellido')
            )
            
            # 2. Dirección
            dir_id = request.POST.get('direccion_id')
            direccion = Direccion.objects.get(id=dir_id)
            
            # 3. Persona
            persona = Persona.objects.create(
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=request.POST.get('fecha_nacimiento'),
                direccion=direccion,
                sexo=request.POST.get('sexo'),
                etnia_id=request.POST.get('etnia_id') or None,
                sangre_id=request.POST.get('sangre_id') or None,
                discapacidad_id=request.POST.get('discapacidad_id') or None,
            )
            
            # 4. Paciente
            paciente = Paciente.objects.create(persona=persona)
            
            # 5. Identificación (tipo desde el catálogo configurable)
            tipo_id = request.POST.get('identificacion_tipo_id')
            cat = Identificacion.objects.filter(
                pk=tipo_id, persona__isnull=True).first() if tipo_id else None
            Identificacion.objects.create(
                persona=persona,
                dsc=cat.dsc if cat else (request.POST.get('identificacion_tipo_desc') or 'Cédula'),
                depid=cat,
                tipo=1,
                valor=request.POST.get('identificacion_valor')
            )
            
            # 6. Cita (Opcional)
            medico_id = request.POST.get('medico_id')
            if medico_id:
                Cita.objects.create(
                    medico_id=medico_id,
                    paciente=paciente,
                    fecha_atencion=request.POST.get('cita_fecha'),
                    fecha_creacion=datetime.time(10, 0),
                    estado_cita_id=1,
                    tipo_cita=request.POST.get('cita_tipo')
                )

            return redirect('identificacion:lista_pacientes')
        except Exception as e:
            print(f"Error registrando: {e}")
            return render(request, 'identificacion/registrar_paciente.html', {'error': str(e)})

    contexto = {
        'etnias': Etnia.objects.all(),
        'sangre': Sangre.objects.all(),
        'estados': Direccion.objects.filter(depid__isnull=True),
        'medicos': Medico.objects.all(),
        'especialidades': Especialidad.objects.all(),
        'antec_raices': AntecedenteCategoria.objects.filter(dep_id__isnull=True),
        'tipos_identificacion': Identificacion.objects.filter(persona__isnull=True),
        'discapacidades': Discapacidad.objects.all(),
    }
    return render(request, 'identificacion/registrar_paciente.html', contexto)

def api_direcciones(request):
    parent_id = request.GET.get('parent_id')
    if parent_id:
        dirs = Direccion.objects.filter(depid_id=parent_id).values('id', 'dsc')
    else:
        dirs = Direccion.objects.filter(depid__isnull=True).values('id', 'dsc')
    return JsonResponse(list(dirs), safe=False)

def api_antecedentes(request):
    parent_id = request.GET.get('parent_id')
    if parent_id:
        cats = AntecedenteCategoria.objects.filter(dep_id_id=parent_id).values('id', 'dsc')
    else:
        cats = AntecedenteCategoria.objects.filter(dep_id__isnull=True).values('id', 'dsc')
    return JsonResponse(list(cats), safe=False)

@csrf_exempt
@csrf_exempt
def api_crear_sector(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        nueva_dir = Direccion.objects.create(
            dsc=data.get('nombre'),
            depid_id=data.get('parent_id'),
            tipo=4
        )
        return JsonResponse({'id': nueva_dir.id, 'dsc': nueva_dir.dsc})
    return HttpResponse(status=405)

@login_required
@permiso_requerido('medicos.editar')
def gestion_medicos(request):
    if request.method == 'POST':
        try:
            # Datos personales
            nombre, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion=request.POST.get('nombre'))
            apellido, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion=request.POST.get('apellido'))
            direccion = Direccion.objects.get(id=request.POST.get('direccion_id'))
            persona = Persona.objects.create(
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=request.POST.get('fecha_nacimiento'),
                direccion=direccion,
                sexo=request.POST.get('sexo'),
                etnia_id=request.POST.get('etnia_id') or None,
                sangre_id=request.POST.get('sangre_id') or None,
            )
            # Identificación
            Identificacion.objects.create(
                persona=persona,
                dsc=request.POST.get('identificacion_tipo') or 'Cédula',
                tipo=1,
                valor=request.POST.get('identificacion_valor') or ''
            )
            Medico.objects.create(
                persona=persona,
                especialidad_id=request.POST.get('especialidad_id'),
                estado=True
            )
            return redirect('identificacion:gestion_medicos')
        except Exception as e:
            print(f"Error registrando medico: {e}")

    medicos = Medico.objects.select_related('persona__nombre', 'persona__apellido', 'especialidad').all()
    contexto = {
        'medicos': medicos,
        'etnias': Etnia.objects.all(),
        'sangre': Sangre.objects.all(),
        'estados': Direccion.objects.filter(depid__isnull=True),
        'especialidades': Especialidad.objects.all(),
    }
    return render(request, 'identificacion/gestion_medicos.html', contexto)

@login_required
@permiso_requerido('especialidades.editar')
def gestion_especialidades(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'crear':
            Especialidad.objects.create(descripcion=request.POST.get('descripcion'), estado=True)
        elif action == 'editar':
            esp = get_object_or_404(Especialidad, pk=request.POST.get('id'))
            esp.descripcion = request.POST.get('descripcion')
            esp.save()
        elif action == 'activar':
            esp = get_object_or_404(Especialidad, pk=request.POST.get('id'))
            esp.estado = True
            esp.save()
        elif action == 'desactivar':
            esp = get_object_or_404(Especialidad, pk=request.POST.get('id'))
            esp.estado = False
            esp.save()
        return redirect('identificacion:gestion_especialidades')

    especialidades = Especialidad.objects.all().order_by('id')
    return render(request, 'identificacion/gestion_especialidades.html', {'especialidades': especialidades})


TIPOS_DIRECCION = ((1, 'Estado'), (2, 'Municipio'), (3, 'Parroquia'), (4, 'Sector / Calle'))

# Catálogos simples de persona: (modelo, campo, título)
CATALOGOS_PERSONA = {
    'etnia': (Etnia, 'tipo_etnia', 'Etnias'),
    'sangre': (Sangre, 'tipo_sangre', 'Tipos de Sangre'),
    'discapacidad': (Discapacidad, 'tipo_discapacidad', 'Discapacidades'),
}


@login_required
@permiso_requerido('pacientes.editar')
def gestion_catalogo_persona(request, tipo):
    """CRUD genérico de catálogos simples: etnia, sangre, discapacidad."""
    from django.http import Http404
    if tipo not in CATALOGOS_PERSONA:
        raise Http404(f'Catálogo desconocido: {tipo}')
    modelo, campo, titulo = CATALOGOS_PERSONA[tipo]
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'crear':
            modelo.objects.create(**{campo: request.POST.get('dsc')})
        elif action == 'editar':
            obj = get_object_or_404(modelo, pk=request.POST.get('id'))
            setattr(obj, campo, request.POST.get('dsc'))
            obj.save()
        return redirect('identificacion:gestion_catalogo_persona', tipo=tipo)
    items = modelo.objects.all().order_by('id')
    return render(request, 'identificacion/gestion_catalogo_persona.html', {
        'items': items,
        'titulo': titulo,
        'tipo': tipo,
    })


@login_required
@permiso_requerido('pacientes.editar')
def gestion_tipos_identificacion(request):
    """Catálogo de tipos de identificación (Cédula, Pasaporte...).

    Las entradas de catálogo no tienen persona ni valor; los pacientes
    referencian el tipo mediante el campo depid.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'crear':
            Identificacion.objects.create(
                dsc=request.POST.get('dsc'),
                depid_id=request.POST.get('depid') or None,
                tipo=request.POST.get('tipo') or 1,
                valor=None,
                persona=None)
        elif action == 'editar':
            tipo_obj = get_object_or_404(Identificacion, pk=request.POST.get('id'),
                                         persona__isnull=True)
            tipo_obj.dsc = request.POST.get('dsc')
            tipo_obj.tipo = request.POST.get('tipo') or tipo_obj.tipo
            tipo_obj.depid_id = request.POST.get('depid') or None
            tipo_obj.save()
        return redirect('identificacion:gestion_tipos_identificacion')
    catalogo = (Identificacion.objects
                .filter(persona__isnull=True)
                .select_related('depid').order_by('id'))
    return render(request, 'identificacion/gestion_tipos_identificacion.html',
                  {'catalogo': catalogo})


@login_required
@permiso_requerido('pacientes.editar')
def gestion_direcciones(request):
    """Jerarquía de direcciones: Estado → Municipio → Parroquia → Sector/Calle.

    El padre permitido es siempre el nivel inmediatamente superior:
    Municipio→Estado, Parroquia→Municipio, Sector→Parroquia.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        tipo = int(request.POST.get('tipo') or 1)
        depid = request.POST.get('depid') or None
        if tipo == 1:
            depid = None  # Un Estado no tiene padre
        elif depid:
            padre = Direccion.objects.filter(pk=depid).first()
            if not padre or padre.tipo != tipo - 1:
                # Padre inválido para ese nivel: se ignora para no romper la jerarquía
                depid = None
        if action == 'crear':
            Direccion.objects.create(
                dsc=request.POST.get('dsc'), depid_id=depid, tipo=tipo)
        elif action == 'editar':
            dir_obj = get_object_or_404(Direccion, pk=request.POST.get('id'))
            dir_obj.dsc = request.POST.get('dsc')
            dir_obj.tipo = tipo
            dir_obj.depid_id = depid
            dir_obj.save()
        return redirect('identificacion:gestion_direcciones')

    direcciones = Direccion.objects.select_related('depid').order_by('dsc')
    grupos = []
    for val, etiqueta in TIPOS_DIRECCION:
        grupos.append({
            'tipo': val,
            'etiqueta': etiqueta,
            'items': [d for d in direcciones if d.tipo == val],
        })
    return render(request, 'identificacion/gestion_direcciones.html', {
        'direcciones': direcciones,
        'grupos': grupos,
        'tipos': TIPOS_DIRECCION,
    })


@login_required
def historial_paciente(request, pk):
    from apps.mediciones.models import MedicionesCabecera
    from apps.antecedentes.models import AntecedentesSalud
    from apps.diagnostico.models import Consulta, Diagnostico
    paciente = get_object_or_404(Paciente, pk=pk)
    mediciones = MedicionesCabecera.objects.filter(paciente=paciente).order_by('-fecha_toma')[:10]
    antecedentes = AntecedentesSalud.objects.filter(paciente=paciente).select_related('antecedente_salud_id')
    consultas = Consulta.objects.filter(cita__paciente=paciente).select_related('cita').order_by('-cita__fecha_atencion')[:10]
    rol_nombre = request.user.rol.nombre if request.user.rol else ''
    return render(request, 'identificacion/historial_paciente.html', {
        'paciente': paciente,
        'mediciones': mediciones,
        'antecedentes': antecedentes,
        'consultas': consultas,
        'rol_nombre': rol_nombre,
    })


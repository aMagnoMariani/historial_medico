import datetime
import json

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from apps import catalog
from apps.catalog import (TIPOS_ANTECEDENTE, TIPOS_DIRECCION,
                          TIPOS_IDENTIFICACION)
from apps.usuarios.permissions import permiso_requerido, valida_accion

from .models import (Persona, Paciente, Nombres, Direccion,
                     Identificacion, Sangre, Etnia, Discapacidad)
from apps.citas.models import Cita, TipoCita
from apps.identificacion.models import Medico, Especialidad
from apps.antecedentes.models import AntecedentesSalud

ESTADO_CITA_MAP = {
    1: 'En espera',
    2: 'Atendido',
    3: 'Cancelada',
}


@login_required
def lista_pacientes(request):
    pacientes = Paciente.objects.all().select_related(
        'persona__nombre', 'persona__apellido')
    return render(request, 'identificacion/lista_pacientes.html',
                  {'pacientes': pacientes})


@login_required
def detalle_paciente(request, pk):
    from apps.mediciones.models import MedicionesCabecera
    from apps.diagnostico.models import Consulta, Diagnostico, Enfermedad, Sintomas

    paciente = get_object_or_404(
        Paciente.objects.select_related(
            'persona__nombre', 'persona__apellido',
            'persona__sangre', 'persona__discapacidad'),
        pk=pk)

    # Todas las visitas del paciente con su diagnostico
    citas = (Cita.objects.filter(paciente=paciente)
             .select_related('medico__persona__nombre',
                             'medico__persona__apellido')
             .order_by('-fecha_atencion'))
    visitas = []
    for cita in citas:
        consulta = Consulta.objects.filter(cita=cita).first()
        enfermedades, sintomas = [], []
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

    # Mediciones del paciente (con su detalle)
    mediciones = (MedicionesCabecera.objects.filter(paciente=paciente)
                  .prefetch_related('medicionesdetalles_set__equipo_parametro__equipo',
                                    'medicionesdetalles_set__equipo_parametro__parametro')
                  .order_by('-fecha_toma'))

    # Antecedentes: descrip indica si es personal o familiar
    ant_qs = AntecedentesSalud.objects.filter(paciente=paciente).order_by('id')
    antecedentes_salud = [a for a in ant_qs if a.descrip == 'Antecedente Personal']
    antecedentes_familiares = [a for a in ant_qs if a.descrip == 'Antecedente Familiar']

    return render(request, 'identificacion/detalle_paciente.html', {
        'paciente': paciente,
        'visitas': visitas,
        'mediciones': mediciones,
        'antecentes_salud': antecedentes_salud,
        'antecentes_familiares': antecedentes_familiares,
    })


@login_required
@permiso_requerido('pacientes.crear')
def registrar_paciente(request):
    if request.method == 'POST':
        try:
            # 1. Nombres y Apellidos
            nombre, _ = Nombres.objects.get_or_create(
                tipo='NOMBRE', descripcion=request.POST.get('nombre') or 'Sin nombre')
            apellido, _ = Nombres.objects.get_or_create(
                tipo='APELLIDO', descripcion=request.POST.get('apellido') or 'Sin apellido')

            # 2. Direccion (NOT NULL)
            dir_id = request.POST.get('direccion_id') or catalog.direccion_default()

            # 3. Persona (todas las FK son NOT NULL en el esquema)
            persona = Persona.objects.create(
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=request.POST.get('fecha_nacimiento') or '1990-01-01',
                direccion_id=dir_id,
                sexo=request.POST.get('sexo') or 'O',
                etnia_id=request.POST.get('etnia_id') or catalog.etnia_default(),
                sangre_id=request.POST.get('sangre_id') or catalog.sangre_default(),
                discapacidad_id=request.POST.get('discapacidad_id') or catalog.discapacidad_default(),
                telefono=request.POST.get('telefono') or None,
            )

            # 4. Paciente
            paciente = Paciente.objects.create(persona=persona)

            # 5. Identificacion (valor y persona_id son NOT NULL)
            tipo_id = request.POST.get('identificacion_tipo_id')
            tipo = Identificacion.objects.filter(pk=tipo_id).first() if tipo_id else None
            Identificacion.objects.create(
                persona=persona,
                descripcion=(tipo.descripcion if tipo
                             else request.POST.get('identificacion_tipo_desc') or 'Cedula'),
                descripcion_id=tipo.id if tipo else 0,
                tipo=2 if tipo else 1,
                valor=request.POST.get('identificacion_valor') or 'S/N',
            )

            # 6. Cita (opcional)
            medico_id = request.POST.get('medico_id')
            if medico_id:
                Cita.objects.create(
                    medico_id=medico_id,
                    paciente=paciente,
                    fecha_atencion=request.POST.get('cita_fecha') or '2026-01-01',
                    fecha_creacion=datetime.time(10, 0),
                    estado_cita_id=1,
                    tipo_cita=request.POST.get('tipo_cita') or None,
                )

            return redirect('identificacion:lista_pacientes')
        except Exception as e:
            print(f"Error registrando paciente: {e}")
            return render(request, 'identificacion/registrar_paciente.html',
                          {'error': str(e)})

    contexto = {
        'etnias': Etnia.objects.all(),
        'sangre': Sangre.objects.all(),
        'estados': Direccion.objects.filter(divicion_politica_id=None),
        'medicos': Medico.objects.all(),
        'especialidades': Especialidad.objects.all(),
        'discapacidades': Discapacidad.objects.all(),
        'tipos_antecedente': TIPOS_ANTECEDENTE,
        'tipos_cita': TipoCita.choices,
        'tipos_identificacion': Identificacion.objects.filter(
            persona__nombre__descripcion='CATALOGO'),
    }
    return render(request, 'identificacion/registrar_paciente.html', contexto)


def api_direcciones(request):
    parent_id = request.GET.get('parent_id')
    if parent_id:
        dirs = Direccion.objects.filter(
            divicion_politica_id=parent_id).values('id', 'valor', 'division_politica')
    else:
        dirs = Direccion.objects.filter(
            divicion_politica_id=None).values('id', 'valor', 'division_politica')
    return JsonResponse(list(dirs), safe=False)


def api_antecedentes(request):
    """Devuelve los tipos de antecedente disponibles."""
    return JsonResponse(
        [{'id': i, 'descrip': d} for i, (d, _) in enumerate(TIPOS_ANTECEDENTE)],
        safe=False)


def api_tipos_identificacion(request):
    tipos = Identificacion.objects.filter(
        persona__nombre__descripcion='CATALOGO').values('id', 'descripcion')
    return JsonResponse(list(tipos), safe=False)


@csrf_exempt
def api_crear_sector(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nueva_dir = Direccion.objects.create(
            division_politica=data.get('division_politica', 'Calle / Sector'),
            valor=data.get('valor') or 'S/N',
            tipo=4,
            divicion_politica_id=data.get('parent_id') or 0
        )
        return JsonResponse({'id': nueva_dir.id,
                             'valor': nueva_dir.valor,
                             'division_politica': nueva_dir.division_politica})
    return HttpResponse(status=405)


@login_required
@permiso_requerido('medicos.ver')
def gestion_medicos(request):
    if request.method == 'POST':
        try:
            nombre, _ = Nombres.objects.get_or_create(
                tipo='NOMBRE', descripcion=request.POST.get('nombre') or 'Sin nombre')
            apellido, _ = Nombres.objects.get_or_create(
                tipo='APELLIDO', descripcion=request.POST.get('apellido') or 'Sin apellido')
            dir_id = request.POST.get('direccion_id') or catalog.direccion_default()
            persona = Persona.objects.create(
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=request.POST.get('fecha_nacimiento') or '1990-01-01',
                direccion_id=dir_id,
                sexo=request.POST.get('sexo') or 'O',
                etnia_id=request.POST.get('etnia_id') or catalog.etnia_default(),
                sangre_id=request.POST.get('sangre_id') or catalog.sangre_default(),
                discapacidad_id=request.POST.get('discapacidad_id') or catalog.discapacidad_default(),
                telefono=request.POST.get('telefono') or None,
            )
            Identificacion.objects.create(
                persona=persona,
                descripcion=request.POST.get('identificacion_tipo') or 'Cedula',
                descripcion_id=(request.POST.get('identificacion_tipo_id')
                                or catalog.tipo_identificacion_default().id),
                tipo=2,
                valor=request.POST.get('identificacion_valor') or 'S/N',
            )
            Medico.objects.create(
                persona=persona,
                especialidad_id=request.POST.get('especialidad_id'),
                estado=True
            )
            return redirect('identificacion:gestion_medicos')
        except Exception as e:
            print(f"Error registrando medico: {e}")

    medicos = Medico.objects.select_related(
        'persona__nombre', 'persona__apellido', 'especialidad').all()
    contexto = {
        'medicos': medicos,
        'etnias': Etnia.objects.all(),
        'sangre': Sangre.objects.all(),
        'discapacidades': Discapacidad.objects.all(),
        'estados': Direccion.objects.filter(divicion_politica_id=None),
        'especialidades': Especialidad.objects.all(),
        'tipos_identificacion': Identificacion.objects.filter(
            persona__nombre__descripcion='CATALOGO'),
    }
    return render(request, 'identificacion/gestion_medicos.html', contexto)


@login_required
@permiso_requerido('especialidades.ver')
def gestion_especialidades(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        rechazo = valida_accion(request, action, 'especialidades')
        if rechazo:
            return rechazo
        rechazo = valida_accion(request, action, 'medicos')
        if rechazo:
            return rechazo
        if action == 'crear':
            Especialidad.objects.create(descripcion=request.POST.get('descripcion'),
                                        estado=True)
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
    return render(request, 'identificacion/gestion_especialidades.html',
                  {'especialidades': especialidades})


# Catalogos simples de persona: (modelo, campo, titulo)
CATALOGOS_PERSONA = {
    'etnia': (Etnia, 'tipo_etnia', 'Etnias'),
    'sangre': (Sangre, 'tipo_sangre', 'Tipos de Sangre'),
    'discapacidad': (Discapacidad, 'discapacidad', 'Discapacidades'),
}


@login_required
@permiso_requerido('catalogos.ver')
def gestion_catalogo_persona(request, tipo):
    """CRUD generico de catalogos simples: etnia, sangre, discapacidad."""
    from django.http import Http404
    if tipo not in CATALOGOS_PERSONA:
        raise Http404(f'Catalogo desconocido: {tipo}')
    modelo, campo, titulo = CATALOGOS_PERSONA[tipo]
    if request.method == 'POST':
        action = request.POST.get('action')
        rechazo = valida_accion(request, action, 'catalogos')
        if rechazo:
            return rechazo
        if action == 'crear':
            modelo.objects.create(**{campo: request.POST.get('dsc') or 'S/N'})
        elif action == 'editar':
            obj = get_object_or_404(modelo, pk=request.POST.get('id'))
            setattr(obj, campo, request.POST.get('dsc') or 'S/N')
            obj.save()
        return redirect('identificacion:gestion_catalogo_persona', tipo=tipo)
    items = modelo.objects.all().order_by('id')
    return render(request, 'identificacion/gestion_catalogo_persona.html', {
        'items': items,
        'titulo': titulo,
        'tipo': tipo,
    })


@login_required
@permiso_requerido('identificacion.ver')
def gestion_tipos_identificacion(request):
    """Catalogo de tipos de documento (Cedula, Pasaporte...) y subtipos.

    Estructura de ancla: id 0 = NINGUNO, tipo 1 = Documento (raíz),
    tipo 2 = Subtipo. El padre apunta siempre a una fila.
    """
    persona = catalog.persona_catalogo()

    if request.method == 'POST':
        action = request.POST.get('action')
        rechazo = valida_accion(request, action, 'identificacion')
        if rechazo:
            return rechazo

        # 1 = Documento (raíz -> NINGUNO), 2 = Subtipo (cuelga de un documento)
        tipo = 2 if request.POST.get('tipo') == '2' else 1
        depid = 0
        if tipo == 2:
            try:
                propuesto = int(request.POST.get('descripcion_id') or 0)
            except (TypeError, ValueError):
                propuesto = 0
            if propuesto and Identificacion.objects.filter(
                    id=propuesto, tipo=1).exists():
                depid = propuesto

        descripcion = (request.POST.get('descripcion') or 'S/N').strip()

        if action == 'crear':
            Identificacion.objects.create(
                persona=persona,
                descripcion=descripcion,
                descripcion_id=depid,
                valor='TIPO',
                tipo=tipo,
            )
        elif action == 'editar':
            tipo_obj = get_object_or_404(Identificacion,
                                         pk=request.POST.get('id'))
            tipo_obj.descripcion = descripcion
            tipo_obj.descripcion_id = depid
            tipo_obj.tipo = tipo
            tipo_obj.save()
        return redirect('identificacion:gestion_tipos_identificacion')

    catalogo = (Identificacion.objects
                .filter(persona=persona)
                .exclude(id=0)
                .order_by('tipo', 'descripcion'))
    # Nombre legible del padre (descripcion_id es una columna integer)
    mapa = {d.id: d.descripcion for d in Identificacion.objects.all()}
    for t in catalogo:
        t.padre_valor = mapa.get(t.descripcion_id, 'NINGUNO')

    # Padres válidos por nivel
    documentos = Identificacion.objects.filter(tipo=1).exclude(id=0).order_by('descripcion')
    padres_json = json.dumps({
        '1': [{'id': 0, 'valor': 'NINGUNO'}],
        '2': [{'id': d.id, 'valor': d.descripcion} for d in documentos],
    }, ensure_ascii=False)

    return render(request, 'identificacion/gestion_tipos_identificacion.html',
                  {'catalogo': catalogo,
                   'tipos': TIPOS_IDENTIFICACION,
                   'padres_json': padres_json})


@login_required
@permiso_requerido('direcciones.ver')
def gestion_direcciones(request):
    """Jerarquia: Estado -> Municipio -> Parroquia -> Calle/Sector.

    Ninguna fila queda huérfana: el padre siempre apunta a una fila
    (0 = NINGUNO si es raíz) y el selector solo ofrece el nivel anterior.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        rechazo = valida_accion(request, action, 'direcciones')
        if rechazo:
            return rechazo

        tipo = request.POST.get('tipo')
        try:
            tipo = int(tipo)
        except (TypeError, ValueError):
            tipo = 1
        if tipo not in dict(TIPOS_DIRECCION):
            tipo = 1

        etiqueta_nivel = dict(TIPOS_DIRECCION)[tipo]

        # Padre: 0 (ancla) si es raíz; si no, el id recibido si existe y es
        # del nivel inmediatamente anterior.
        depid = 0
        if tipo > 1:
            try:
                propuesto = int(request.POST.get('divicion_politica_id') or 0)
            except (TypeError, ValueError):
                propuesto = 0
            if propuesto and Direccion.objects.filter(
                    id=propuesto, tipo=tipo - 1).exists():
                depid = propuesto

        valor = (request.POST.get('valor') or 'S/N').strip()

        if action == 'crear':
            Direccion.objects.create(
                division_politica=etiqueta_nivel,
                valor=valor,
                tipo=tipo,
                divicion_politica_id=depid,
            )
        elif action == 'editar':
            dir_obj = get_object_or_404(Direccion, pk=request.POST.get('id'))
            dir_obj.division_politica = etiqueta_nivel
            dir_obj.valor = valor
            dir_obj.tipo = tipo
            dir_obj.divicion_politica_id = depid
            dir_obj.save()
        return redirect('identificacion:gestion_direcciones')

    # Asegurar que exista la fila ancla
    if not Direccion.objects.filter(id=0).exists():
        Direccion.objects.create(id=0, division_politica='NINGUNO',
                                 valor='NINGUNO', tipo=0, divicion_politica_id=0)

    direcciones = list(Direccion.objects.exclude(id=0).order_by('tipo', 'valor'))
    mapa = {d.id: d.valor for d in Direccion.objects.all()}

    def padre_de(d):
        return mapa.get(d.divicion_politica_id, 'NINGUNO')

    grupos = [{
        'tipo': valor,
        'etiqueta': etiqueta,
        'items': [{'d': d, 'padre': padre_de(d)} for d in direcciones
                  if d.tipo == valor],
    } for valor, etiqueta in TIPOS_DIRECCION]

    # Opciones de padre por nivel (para el selector del formulario)
    padres_por_tipo = {}
    for valor, etiqueta in TIPOS_DIRECCION:
        if valor == 1:
            padres_por_tipo[valor] = [{'id': 0, 'valor': 'NINGUNO'}]
        else:
            padres_por_tipo[valor] = [
                {'id': d.id, 'valor': d.valor}
                for d in Direccion.objects.filter(tipo=valor - 1)
                .exclude(id=0).order_by('valor')]
    return render(request, 'identificacion/gestion_direcciones.html', {
        'grupos': grupos,
        'tipos': TIPOS_DIRECCION,
        'padres_json': json.dumps(
            {str(v): lst for v, lst in padres_por_tipo.items()},
            ensure_ascii=False),
        'tipos_labels': json.dumps(
            {str(v): e for v, e in TIPOS_DIRECCION}, ensure_ascii=False),
    })


@login_required
def historial_paciente(request, pk):
    from apps.mediciones.models import MedicionesCabecera
    from apps.diagnostico.models import Consulta, Diagnostico
    paciente = get_object_or_404(Paciente, pk=pk)
    mediciones = MedicionesCabecera.objects.filter(
        paciente=paciente).order_by('-fecha_toma')[:10]
    antecedentes = AntecedentesSalud.objects.filter(paciente=paciente).order_by('id')
    consultas = Consulta.objects.filter(
        cita__paciente=paciente).select_related('cita').order_by(
        '-cita__fecha_atencion')[:10]
    rol_nombre = request.user.rol.nombre if request.user.rol else ''
    return render(request, 'identificacion/historial_paciente.html', {
        'paciente': paciente,
        'mediciones': mediciones,
        'antecentes': antecedentes,
        'consultas': consultas,
        'rol_nombre': rol_nombre,
    })

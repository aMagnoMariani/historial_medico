from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.usuarios.permissions import permiso_requerido
from apps.diagnostico.models import Consulta
from apps.citas.models import Cita

ESTADO_MAP = {
    1: 'En espera',
    2: 'Atendido',
    3: 'Cancelada',
}

@login_required
@permiso_requerido('citas.ver')
def historial_medico(request):
    return render(request, 'diagnostico/historial_medico.html')

@login_required
@permiso_requerido('citas.ver')
def api_buscar_historial(request):
    q = request.GET.get('q', '').strip()
    fecha = request.GET.get('fecha', '').strip()
    estado = request.GET.get('estado', '').strip().lower()

    consultas = Consulta.objects.select_related(
        'cita__paciente__persona__nombre',
        'cita__paciente__persona__apellido',
        'cita__medico__persona__nombre',
        'cita__medico__persona__apellido'
    )

    # Filtrar por cédula del paciente
    if q:
        consultas = consultas.filter(
            Q(cita__paciente__persona__identificaciones__valor__icontains=q)
        )

    # Filtrar por fecha de atención
    if fecha:
        consultas = consultas.filter(cita__fecha_atencion=fecha)

    # Filtrar por estado
    if estado:
        estado_id = None
        for k, v in ESTADO_MAP.items():
            if v.lower() == estado:
                estado_id = k
                break
        if estado_id:
            consultas = consultas.filter(cita__estado_cita_id=estado_id)

    consultas = consultas.distinct()

    data = []
    for cons in consultas:
        cita = cons.cita
        ident = cita.paciente.persona.identificaciones.first()
        cedula = f"{ident.dsc} {ident.valor}" if ident else ''
        data.append({
            'id': cons.id,
            'paciente': f"{cita.paciente.persona.nombre} {cita.paciente.persona.apellido}",
            'cedula': cedula,
            'medico': f"{cita.medico.persona.nombre} {cita.medico.persona.apellido}",
            'fecha_atencion': cita.fecha_atencion.strftime('%Y-%m-%d'),
            'tipo_consulta': cons.tipo_consulta,
            'estado': ESTADO_MAP.get(cita.estado_cita_id, 'Desconocido'),
        })
    return JsonResponse(data, safe=False)


@login_required
def atender_cita(request, cita_id):
    from apps.citas.models import Cita
    from apps.diagnostico.models import Consulta, Diagnostico, Enfermedad, Sintomas
    from apps.mediciones.models import MedicionesCabecera, MedicionesDetalles, EquipoParametros, Parametros
    from apps.antecedentes.models import AntecedenteCategoria, AntecedentesSalud
    from apps.identificacion.models import Persona

    cita = Cita.objects.select_related('paciente__persona__nombre','paciente__persona__apellido','medico__persona__nombre','medico__persona__apellido').get(pk=cita_id)
    # Obtener o crear consulta
    consulta, _ = Consulta.objects.get_or_create(cita=cita, defaults={'tipo_consulta':1})
    diagnostico, _ = Diagnostico.objects.get_or_create(consulta=consulta)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'medicion':
            # Múltiples mediciones en un solo envío
            eps = request.POST.getlist('equipo_parametro')
            valores = request.POST.getlist('valor')
            pares = [(e, v.strip()) for e, v in zip(eps, valores) if e and v.strip()]
            if pares:
                cab, _ = MedicionesCabecera.objects.get_or_create(
                    paciente=cita.paciente, defaults={})
                eps_existentes = EquipoParametros.objects.filter(
                    pk__in=[e for e, _ in pares]).in_bulk()
                for ep_id, valor in pares:
                    ep = eps_existentes.get(int(ep_id))
                    if ep:
                        MedicionesDetalles.objects.create(
                            medicion=cab, equipo_parametro=ep,
                            valor_arrojado=valor)
        elif action == 'antecedente':
            # Múltiples antecedentes en un solo envío
            cats = request.POST.getlist('categoria')
            descs = request.POST.getlist('descripcion')
            for cat_id, descripcion in zip(cats, descs):
                descripcion = (descripcion or '').strip()
                if cat_id and descripcion:
                    AntecedentesSalud.objects.create(
                        paciente=cita.paciente,
                        antecedente_salud_id_id=cat_id,
                        descrip='Antecedente', valor=descripcion)
        elif action == 'diagnostico':
            # Guardar enfermedad y síntomas
            enfermedad = request.POST.get('enfermedad','')
            categoria = request.POST.get('enfermedad_categoria','')
            if enfermedad:
                Enfermedad.objects.create(diagnostico=diagnostico, valor=enfermedad, dsc=categoria)
            # Síntomas múltiples
            sintomas_list = request.POST.getlist('sintomas')
            for s in sintomas_list:
                s = s.strip()
                if s:
                    Sintomas.objects.create(diagnostico=diagnostico, sintoma=s)
            # Marcar cita atendida
            cita.estado_cita_id = 2
            cita.save()
            return redirect('citas:lista_citas')

    # Datos para render
    # Solo categorías hoja (con padre) seleccionables para antecedentes
    categorias = (AntecedenteCategoria.objects
                  .filter(dep_id__isnull=False)
                  .select_related('dep_id'))
    ant_qs = (AntecedentesSalud.objects.filter(paciente=cita.paciente)
              .select_related('antecedente_salud_id__dep_id'))
    antecedentes_salud = []
    antecedentes_familiares = []
    for a in ant_qs:
        cat = a.antecedente_salud_id
        raiz = cat.dep_id if cat.dep_id_id else cat
        if raiz and raiz.dsc == 'Antecedentes Familiares':
            antecedentes_familiares.append(a)
        else:
            antecedentes_salud.append(a)
    mediciones = MedicionesCabecera.objects.filter(paciente=cita.paciente).order_by('-fecha_toma')[:5]
    enfermedades = Enfermedad.objects.filter(diagnostico=diagnostico)
    sintomas = Sintomas.objects.filter(diagnostico=diagnostico)
    equipo_parametros = EquipoParametros.objects.select_related('parametro','equipo').all()
    from apps.diagnostico.models import EnfermedadCatalogo
    catalogo = EnfermedadCatalogo.objects.all()

    contexto = {
        'cita': cita,
        'consulta': consulta,
        'diagnostico': diagnostico,
        'categorias': categorias,
        'antecedentes_salud': antecedentes_salud,
        'antecedentes_familiares': antecedentes_familiares,
        'mediciones': mediciones,
        'enfermedades': enfermedades,
        'sintomas': sintomas,
        'equipo_parametros': equipo_parametros,
        'catalogo': catalogo,
    }
    return render(request, 'diagnostico/atender_cita.html', contexto)

@login_required
@permiso_requerido('diagnostico.editar')
def gestion_catalogo_enfermedades(request):
    from apps.diagnostico.models import EnfermedadCatalogo
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'crear':
            EnfermedadCatalogo.objects.create(
                dsc=request.POST.get('dsc'),
                depid_id=request.POST.get('depid') or None,
                tipo=request.POST.get('tipo') or None
            )
        return redirect('diagnostico:gestion_catalogo_enfermedades')
    catalogo = EnfermedadCatalogo.objects.all()
    return render(request, 'diagnostico/gestion_catalogo_enfermedades.html', {'catalogo': catalogo})

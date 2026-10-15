from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.citas.models import Cita
from apps.usuarios.permissions import permiso_requerido

ESTADO_MAP = {
    1: 'En espera',
    2: 'Atendido',
    3: 'Cancelada',
}

@login_required
@permiso_requerido('citas.ver')
def lista_citas(request):
    citas = Cita.objects.all().select_related('paciente__persona__nombre', 'paciente__persona__apellido', 'medico__persona__nombre', 'medico__persona__apellido')
    return render(request, 'citas/lista_citas.html', {'citas': citas})

@login_required
@permiso_requerido('citas.ver')
def api_buscar_citas(request):
    q = request.GET.get('q', '').strip()
    fecha = request.GET.get('fecha', '').strip()
    estado = request.GET.get('estado', '').strip().lower()

    citas = Cita.objects.select_related(
        'paciente__persona__nombre',
        'paciente__persona__apellido',
        'medico__persona__nombre',
        'medico__persona__apellido'
    )

    # Buscar por cédula del paciente
    if q:
        citas = citas.filter(
            Q(paciente__persona__identificaciones__valor__icontains=q)
        )

    if fecha:
        citas = citas.filter(fecha_atencion=fecha)

    if estado:
        # mapear texto a id
        estado_id = None
        for k,v in ESTADO_MAP.items():
            if v.lower() == estado:
                estado_id = k
                break
        if estado_id:
            citas = citas.filter(estado_cita_id=estado_id)

    citas = citas.distinct()

    data = []
    for c in citas:
        # obtener cédula del paciente
        ident = c.paciente.persona.identificaciones.first()
        cedula = f"{ident.dsc} {ident.valor}" if ident else ''
        data.append({
            'id': c.id,
            'paciente': f"{c.paciente.persona.nombre} {c.paciente.persona.apellido}",
            'cedula': cedula,
            'medico': f"{c.medico.persona.nombre} {c.medico.persona.apellido}",
            'fecha_atencion': c.fecha_atencion.strftime('%Y-%m-%d'),
            'estado': ESTADO_MAP.get(c.estado_cita_id, 'Desconocido'),
            'tipo': c.tipo_cita or '',
        })
    return JsonResponse(data, safe=False)

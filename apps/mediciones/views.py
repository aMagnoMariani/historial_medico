from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.usuarios.permissions import permiso_requerido, valida_accion
from .models import Equipos, Parametros, EquipoParametros

@login_required
@permiso_requerido('config-mediciones.ver')
def gestion_config_mediciones(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        rechazo = valida_accion(request, action, 'config-mediciones')
        if rechazo:
            return rechazo
        if action == 'crear_equipo':
            Equipos.objects.create(
                nombre=request.POST.get('nombre'),
                tipo_tecnologia=request.POST.get('tipo_tecnologia',''),
                marca=request.POST.get('marca',''),
                modelo=request.POST.get('modelo','')
            )
        elif action == 'crear_parametro':
            Parametros.objects.create(
                dsc=request.POST.get('dsc'),
                unidad=request.POST.get('unidad','')
            )
        elif action == 'crear_relacion':
            EquipoParametros.objects.create(
                equipo_id=request.POST.get('equipo_id'),
                parametro_id=request.POST.get('parametro_id')
            )
        return redirect('mediciones:gestion_config_mediciones')
    
    equipos = Equipos.objects.all()
    parametros = Parametros.objects.all()
    relaciones = EquipoParametros.objects.select_related('equipo','parametro').all()
    return render(request, 'mediciones/gestion_config_mediciones.html', {
        'equipos': equipos,
        'parametros': parametros,
        'relaciones': relaciones,
    })

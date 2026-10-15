"""Consultas estadísticas del sistema (citas, diagnósticos, mediciones)."""
import datetime
from collections import Counter

from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth

from apps.citas.models import Cita
from apps.diagnostico.models import Enfermedad, Sintomas
from apps.identificacion.models import Especialidad, Paciente, Persona, Sexo
from apps.mediciones.models import MedicionesDetalles


def citas_por_mes():
    return (Cita.objects
            .annotate(mes=TruncMonth('fecha_atencion'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes'))


ESTADO_CITA = {1: 'En espera', 2: 'Atendido', 3: 'Cancelada'}


def citas_por_estado():
    datos = (Cita.objects
             .values('estado_cita_id')
             .annotate(total=Count('id'))
             .order_by('-total'))
    return [{'estado': ESTADO_CITA.get(r['estado_cita_id'], 'Desconocido'),
             'total': r['total']} for r in datos]


def citas_por_especialidad():
    return (Cita.objects
            .values('medico__especialidad__descripcion')
            .annotate(total=Count('id'))
            .order_by('-total'))


def enfermedades_frecuentes(limite=10):
    return (Enfermedad.objects
            .values('valor')
            .annotate(total=Count('id'))
            .order_by('-total')[:limite])


def sintomas_frecuentes(limite=10):
    return (Sintomas.objects
            .values('sintoma')
            .annotate(total=Count('id'))
            .order_by('-total')[:limite])


def promedio_mediciones_por_parametro():
    return (MedicionesDetalles.objects
            .values('equipo_parametro__parametro__dsc',
                    'equipo_parametro__parametro__unidad')
            .annotate(promedio=Avg('valor_arrojado'))
            .order_by('equipo_parametro__parametro__dsc'))


def pacientes_atendidos_por_mes():
    return (MedicionesDetalles.objects
            .annotate(mes=TruncMonth('medicion__fecha_toma'))
            .values('mes')
            .annotate(pacientes=Count('medicion__paciente', distinct=True))
            .order_by('mes'))


def resumen_general():
    return {
        'total_citas': Cita.objects.count(),
        'total_pacientes': Paciente.objects.count(),
        'total_especialidades_activas': Especialidad.objects.filter(
            estado=True).count(),
        'total_diagnosticos': Enfermedad.objects.values(
            'diagnostico').distinct().count(),
        'total_mediciones': MedicionesDetalles.objects.count(),
    }


def pacientes_por_sexo():
    """Pacientes agrupados por sexo (etiqueta legible)."""
    etiquetas = dict(Sexo.choices)
    datos = (Paciente.objects
             .values('persona__sexo')
             .annotate(total=Count('id'))
             .order_by('-total'))
    return [{
        'sexo': etiquetas.get(r['persona__sexo'], 'No especificado'),
        'total': r['total'],
    } for r in datos]


def pacientes_por_edad():
    """Pacientes por rango de edad según fecha de nacimiento."""
    hoy = datetime.date.today()
    rangos = [(0, 12), (13, 17), (18, 29), (30, 59), (60, 200)]
    conteo = {f'{a}-{b}' if b < 200 else f'{a}+': 0 for a, b in rangos}
    for fn in (Paciente.objects
               .filter(persona__fecha_nacimiento__isnull=False)
               .values_list('persona__fecha_nacimiento', flat=True)):
        edad = (hoy - fn).days // 365
        for a, b in rangos:
            if a <= edad <= b:
                clave = f'{a}-{b}' if b < 200 else f'{a}+'
                conteo[clave] += 1
                break
    return [{'rango': k, 'total': v} for k, v in conteo.items()]


def pacientes_por_etnia():
    return (Paciente.objects
            .values('persona__etnia__tipo_etnia')
            .annotate(total=Count('id'))
            .order_by('-total'))


def pacientes_por_ubicacion():
    """Pacientes por Estado (raíz de la jerarquía de direcciones)."""
    from apps.identificacion.models import Direccion
    nodos = {d.id: d for d in Direccion.objects.all()}

    def raiz(dir_id):
        d = nodos.get(dir_id)
        while d and d.depid_id and d.depid_id in nodos:
            d = nodos[d.depid_id]
        return d

    conteo = Counter()
    for dir_id in (Paciente.objects
                   .filter(persona__direccion__isnull=False)
                   .values_list('persona__direccion_id', flat=True)):
        r = raiz(dir_id)
        conteo[r.dsc if r else 'No especificado'] += 1
    return [{'ubicacion': k, 'total': v}
            for k, v in conteo.most_common()]


def enfermedades_por_categoria():
    """Diagnósticos agrupados por categoría de la enfermedad."""
    return (Enfermedad.objects
            .values('dsc')
            .annotate(total=Count('id'))
            .order_by('-total'))


def pacientes_por_sintoma(limite=10):
    """Cuántos pacientes distintos presentaron cada síntoma (ej: tos)."""
    return (Sintomas.objects
            .values('sintoma')
            .annotate(pacientes=Count(
                'diagnostico__consulta__cita__paciente', distinct=True))
            .order_by('-pacientes')[:limite])


def antecedentes_frecuentes(limite=10):
    """Antecedentes más reportados por categoría."""
    from apps.antecedentes.models import AntecedentesSalud
    return (AntecedentesSalud.objects
            .values('antecedente_salud_id__dsc')
            .annotate(total=Count('id'))
            .order_by('-total')[:limite])


def especialidades_atendidas():
    """Especialidades con más consultas atendidas."""
    return (Cita.objects.filter(estado_cita_id=2)
            .values('medico__especialidad__descripcion')
            .annotate(atendidas=Count('id'))
            .order_by('-atendidas'))


DIA_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves',
              'Viernes', 'Sábado', 'Domingo']


def _calcular_edad(fecha_nacimiento):
    hoy = datetime.date.today()
    return (hoy - fecha_nacimiento).days // 365 if fecha_nacimiento else None


def _raiz_direccion(dir_id, nodos):
    d = nodos.get(dir_id)
    while d and d.depid_id and d.depid_id in nodos:
        d = nodos[d.depid_id]
    return d


def pacientes_exportables():
    """Datos completos de cada paciente para exportar."""
    from apps.identificacion.models import Direccion
    nodos = {d.id: d for d in Direccion.objects.all()}
    filas = []
    for p in (Paciente.objects
              .select_related('persona__nombre', 'persona__apellido',
                              'persona__etnia', 'persona__sangre',
                              'persona__direccion')):
        per = p.persona
        ident = per.identificaciones.first()
        raiz = _raiz_direccion(per.direccion_id, nodos) if per.direccion_id else None
        filas.append({
            'id': p.id,
            'nombre': f'{per.nombre} {per.apellido}',
            'cedula': f'{ident.dsc} {ident.valor}' if ident else '',
            'sexo': per.get_sexo_display() or '',
            'edad': _calcular_edad(per.fecha_nacimiento),
            'fecha_nacimiento': per.fecha_nacimiento,
            'etnia': per.etnia.tipo_etnia if per.etnia else '',
            'sangre': per.sangre.tipo_sangre if per.sangre else '',
            'ubicacion': raiz.dsc if raiz else '',
            'telefono': per.telefono or '',
        })
    return filas


def visitas_exportables(desde=None, hasta=None):
    """Cada visita al consultorio con diagnóstico, para exportar/filtrar.

    Incluye el día de la semana para responder: cuántos llegaron el lunes,
    en abril, quiénes fueron, qué se les hizo y sus características.
    """
    from apps.diagnostico.models import Consulta, Diagnostico, Enfermedad, Sintomas
    qs = (Cita.objects
          .select_related('paciente__persona__nombre', 'paciente__persona__apellido',
                          'medico__persona__nombre', 'medico__persona__apellido',
                          'medico__especialidad')
          .order_by('fecha_atencion'))
    if desde:
        qs = qs.filter(fecha_atencion__gte=desde)
    if hasta:
        qs = qs.filter(fecha_atencion__lte=hasta)

    filas = []
    for cita in qs:
        enfermedades, sintomas = [], []
        consulta = Consulta.objects.filter(cita=cita).first()
        if consulta:
            diag = Diagnostico.objects.filter(consulta=consulta).first()
            if diag:
                enfermedades = [e.valor for e in
                                Enfermedad.objects.filter(diagnostico=diag)
                                if e.valor]
                sintomas = [s.sintoma for s in
                            Sintomas.objects.filter(diagnostico=diag)]
        per = cita.paciente.persona
        filas.append({
            'fecha': cita.fecha_atencion,
            'dia_semana': DIA_SEMANA[cita.fecha_atencion.weekday()],
            'paciente': f'{per.nombre} {per.apellido}',
            'sexo': per.get_sexo_display() or '',
            'edad': _calcular_edad(per.fecha_nacimiento),
            'medico': (f'{cita.medico.persona.nombre} '
                       f'{cita.medico.persona.apellido}'),
            'especialidad': cita.medico.especialidad.descripcion,
            'tipo': cita.get_tipo_cita_display() or '-',
            'estado': ESTADO_CITA.get(cita.estado_cita_id, 'Desconocido'),
            'enfermedades': ', '.join(enfermedades) or '-',
            'sintomas': ', '.join(sintomas) or '-',
        })
    return filas

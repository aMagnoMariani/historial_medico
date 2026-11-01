"""Consultas estadísticas y reportes del sistema.

Reglas importantes:
  - La EDAD de un paciente se calcula a la FECHA DE ATENCIÓN de la cita,
    no a la fecha de hoy. Así, si a alguien se le diagnosticó cáncer de
    próstata a los 55 años, ese registro aparece con 55 aunque hoy tenga 60.
  - La sección "por ubicación" arranca en Monagas y permite bajar por la
    jerarquía: Municipio -> Parroquia -> Sector/Calle.
"""
import datetime
from collections import Counter, OrderedDict

from django.db.models import Count

from apps.citas.models import Cita
from apps.diagnostico.models import Enfermedad, Sintomas
from apps.identificacion.models import (Especialidad, Paciente, Persona,
                                        Sexo, Direccion)

ESTADO_CITA = {1: 'En espera', 2: 'Atendido', 3: 'Cancelada'}

DIA_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves',
              'Viernes', 'Sábado', 'Domingo']

# ---------------------------------------------------------------------
#  RANGOS DE EDAD
# ---------------------------------------------------------------------
# (etiqueta, años mínimos, años máximos inclusive)
RANGOS_EDAD = [
    ('0-11 meses', 0, 0),
    ('1-3 años', 1, 3),
    ('4-6 años', 4, 6),
    ('7-9 años', 7, 9),
    ('10-12 años', 10, 12),
    ('13-17 años', 13, 17),
    ('18-25 años', 18, 25),
    ('26-35 años', 26, 35),
    ('36-59 años', 36, 59),
    ('60 años o más', 60, 200),
]

SEXOS = [('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')]

# Raíz de la sección de ubicación
ESTADO_RAIZ = 'Monagas'

# Fecha de la cita interna del sistema (no se cuenta en las estadísticas)
FECHA_COMODIN = '1900-01-01'


def edad_en_fecha(fecha_nacimiento, fecha_referencia):
    """Edad cumplida (en años) a la fecha de referencia.

    Devuelve None si no hay fecha de nacimiento.
    """
    if not fecha_nacimiento or not fecha_referencia:
        return None
    if isinstance(fecha_referencia, datetime.datetime):
        fecha_referencia = fecha_referencia.date()
    if isinstance(fecha_nacimiento, datetime.datetime):
        fecha_nacimiento = fecha_nacimiento.date()
    if fecha_referencia < fecha_nacimiento:
        return 0
    años = fecha_referencia.year - fecha_nacimiento.year
    # aún no cumplió este año
    if (fecha_referencia.month, fecha_referencia.day) < \
            (fecha_nacimiento.month, fecha_nacimiento.day):
        años -= 1
    return años


def _rango_de_edad(edad):
    """Etiqueta del rango al que pertenece una edad en años."""
    if edad is None:
        return 'Sin fecha de nacimiento'
    # 0-11 meses: menores de 1 año
    if edad == 0:
        return '0-11 meses'
    for etiqueta, minimo, maximo in RANGOS_EDAD[1:]:
        if minimo <= edad <= maximo:
            return etiqueta
    return '60 años o más'


def _etiqueta_sexo(codigo):
    return dict(SEXOS).get(codigo, codigo or 'Sin sexo')


# =====================================================================
#  CITAS
# =====================================================================
def citas_por_mes():
    from django.db.models.functions import TruncMonth
    return (Cita.objects
            .annotate(mes=TruncMonth('fecha_atencion'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes'))


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


def especialidades_atendidas():
    return (Cita.objects.filter(estado_cita_id=2)
            .values('medico__especialidad__descripcion')
            .annotate(atendidas=Count('id'))
            .order_by('-atendidas'))


# =====================================================================
#  DIAGNÓSTICOS
# =====================================================================
def enfermedades_frecuentes(limite=10):
    contador = Counter()
    for desc in Enfermedad.objects.values_list('desc', flat=True):
        for nombre in (desc or []):
            contador[nombre] += 1
    return [{'desc': nombre, 'total': total}
            for nombre, total in contador.most_common(limite)]


def sintomas_frecuentes(limite=10):
    return (Sintomas.objects
            .values('desc')
            .annotate(total=Count('id'))
            .order_by('-total')[:limite])


def pacientes_por_sintoma(limite=10):
    return (Sintomas.objects
            .values('desc')
            .annotate(pacientes=Count(
                'diagnostico__consulta__cita__paciente', distinct=True))
            .order_by('-pacientes')[:limite])


def antecedentes_frecuentes(limite=10):
    from apps.antecedentes.models import AntecedentesSalud
    return (AntecedentesSalud.objects
            .values('descrip')
            .annotate(total=Count('id'))
            .order_by('-total')[:limite])


# =====================================================================
#  DEMOGRAFÍA: EDAD x SEXO x ESPECIALIDAD
# =====================================================================
def _visitas_filtradas(desde=None, hasta=None, solo_atendidas=True):
    """Visitas (citas) con sus datos ya resueltos, filtradas por fecha.

    La cita interna del sistema (fecha 1900-01-01) se excluye siempre:
    solo existe para alojar las filas del catálogo.
    """
    qs = (Cita.objects
          .exclude(fecha_atencion=FECHA_COMODIN)
          .select_related('paciente__persona__nombre',
                          'paciente__persona__apellido',
                          'medico__especialidad'))
    if solo_atendidas:
        qs = qs.filter(estado_cita_id=2)
    if desde:
        qs = qs.filter(fecha_atencion__gte=desde)
    if hasta:
        qs = qs.filter(fecha_atencion__lte=hasta)
    return qs.order_by('fecha_atencion', 'id')


def visitas_demograficas(desde=None, hasta=None):
    """Lista de visitas atendidas con edad (a la fecha de atención),
    sexo y especialidad. Es la base de los conteos por edad."""
    filas = []
    for cita in _visitas_filtradas(desde, hasta):
        per = cita.paciente.persona
        edad = edad_en_fecha(per.fecha_nacimiento, cita.fecha_atencion)
        filas.append({
            'cita_id': cita.id,
            'paciente_id': cita.paciente_id,
            'nombre': f'{per.nombre} {per.apellido}',
            'sexo': per.sexo,
            'sexo_etiqueta': _etiqueta_sexo(per.sexo),
            'fecha_nacimiento': per.fecha_nacimiento,
            'fecha_atencion': cita.fecha_atencion,
            'edad': edad,
            'rango': _rango_de_edad(edad),
            'especialidad': cita.medico.especialidad.descripcion,
        })
    return filas


def edad_por_sexo(desde=None, hasta=None):
    """Tabla rango de edad x sexo.

    Devuelve filas con {'rango', 'M', 'F', 'O', 'total'}.
    """
    rangos = [etiqueta for etiqueta, _, _ in RANGOS_EDAD]
    rangos.append('Sin fecha de nacimiento')
    tabla = OrderedDict((r, {'rango': r, 'M': 0, 'F': 0, 'O': 0, 'total': 0})
                        for r in rangos)

    for v in visitas_demograficas(desde, hasta):
        fila = tabla[v['rango']]
        codigo = v['sexo'] if v['sexo'] in ('M', 'F', 'O') else 'O'
        fila[codigo] += 1
        fila['total'] += 1

    return list(tabla.values())


def edad_por_sexo_totales(desde=None, hasta=None):
    """Totales generales por sexo sobre las mismas visitas."""
    totales = {'M': 0, 'F': 0, 'O': 0, 'total': 0}
    for v in visitas_demograficas(desde, hasta):
        codigo = v['sexo'] if v['sexo'] in ('M', 'F', 'O') else 'O'
        totales[codigo] += 1
        totales['total'] += 1
    return totales


def edad_por_especialidad(desde=None, hasta=None):
    """Tabla rango de edad x especialidad.

    Devuelve una estructura lista para la plantilla:
        {
          'especialidades': [...],          # cabeceras
          'filas': [{'rango', 'valores', 'total'}],
          'totales': [...]                  # última fila
        }
    """
    visitas = visitas_demograficas(desde, hasta)

    especialidades = sorted({v['especialidad'] for v in visitas})
    rangos = [etiqueta for etiqueta, _, _ in RANGOS_EDAD]

    # conteo[rango][especialidad]
    conteo = OrderedDict((r, OrderedDict((e, 0) for e in especialidades))
                         for r in rangos)
    for v in visitas:
        conteo[v['rango']][v['especialidad']] += 1

    filas = []
    for r in rangos:
        valores = [conteo[r][e] for e in especialidades]
        filas.append({'rango': r, 'valores': valores, 'total': sum(valores)})

    totales = [sum(conteo[r][e] for r in rangos) for e in especialidades]
    totales.append(sum(totales))

    return {
        'especialidades': especialidades,
        'filas': filas,
        'totales': totales,
        'total_general': totales[-1],
    }


def especialidades_mas_atendidas(desde=None, hasta=None, limite=10):
    contador = Counter()
    for v in visitas_demograficas(desde, hasta):
        contador[v['especialidad']] += 1
    return [{'especialidad': e, 'total': t}
            for e, t in contador.most_common(limite)]


def especialidad_edad_sexo(desde=None, hasta=None):
    """Tabla del ejemplo: especialidad x rango de edad, con M y F por rango.

    Estructura de doble cabecera:

        especialidad    | 0-11 meses | 1-3 años | ... | 60 años o más | Totales
                        |  m     f   |  m   f   |     |     m    f     | m  f  tot
        Medicina interna|  0     2   |  0   2   |     |     0    2     | .  .   .

    Devuelve:
        {
          'rangos': [...],                 # etiquetas de rango
          'filas': [{
              'especialidad': str,
              'celdas': [{'M':n,'F':n}, ...],  # una por rango
              'total_M': n, 'total_F': n, 'total': n
          }],
          'totales': [{'M':n,'F':n}, ...], # una por rango
          'totales_generales': {'M':n,'F':n,'total':n}
        }
    """
    visitas = visitas_demograficas(desde, hasta)

    especialidades = sorted({v['especialidad'] for v in visitas})
    rangos = [etiqueta for etiqueta, _, _ in RANGOS_EDAD]

    def celda_vacia():
        return {'M': 0, 'F': 0, 'O': 0}

    # conteo[especialidad][rango] = {'M':n,'F':n}
    conteo = {e: OrderedDict((r, celda_vacia()) for r in rangos)
              for e in especialidades}
    gran_total = OrderedDict((r, celda_vacia()) for r in rangos)

    for v in visitas:
        codigo = v['sexo'] if v['sexo'] in ('M', 'F') else 'O'
        # "Otro" se suma aparte para no perder el dato
        conteo[v['especialidad']][v['rango']][codigo] += 1
        gran_total[v['rango']][codigo] += 1

    filas = []
    for e in especialidades:
        celdas = [conteo[e][r] for r in rangos]
        tot_m = sum(c['M'] for c in celdas)
        tot_f = sum(c['F'] for c in celdas)
        tot_o = sum(c['O'] for c in celdas)
        filas.append({
            'especialidad': e,
            'celdas': celdas,
            'total_M': tot_m,
            'total_F': tot_f,
            'total_O': tot_o,
            'total': tot_m + tot_f + tot_o,
        })

    filas.sort(key=lambda f: (-f['total'], f['especialidad']))

    gm = sum(gran_total[r]['M'] for r in rangos)
    gf = sum(gran_total[r]['F'] for r in rangos)
    go = sum(gran_total[r]['O'] for r in rangos)

    return {
        'rangos': rangos,
        'filas': filas,
        'totales': [gran_total[r] for r in rangos],
        'totales_generales': {'M': gm, 'F': gf, 'O': go,
                              'total': gm + gf + go},
    }


# =====================================================================
#  PACIENTES
# =====================================================================
def pacientes_por_sexo():
    etiquetas = dict(Sexo.choices)
    datos = (Paciente.objects
             .values('persona__sexo')
             .annotate(total=Count('id'))
             .order_by('-total'))
    return [{'sexo': etiquetas.get(r['persona__sexo'], 'No especificado'),
             'total': r['total']} for r in datos]


def pacientes_por_etnia():
    return (Paciente.objects
            .values('persona__etnia__tipo_etnia')
            .annotate(total=Count('id'))
            .order_by('-total'))


def pacientes_atendidos_por_mes():
    from django.db.models.functions import TruncMonth
    return (Cita.objects.filter(estado_cita_id=2)
            .annotate(mes=TruncMonth('fecha_atencion'))
            .values('mes')
            .annotate(pacientes=Count('paciente', distinct=True))
            .order_by('mes'))


def resumen_general(desde=None, hasta=None):
    citas = Cita.objects.all()
    if desde:
        citas = citas.filter(fecha_atencion__gte=desde)
    if hasta:
        citas = citas.filter(fecha_atencion__lte=hasta)
    return {
        'total_citas': citas.count(),
        'total_pacientes': Paciente.objects.count(),
        'total_especialidades_activas': Especialidad.objects.filter(
            estado=True).count(),
        'total_diagnosticos': Enfermedad.objects.values(
            'diagnostico').distinct().count(),
        'atendidas': citas.filter(estado_cita_id=2).count(),
    }


# =====================================================================
#  UBICACIÓN JERÁRQUICA (Monagas -> Municipio -> Parroquia -> Sector)
# =====================================================================
def mapa_direcciones():
    """{id: nodo} con todas las direcciones."""
    return {d.id: d for d in Direccion.objects.all()}


def estado_raiz():
    """Nodo raíz de la sección (Monagas). Si no existe, cualquiera.

    La búsqueda es tolerante: en los datos reales el campo
    division_politica no siempre dice 'Estado' (a veces trae el nombre
    del municipio), por eso se busca primero por el VALOR.
    """
    nodos = mapa_direcciones()

    # 1. Un nodo sin padre cuyo valor sea el estado buscado
    for d in nodos.values():
        if not d.divicion_politica_id and \
                (d.valor or '').strip().lower() == ESTADO_RAIZ.lower():
            return d

    # 2. Cualquier nodo cuyo valor contenga el estado (aunque tenga padre)
    for d in nodos.values():
        if ESTADO_RAIZ.lower() in (d.valor or '').strip().lower():
            return d

    # 3. Cualquier nodo marcado como Estado en division_politica
    for d in nodos.values():
        if d.division_politica == 'Estado' and not d.divicion_politica_id:
            return d

    # 4. Cualquier nodo sin padre
    for d in sorted(nodos.values(), key=lambda x: x.id):
        if not d.divicion_politica_id:
            return d
    return None


def _descendientes(nodo_id, nodos):
    """Todos los ids debajo de un nodo (incluido él)."""
    vistos, pila = set(), [nodo_id]
    while pila:
        actual = pila.pop()
        if actual in vistos or actual not in nodos:
            continue
        vistos.add(actual)
        for d in nodos.values():
            if d.divicion_politica_id == actual and d.id not in vistos:
                pila.append(d.id)
    return vistos


def ruta_direccion(direccion_id, nodos=None):
    """Cadena legible de la dirección: Sector › Parroquia › Municipio › Estado."""
    nodos = nodos or mapa_direcciones()
    partes, d = [], nodos.get(direccion_id)
    while d:
        if d.valor:
            partes.append(d.valor)
        d = nodos.get(d.divicion_politica_id) if d.divicion_politica_id else None
    return ' › '.join(reversed(partes)) or ''


def ubicacion_nivel(padre_id=None):
    """Hijos de un nodo de dirección, con el conteo de pacientes.

    - padre_id None -> los municipios del estado raíz (Monagas)
    - padre_id con valor -> los hijos de ese nodo (parroquias, sectores...)

    Devuelve contexto listo para la plantilla.
    """
    nodos = mapa_direcciones()
    raiz = estado_raiz()
    if raiz is None:
        return {'nivel': 1, 'padre': None, 'items': [], 'migas': []}

    objetivo = nodos.get(padre_id) if padre_id else raiz

    # Protección: solo se navega DENTRO del estado raíz.
    # El nodo pedido debe colgar de la raíz (o ser la raíz misma).
    subarbol_raiz = _descendientes(raiz.id, nodos)
    if objetivo and objetivo.id != raiz.id and objetivo.id not in subarbol_raiz:
        objetivo = raiz

    # Contar pacientes cuya dirección cuelgue de este nodo
    subarbol = _descendientes(objetivo.id, nodos)
    conteo = Counter(
        Paciente.objects
        .filter(persona__direccion_id__in=subarbol)
        .values_list('persona__direccion_id', flat=True))

    # Pacientes cuya dirección es exactamente este nodo
    directos = conteo.get(objetivo.id, 0)

    # Hijos con su propio subtotal
    hijos = [d for d in nodos.values() if d.divicion_politica_id == objetivo.id]
    items = []
    for h in sorted(hijos, key=lambda x: x.valor or ''):
        sub = _descendientes(h.id, nodos)
        total_hijo = sum(conteo.get(i, 0) for i in sub)
        items.append({
            'id': h.id,
            'nombre': h.valor,
            'nivel': h.division_politica,
            'total': total_hijo,
            'tiene_hijos': any(n.divicion_politica_id == h.id for n in nodos.values()),
        })

    # Migas de pan: raíz -> ... -> nodo actual
    migas, d = [], objetivo
    while d:
        migas.append({'id': d.id, 'nombre': d.valor, 'nivel': d.division_politica})
        d = nodos.get(d.divicion_politica_id) if d.divicion_politica_id else None
    migas.reverse()

    # Nivel dentro de la jerarquía (1=municipio, 2=parroquia, 3=sector)
    nivel = len(migas) - 1
    # El nodo final no tiene hijos propios: mostrar los pacientes
    pacientes = []
    if not items:
        pacientes = (Paciente.objects
                     .filter(persona__direccion_id=objetivo.id)
                     .select_related('persona__nombre', 'persona__apellido')
                     .order_by('persona__nombre__descripcion'))

    return {
        'nivel': nivel,
        'padre': objetivo,
        'padre_nombre': objetivo.valor,
        'padre_nivel': objetivo.division_politica,
        'items': items,
        'directos': directos,
        'total': sum(i['total'] for i in items) + directos,
        'migas': migas,
        'es_raiz': objetivo.id == raiz.id,
        'pacientes': pacientes,
        'estado': raiz.valor,
    }


# =====================================================================
#  REPORTE HISTÓRICO
# =====================================================================
def reporte_historico(desde=None, hasta=None, buscar=None):
    """Reporte detallado: una fila por visita atendida.

    Columnas: fecha, nombre, apellido, edad (a la fecha de atención),
    sexo, cédula, dirección exacta, teléfono, fecha de nacimiento,
    diagnóstico y conducta.

    Sirve para responder cosas como: "¿a quién se le diagnosticó cáncer de
    próstata a los 55 años?" filtrando por enfermedad y rango de fechas.
    """
    from apps.diagnostico.models import Consulta, Diagnostico

    nodos = mapa_direcciones()
    filas = []

    qs = (Cita.objects
          .filter(estado_cita_id=2)
          .exclude(fecha_atencion=FECHA_COMODIN)
          .select_related('paciente__persona__nombre',
                          'paciente__persona__apellido',
                          'medico__persona__nombre',
                          'medico__persona__apellido',
                          'medico__especialidad')
          .order_by('fecha_atencion', 'id'))
    if desde:
        qs = qs.filter(fecha_atencion__gte=desde)
    if hasta:
        qs = qs.filter(fecha_atencion__lte=hasta)
    if buscar:
        from django.db.models import Q
        qs = qs.filter(
            Q(paciente__persona__nombre__descripcion__icontains=buscar) |
            Q(paciente__persona__apellido__descripcion__icontains=buscar) |
            Q(paciente__persona__identificaciones__valor__icontains=buscar))

    consultas = {c.cita_id: c for c in Consulta.objects.all()}
    diagnosticos = {d.consulta_id: d for d in Diagnostico.objects.all()}

    # Enfermedades y síntomas por diagnóstico
    enf_por_diag, sin_por_diag = {}, {}
    for e in Enfermedad.objects.all():
        enf_por_diag.setdefault(e.diagnostico_id, []).append(e)
    for s in Sintomas.objects.all():
        sin_por_diag.setdefault(s.diagnostico_id, []).append(s)

    for cita in qs:
        per = cita.paciente.persona
        ident = per.identificaciones.first()

        consulta = consultas.get(cita.id)
        diag = diagnosticos.get(consulta.id) if consulta else None

        enfermedades, sintomas, conducta = [], [], ''
        if diag:
            for e in enf_por_diag.get(diag.id, []):
                if e.desc:
                    enfermedades.append(', '.join(e.desc))
                elif e.valor:
                    enfermedades.append(e.valor)
            sintomas = [s.desc for s in sin_por_diag.get(diag.id, [])]
            # conducta_id puede estar vacío en registros antiguos
            try:
                conducta_obj = diag.conducta
            except Exception:
                conducta_obj = None
            if conducta_obj:
                conducta = ', '.join(conducta_obj.conducta or [])
                if conducta_obj.descripcion:
                    conducta += f' ({conducta_obj.descripcion})'

        edad = edad_en_fecha(per.fecha_nacimiento, cita.fecha_atencion)

        filas.append({
            'cita_id': cita.id,
            'fecha': cita.fecha_atencion,
            'dia_semana': DIA_SEMANA[cita.fecha_atencion.weekday()],
            'nombre': per.nombre.descripcion if per.nombre else '',
            'apellido': per.apellido.descripcion if per.apellido else '',
            'edad': edad,
            'rango': _rango_de_edad(edad),
            'sexo': _etiqueta_sexo(per.sexo),
            'cedula': f"{ident.descripcion}: {ident.valor}" if ident else '',
            'direccion': ruta_direccion(per.direccion_id, nodos),
            'telefono': per.telefono or '',
            'fecha_nacimiento': per.fecha_nacimiento,
            'especialidad': cita.medico.especialidad.descripcion,
            'medico': f'{cita.medico.persona.nombre} {cita.medico.persona.apellido}',
            'diagnostico': ', '.join(enfermedades) or 'Sin diagnóstico',
            'sintomas': ', '.join(sintomas) or '-',
            'conducta': conducta or '-',
        })
    return filas


# =====================================================================
#  EXPORTACIÓN
# =====================================================================
def _calcular_edad(fecha_nacimiento):
    """Edad hoy (se usa solo en la hoja de pacientes, no en históricos)."""
    return edad_en_fecha(fecha_nacimiento, datetime.date.today())


def pacientes_exportables():
    nodos = mapa_direcciones()
    filas = []
    for p in (Paciente.objects
              .select_related('persona__nombre', 'persona__apellido',
                              'persona__etnia', 'persona__sangre')):
        per = p.persona
        ident = per.identificaciones.first()
        filas.append({
            'id': p.id,
            'nombre': f'{per.nombre} {per.apellido}',
            'cedula': f'{ident.descripcion} {ident.valor}' if ident else '',
            'sexo': per.get_sexo_display() or '',
            'edad': _calcular_edad(per.fecha_nacimiento),
            'fecha_nacimiento': per.fecha_nacimiento,
            'etnia': per.etnia.tipo_etnia if per.etnia else '',
            'sangre': per.sangre.tipo_sangre if per.sangre else '',
            'ubicacion': ruta_direccion(per.direccion_id, nodos),
            'telefono': per.telefono or '',
        })
    return filas


def visitas_exportables(desde=None, hasta=None):
    filas = []
    for r in reporte_historico(desde, hasta):
        filas.append({
            'fecha': r['fecha'],
            'dia_semana': r['dia_semana'],
            'paciente': f"{r['nombre']} {r['apellido']}",
            'sexo': r['sexo'],
            'edad': r['edad'],
            'medico': r['medico'],
            'especialidad': r['especialidad'],
            'estado': 'Atendido',
            'diagnostico': r['diagnostico'],
            'sintomas': r['sintomas'],
            'conducta': r['conducta'],
        })
    return filas

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from apps import catalog
from apps.usuarios.permissions import permiso_requerido, valida_accion
from apps.diagnostico.models import (Consulta, Diagnostico, Conducta, Enfermedad,
                                     Sintomas)
from apps.citas.models import Cita
from apps.mediciones.models import (MedicionesCabecera, MedicionesDetalles,
                                    EquipoParametros)
from apps.antecedentes.models import AntecedentesSalud
from apps.catalog import (TIPOS_ANTECEDENTE, TIPOS_ENFERMEDAD,
                          TIPOS_SINTOMA)

ESTADO_MAP = {
    1: 'En espera',
    2: 'Atendido',
    3: 'Cancelada',
}

# Conductas medicas disponibles (se guardan en conducta.conducta[])
CONDUCTAS = [
    ('engresado', 'Engresado'),
    ('remitido', 'Remitido'),
    ('derivado', 'Derivado'),
    ('observado', 'Observado'),
    ('despacho', 'Despacho'),
]


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

    if q:
        consultas = consultas.filter(
            Q(cita__paciente__persona__identificaciones__valor__icontains=q))

    if fecha:
        consultas = consultas.filter(cita__fecha_atencion=fecha)

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
        cedula = f"{ident.descripcion} {ident.valor}" if ident else ''
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
@permiso_requerido('citas.ver')
def atender_cita(request, cita_id=None):
    """Atencion de una cita: mediciones, antecedentes y diagnostico."""
    if cita_id is None:
        # Sin cita especifica: listado de citas en espera para atender
        citas = (Cita.objects.filter(estado_cita_id=1)
                 .select_related('paciente__persona__nombre',
                                  'paciente__persona__apellido',
                                  'medico__persona__nombre',
                                  'medico__persona__apellido')
                 .order_by('fecha_atencion', 'id'))
        return render(request, 'diagnostico/atender_cita.html',
                      {'citas_pendientes': citas, 'sin_cita': True})

    cita = get_object_or_404(
        Cita.objects.select_related('paciente__persona__nombre',
                                    'paciente__persona__apellido',
                                    'medico__persona__nombre',
                                    'medico__persona__apellido'),
        pk=cita_id)

    # La cita interna del sistema (fecha 1900-01-01) no se atiende nunca:
    # solo existe para alojar las filas del catalogo.
    if cita.fecha_atencion.isoformat() == catalog.FECHA_COMODIN:
        return redirect('diagnostico:atender_cita')

    consulta, _ = Consulta.objects.get_or_create(cita=cita,
                                                 defaults={'tipo_consulta': 1})
    # conducta_id es NOT NULL: se crea una conducta por defecto
    conducta_default = catalog.conducta_comodin()
    diagnostico, _ = Diagnostico.objects.get_or_create(
        consulta=consulta,
        defaults={'descr': '', 'conducta': conducta_default})

    if request.method == 'POST':
        action = request.POST.get('action')

        from django.contrib import messages
        if action == 'medicion' and not request.user.tiene_permiso('mediciones.crear'):
            messages.error(request, 'No tienes permiso para registrar mediciones.')
            return redirect(request.path)
        if action == 'antecedente' and not request.user.tiene_permiso('antecedentes.crear'):
            messages.error(request, 'No tienes permiso para registrar antecedentes.')
            return redirect(request.path)
        if action == 'diagnostico' and not request.user.tiene_permiso('diagnostico.crear'):
            messages.error(request, 'No tienes permiso para registrar el diagnóstico.')
            return redirect(request.path)

        if action == 'medicion':
            eps = request.POST.getlist('equipo_parametro')
            valores = request.POST.getlist('valor')
            pares = [(e, v.strip()) for e, v in zip(eps, valores)
                     if e and v.strip()]
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
            tipos = request.POST.getlist('antecedente_tipo')
            descs = request.POST.getlist('descripcion')
            for tipo, descripcion in zip(tipos, descs):
                descripcion = (descripcion or '').strip()
                if tipo and descripcion:
                    AntecedentesSalud.objects.create(
                        paciente=cita.paciente,
                        descrip=tipo[:20],
                        antecedente_salud_id=0,
                        valor=descripcion[:20],
                    )

        elif action == 'diagnostico':
            descripcion = request.POST.get('descripcion_diagnostico', '').strip()
            conducta_valor = request.POST.get('conducta', '').strip()
            conducta_desc = request.POST.get('conducta_descripcion', '').strip()

            # 1. Enfermedades (desc[] y valor son NOT NULL).
            #    El paciente puede presentar varias enfermedades de distintas
            #    categorias: cada fila envia su categoria, la enfermedad
            #    elegida del catalogo y (si aplica) el texto escrito a mano.
            enf_categorias = request.POST.getlist('enfermedad_categoria')
            enf_sel = request.POST.getlist('enfermedad')
            enf_otro = request.POST.getlist('enfermedad_otro')

            for i in range(max(len(enf_categorias), len(enf_sel))):
                cat = (enf_categorias[i] if i < len(enf_categorias) else '').strip()
                sel = (enf_sel[i] if i < len(enf_sel) else '').strip()
                otro = (enf_otro[i] if i < len(enf_otro) else '').strip()

                # Si se eligio "otro", manda el texto escrito por el medico
                nombre = otro if sel == '__OTRO__' else sel
                if nombre:
                    # La categoría es otra fila de enfermedad. Si no se
                    # eligió, apunta a la ancla NINGUNO (0): nunca NULL.
                    try:
                        padre = int(cat) if cat.isdigit() else 0
                    except (TypeError, ValueError):
                        padre = 0
                    Enfermedad.objects.create(
                        diagnostico=diagnostico,
                        desc=[nombre[:20]],
                        valor=nombre[:20],
                        tipo=2 if padre else 1,
                        enfermedad_id=padre,
                    )

            # 2. Sintomas (desc y diagnostico_id son NOT NULL).
            #    El paciente puede presentar varios sintomas de distintas
            #    categorias: cada fila envia su categoria, el sintoma elegido
            #    del catalogo y (si aplica) el texto escrito a mano.
            categorias = request.POST.getlist('sintoma_categoria')
            sintomas_sel = request.POST.getlist('sintomas')
            sintomas_otro = request.POST.getlist('sintoma_otro')

            for i in range(max(len(categorias), len(sintomas_sel))):
                cat = (categorias[i] if i < len(categorias) else '').strip()
                sel = (sintomas_sel[i] if i < len(sintomas_sel) else '').strip()
                otro = (sintomas_otro[i] if i < len(sintomas_otro) else '').strip()

                # Si se eligio "otro", manda el texto escrito por el medico
                desc = otro if sel == '__OTRO__' else sel
                if desc:
                    # Igual que las enfermedades: 0 = NINGUNO si no hay
                    # categoría, nunca NULL.
                    try:
                        depende = int(cat) if cat.isdigit() else 0
                    except (TypeError, ValueError):
                        depende = 0
                    Sintomas.objects.create(
                        diagnostico=diagnostico,
                        desc=desc[:20],
                        depende=depende,
                        tipo=2 if depende else 1,
                    )

            # 3. Descripcion del diagnostico
            if descripcion:
                diagnostico.descr = descripcion[:40]

            # 4. Conducta medica (conducta[] + descripcion de observaciones)
            if conducta_valor:
                obj = Conducta.objects.filter(
                    conducta__contains=[conducta_valor]).first()
                if not obj:
                    obj = Conducta(conducta=[conducta_valor])
                obj.descripcion = conducta_desc[:255] or obj.descripcion
                obj.save()
                diagnostico.conducta = obj

            diagnostico.save()

            # 5. Cita atendida
            cita.estado_cita_id = 2
            cita.save()
            return redirect('citas:lista_citas')

    # --- Contexto para render ---
    ant_qs = AntecedentesSalud.objects.filter(paciente=cita.paciente).order_by('id')
    antecedentes_salud = [a for a in ant_qs if a.descrip == 'Antecedente Personal']
    antecedentes_familiares = [a for a in ant_qs if a.descrip == 'Antecedente Familiar']

    mediciones = MedicionesCabecera.objects.filter(
        paciente=cita.paciente).order_by('-fecha_toma')[:5]
    enfermedades = Enfermedad.objects.filter(diagnostico=diagnostico)
    sintomas = Sintomas.objects.filter(diagnostico=diagnostico)
    equipo_parametros = EquipoParametros.objects.select_related(
        'parametro', 'equipo').all()

    # Catalogo de enfermedades: raices (enfermedad_id NULL) y sus hijos.
    # Ademas del catalogo se ofrecen las enfermedades ya registradas en
    # diagnosticos reales de esa misma categoria (historial del consultorio).
    diag_cat = catalog.diagnostico_comodin()
    cat_raices = Enfermedad.objects.filter(enfermedad_id=0, tipo=1,
                                           diagnostico=diag_cat)
    catalogo = []
    for raiz in cat_raices:
        hijos = list(Enfermedad.objects
                     .filter(enfermedad_id=raiz.id, diagnostico=diag_cat)
                     .values_list('valor', flat=True))
        usadas = list(Enfermedad.objects
                      .filter(enfermedad_id=raiz.id)
                      .exclude(diagnostico=diag_cat)
                      .values_list('valor', flat=True))
        # sin duplicados, preserving el orden
        nombres = list(dict.fromkeys(hijos + usadas))
        catalogo.append({
            'id': raiz.id,
            'dsc': raiz.valor,
            'enfermedades': nombres,
        })

    # Catalogo de sintomas: raices (depende 0 = NINGUNO) y sus hijos
    sin_raices = Sintomas.objects.filter(depende=0, tipo=1,
                                         diagnostico=diag_cat)
    sintomas_catalogo = []
    for raiz in sin_raices:
        hijos = list(Sintomas.objects.filter(depende=raiz.id,
                                             diagnostico=diag_cat))
        sintomas_catalogo.append({
            'id': raiz.id,
            'dsc': raiz.desc,
            'sintomas': [h.desc for h in hijos],
        })

    contexto = {
        'cita': cita,
        'consulta': consulta,
        'diagnostico': diagnostico,
        'tipos_antecedente': TIPOS_ANTECEDENTE,
        'antecedentes_salud': antecedentes_salud,
        'antecedentes_familiares': antecedentes_familiares,
        'mediciones': mediciones,
        'enfermedades': enfermedades,
        'sintomas': sintomas,
        'equipo_parametros': equipo_parametros,
        'catalogo': catalogo,
        'sintomas_catalogo': sintomas_catalogo,
        'conductas': CONDUCTAS,
    }
    return render(request, 'diagnostico/atender_cita.html', contexto)


@login_required
@permiso_requerido('catalogo-enfermedades.ver')
def gestion_catalogo_enfermedades(request):
    """Catálogo de enfermedades y síntomas.

    Estructura de ancla (igual que direcciones):
        id 0 = NINGUNO
        tipo 1 = Categoría (raíz)   -> padre 0
        tipo 2 = Enfermedad/Síntoma -> padre = la categoría

    Ambas tablas tienen diagnostico_id NOT NULL, así que el catálogo se
    guarda contra el diagnóstico comodín.
    """
    import json
    diag = catalog.diagnostico_comodin()

    if request.method == 'POST':
        action = request.POST.get('action')
        rechazo = valida_accion(request, action, 'catalogo-enfermedades')
        if rechazo:
            return rechazo

        # --- Enfermedades ---
        if action in ('crear_enfermedad', 'editar_enfermedad'):
            nombre = request.POST.get('dsc', '').strip()[:20]
            if not nombre:
                return redirect('diagnostico:gestion_catalogo_enfermedades')

            nivel = request.POST.get('nivel', '2')
            tipo = 1 if nivel == '1' else 2

            # Padre: 0 (NINGUNO) si es categoría; si no, el id recibido
            # pero solo si es una categoría real.
            padre = 0
            if tipo == 2:
                try:
                    propuesto = int(request.POST.get('enfermedad_id') or 0)
                except (TypeError, ValueError):
                    propuesto = 0
                if propuesto and Enfermedad.objects.filter(
                        id=propuesto, tipo=1).exists():
                    padre = propuesto

            if action == 'crear_enfermedad':
                Enfermedad.objects.create(
                    diagnostico=diag, desc=[nombre], valor=nombre,
                    tipo=tipo, enfermedad_id=padre)
            else:
                obj = Enfermedad.objects.filter(
                    pk=request.POST.get('id')).first()
                if obj:
                    obj.valor = nombre
                    obj.desc = [nombre]
                    obj.tipo = tipo
                    obj.enfermedad_id = padre
                    obj.save()

        # --- Síntomas ---
        elif action in ('crear_sintoma', 'editar_sintoma'):
            desc = request.POST.get('desc', '').strip()[:20]
            if not desc:
                return redirect('diagnostico:gestion_catalogo_enfermedades')

            nivel = request.POST.get('nivel', '2')
            tipo = 1 if nivel == '1' else 2

            padre = 0
            if tipo == 2:
                try:
                    propuesto = int(request.POST.get('depende') or 0)
                except (TypeError, ValueError):
                    propuesto = 0
                if propuesto and Sintomas.objects.filter(
                        id=propuesto, tipo=1).exists():
                    padre = propuesto

            if action == 'crear_sintoma':
                Sintomas.objects.create(
                    diagnostico=diag, desc=desc, depende=padre, tipo=tipo)
            else:
                obj = Sintomas.objects.filter(
                    pk=request.POST.get('id')).first()
                if obj:
                    obj.desc = desc
                    obj.tipo = tipo
                    obj.depende = padre
                    obj.save()

        return redirect('diagnostico:gestion_catalogo_enfermedades')

    # --- Listado ---
    enf = list(Enfermedad.objects.filter(diagnostico=diag)
               .exclude(id=0).order_by('tipo', 'valor'))
    mapa_enf = {e.id: e.valor for e in Enfermedad.objects.all()}
    for e in enf:
        e.padre_valor = mapa_enf.get(e.enfermedad_id, 'NINGUNO')

    sin = list(Sintomas.objects.filter(diagnostico=diag)
               .exclude(id=0).order_by('tipo', 'desc'))
    mapa_sin = {s.id: s.desc for s in Sintomas.objects.all()}
    for s in sin:
        s.padre_valor = mapa_sin.get(s.depende, 'NINGUNO')

    cat_enf = Enfermedad.objects.filter(tipo=1, diagnostico=diag).exclude(
        id=0).order_by('valor')
    cat_sin = Sintomas.objects.filter(tipo=1, diagnostico=diag).exclude(
        id=0).order_by('desc')

    padres_json = json.dumps({
        'enf': {
            '1': [{'id': 0, 'valor': 'NINGUNO'}],
            '2': [{'id': c.id, 'valor': c.valor} for c in cat_enf],
        },
        'sin': {
            '1': [{'id': 0, 'valor': 'NINGUNO'}],
            '2': [{'id': c.id, 'valor': c.desc} for c in cat_sin],
        },
    }, ensure_ascii=False)

    return render(request, 'diagnostico/gestion_catalogo_enfermedades.html', {
        'enfermedades': enf,
        'sintomas': sin,
        'padres_json': padres_json,
        'tipos_enfermedad': TIPOS_ENFERMEDAD,
        'tipos_sintoma': TIPOS_SINTOMA,
    })

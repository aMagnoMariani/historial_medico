import io

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from . import services
from apps.usuarios.permissions import permiso_requerido


@login_required
@permiso_requerido('estadisticas.ver')
def por_ubicacion(request, padre_id=None):
    """Navegación jerárquica: Estado -> Municipio -> Parroquia -> Sector.

    Arranca en Monagas. Al hacer clic en un municipio muestra sus
    parroquias, y así sucesivamente hasta los pacientes del sector.
    """
    datos = services.ubicacion_nivel(padre_id)
    return render(request, 'estadistica/por_ubicacion.html', {
        'datos': datos,
        'desde': request.GET.get('desde') or '',
        'hasta': request.GET.get('hasta') or '',
    })


def _rango_fechas(request):
    """Lee desde/hasta del querystring."""
    return (request.GET.get('desde') or None,
            request.GET.get('hasta') or None)


@login_required
@permiso_requerido('estadisticas.ver')
def dashboard(request):
    desde, hasta = _rango_fechas(request)

    contexto = {
        'desde': request.GET.get('desde') or '',
        'hasta': request.GET.get('hasta') or '',
        'buscar': request.GET.get('q') or '',
        'resumen': services.resumen_general(desde, hasta),
        'citas_mes': services.citas_por_mes(),
        'citas_estado': services.citas_por_estado(),
        'citas_especialidad': services.citas_por_especialidad(),
        'especialidades_atendidas': services.especialidades_atendidas(),
        'enfermedades_top': services.enfermedades_frecuentes(),
        'sintomas_top': services.sintomas_frecuentes(),
        'pacientes_por_sintoma': services.pacientes_por_sintoma(),
        'antecedentes_top': services.antecedentes_frecuentes(),
        'pacientes_mes': services.pacientes_atendidos_por_mes(),
        'pacientes_sexo': services.pacientes_por_sexo(),
        'pacientes_etnia': services.pacientes_por_etnia(),
        # --- Nuevos reportes ---
        'edad_por_sexo': services.edad_por_sexo(desde, hasta),
        'edad_por_sexo_totales': services.edad_por_sexo_totales(desde, hasta),
        'edad_por_especialidad': services.edad_por_especialidad(desde, hasta),
        'esp_edad_sexo': services.especialidad_edad_sexo(desde, hasta),
        'historico': services.reporte_historico(desde, hasta,
                                                request.GET.get('q') or None),
        'ubicacion': services.ubicacion_nivel(),
    }
    return render(request, 'estadistica/dashboard.html', contexto)


# =====================================================================
#  EXPORTACIÓN
# =====================================================================
@login_required
@permiso_requerido('estadisticas.exportar')
def exportar_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment

    desde, hasta = _rango_fechas(request)

    wb = Workbook()
    negrita = Font(bold=True)

    def titular(ws, fila, textos):
        ws.append(textos)
        for i in range(1, len(textos) + 1):
            ws.cell(row=ws.max_row, column=i).font = negrita

    # -- Hoja 1: Resumen --
    ws = wb.active
    ws.title = 'Resumen'
    ws.append(['Estadísticas del Consultorio'])
    ws['A1'].font = Font(bold=True, size=14)
    ws.append([])
    resumen = services.resumen_general(desde, hasta)
    for clave, valor in resumen.items():
        ws.append([clave.replace('_', ' ').title(), valor])
    ws.append([])
    titular(ws, None, ['Enfermedades más frecuentes', 'Total'])
    for r in services.enfermedades_frecuentes():
        ws.append([r['desc'], r['total']])
    ws.append([])
    titular(ws, None, ['Síntoma', 'Pacientes distintos'])
    for r in services.pacientes_por_sintoma():
        ws.append([r['desc'], r['pacientes']])
    ws.append([])
    titular(ws, None, ['Citas por mes', 'Total'])
    for r in services.citas_por_mes():
        ws.append([r['mes'].strftime('%Y-%m') if r['mes'] else '', r['total']])

    # -- Hoja 2: Edad x Sexo --
    ws2 = wb.create_sheet('Edad por Sexo')
    titular(ws2, None, ['Rango de edad', 'Masculino', 'Femenino', 'Otro', 'Total'])
    for r in services.edad_por_sexo(desde, hasta):
        ws2.append([r['rango'], r['M'], r['F'], r['O'], r['total']])

    # -- Hoja 3: Edad x Especialidad --
    ws3 = wb.create_sheet('Edad por Especialidad')
    cruce = services.edad_por_especialidad(desde, hasta)
    titular(ws3, None, ['Rango de edad'] + cruce['especialidades'] + ['Total'])
    for fila in cruce['filas']:
        ws3.append([fila['rango']] + fila['valores'] + [fila['total']])
    ws3.append(['TOTAL'] + cruce['totales'])

    # -- Hoja 3b: Especialidad x Edad x Sexo (formato del ejemplo) --
    ws3b = wb.create_sheet('Esp x Edad x Sexo')
    neg = Font(bold=True)
    centrado = Alignment(horizontal='center')
    esp = services.especialidad_edad_sexo(desde, hasta)

    # Fila 1: nombre de la especialidad y de cada rango (cada rango ocupa
    # dos columnas: m y f, igual que el ejemplo)
    ws3b.cell(row=1, column=1, value='Especialidad')
    col = 2
    for r in esp['rangos']:
        ws3b.cell(row=1, column=col, value=r)
        ws3b.merge_cells(start_row=1, start_column=col,
                         end_row=1, end_column=col + 1)
        col += 2
    ws3b.cell(row=1, column=col, value='Totales')
    ws3b.merge_cells(start_row=1, start_column=col,
                     end_row=1, end_column=col + 2)

    # Fila 2: sub-cabecera m / f
    ws3b.cell(row=2, column=1, value='')
    col = 2
    for _ in esp['rangos']:
        ws3b.cell(row=2, column=col, value='m')
        ws3b.cell(row=2, column=col + 1, value='f')
        col += 2
    ws3b.cell(row=2, column=col, value='m')
    ws3b.cell(row=2, column=col + 1, value='f')
    ws3b.cell(row=2, column=col + 2, value='tot')

    total_columnas = 1 + 2 * len(esp['rangos']) + 3
    for i in range(1, total_columnas + 1):
        ws3b.cell(row=1, column=i).font = neg
        ws3b.cell(row=2, column=i).font = neg
        ws3b.cell(row=1, column=i).alignment = centrado
        ws3b.cell(row=2, column=i).alignment = centrado

    # Filas de datos
    for fila in esp['filas']:
        valores = [fila['especialidad']]
        for c in fila['celdas']:
            valores += [c['M'], c['F']]
        valores += [fila['total_M'], fila['total_F'], fila['total']]
        ws3b.append(valores)

    # Fila de totales
    tot = ['TOTALES']
    for t in esp['totales']:
        tot += [t['M'], t['F']]
    tg = esp['totales_generales']
    tot += [tg['M'], tg['F'], tg['total']]
    ws3b.append(tot)
    for i in range(1, total_columnas + 1):
        ws3b.cell(row=ws3b.max_row, column=i).font = neg

    ws3b.freeze_panes = 'B3'

    # -- Hoja 4: Pacientes --
    ws4 = wb.create_sheet('Pacientes')
    encabezado = ['ID', 'Nombre', 'Cédula', 'Sexo', 'Edad',
                  'Fecha Nacimiento', 'Etnia', 'Sangre',
                  'Dirección', 'Teléfono']
    titular(ws4, None, encabezado)
    for p in services.pacientes_exportables():
        ws4.append([p['id'], p['nombre'], p['cedula'], p['sexo'],
                    p['edad'], str(p['fecha_nacimiento'] or ''), p['etnia'],
                    p['sangre'], p['ubicacion'], p['telefono']])

    # -- Hoja 5: Reporte histórico --
    ws5 = wb.create_sheet('Histórico')
    titular(ws5, None, ['Fecha', 'Nombre', 'Apellido', 'Edad', 'Sexo', 'Cédula',
                        'Dirección', 'Teléfono', 'Fecha Nacimiento',
                        'Especialidad', 'Médico', 'Diagnóstico', 'Conducta'])
    for h in services.reporte_historico(desde, hasta):
        ws5.append([str(h['fecha']), h['nombre'], h['apellido'], h['edad'],
                    h['sexo'], h['cedula'], h['direccion'], h['telefono'],
                    str(h['fecha_nacimiento'] or ''), h['especialidad'],
                    h['medico'], h['diagnostico'], h['conducta']])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (
        'attachment; filename="estadisticas_consultorio.xlsx"')
    wb.save(response)
    return response


@login_required
@permiso_requerido('estadisticas.exportar')
def exportar_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    desde, hasta = _rango_fechas(request)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            leftMargin=36, rightMargin=36,
                            topMargin=36, bottomMargin=36)
    estilos = getSampleStyleSheet()
    historia = []

    rango = 'Todo el historial'
    if desde or hasta:
        rango = f"Desde {desde or 'inicio'} hasta {hasta or 'hoy'}"
    historia.append(Paragraph('Estadísticas del Consultorio', estilos['Title']))
    historia.append(Paragraph(f'Rango de visitas: {rango}', estilos['Italic']))
    historia.append(Spacer(1, 12))

    def tabla(titulo, encabezado, filas):
        historia.append(Paragraph(titulo, estilos['Heading2']))
        datos = [encabezado] + filas
        t = Table(datos, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#bcd6f5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1c3d6e')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#a8bcd9')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#eef4fc')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        historia.append(t)
        historia.append(Spacer(1, 12))

    resumen = services.resumen_general(desde, hasta)
    tabla('Resumen General', ['Indicador', 'Total'],
          [[k.replace('_', ' ').title(), str(v)] for k, v in resumen.items()])

    tabla('Pacientes Registrados',
          ['Nombre', 'Cédula', 'Sexo', 'Edad', 'Etnia',
           'Sangre', 'Dirección', 'Teléfono'],
          [[p['nombre'], p['cedula'], p['sexo'], str(p['edad'] or ''),
            p['etnia'], p['sangre'], p['ubicacion'], p['telefono']]
           for p in services.pacientes_exportables()])

    # Edad x sexo
    tabla('Visitas por Edad y Sexo',
          ['Rango de edad', 'Masculino', 'Femenino', 'Otro', 'Total'],
          [[r['rango'], str(r['M']), str(r['F']), str(r['O']), str(r['total'])]
           for r in services.edad_por_sexo(desde, hasta)])

    # Edad x especialidad
    cruce = services.edad_por_especialidad(desde, hasta)
    tabla('Visitas por Edad y Especialidad',
          ['Rango de edad'] + cruce['especialidades'] + ['Total'],
          [[f['rango']] + [str(v) for v in f['valores']]
           + [str(f['total'])] for f in cruce['filas']])

    # Especialidad x Edad x Sexo (formato del ejemplo, doble cabecera)
    esp = services.especialidad_edad_sexo(desde, hasta)
    encabezado_esp = ['Especialidad']
    for _ in esp['rangos']:
        encabezado_esp += ['m', 'f']
    encabezado_esp += ['m', 'f', 'tot']
    filas_esp = []
    for f in esp['filas']:
        vals = []
        for c in f['celdas']:
            vals += [str(c['M']), str(c['F'])]
        vals += [str(f['total_M']), str(f['total_F']), str(f['total'])]
        filas_esp.append([f['especialidad']] + vals)
    tot_vals = []
    for t in esp['totales']:
        tot_vals += [str(t['M']), str(t['F'])]
    tg = esp['totales_generales']
    tot_vals += [str(tg['M']), str(tg['F']), str(tg['total'])]
    filas_esp.append(['TOTALES'] + tot_vals)
    tabla('Visitas por Especialidad, Edad y Sexo',
          encabezado_esp, filas_esp)

    tabla('Visitas al Consultorio',
          ['Fecha', 'Día', 'Paciente', 'Sexo', 'Edad', 'Médico',
           'Especialidad', 'Diagnóstico', 'Conducta'],
          [[str(v['fecha']), v['dia_semana'],
            f"{v['nombre']} {v['apellido']}", v['sexo'],
            str(v['edad'] if v['edad'] is not None else ''), v['medico'],
            v['especialidad'], v['diagnostico'], v['conducta']]
           for v in services.reporte_historico(desde, hasta)])

    doc.build(historia)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="estadisticas_consultorio.pdf"')
    return response


# =====================================================================
#  EXPORTACIÓN DEL REPORTE HISTÓRICO (por separado)
# =====================================================================
@login_required
@permiso_requerido('estadisticas.exportar')
def exportar_historico_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    desde, hasta = _rango_fechas(request)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Histórico'
    ws.append(['Reporte histórico de atenciones'])
    ws['A1'].font = Font(bold=True, size=14)
    rango = 'Todo el historial'
    if desde or hasta:
        rango = f"Desde {desde or 'inicio'} hasta {hasta or 'hoy'}"
    ws.append([f'Rango: {rango}'])
    ws.append([])

    encabezado = ['Fecha', 'Nombre', 'Apellido', 'Edad', 'Sexo', 'Cédula',
                  'Dirección', 'Teléfono', 'Fecha Nacimiento',
                  'Especialidad', 'Médico', 'Diagnóstico', 'Conducta']
    ws.append(encabezado)
    for i in range(1, len(encabezado) + 1):
        ws.cell(row=ws.max_row, column=i).font = Font(bold=True)

    for h in services.reporte_historico(desde, hasta,
                                        request.GET.get('q') or None):
        ws.append([str(h['fecha']), h['nombre'], h['apellido'], h['edad'],
                   h['sexo'], h['cedula'], h['direccion'], h['telefono'],
                   str(h['fecha_nacimiento'] or ''), h['especialidad'],
                   h['medico'], h['diagnostico'], h['conducta']])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (
        'attachment; filename="reporte_historico.xlsx"')
    wb.save(response)
    return response


@login_required
@permiso_requerido('estadisticas.exportar')
def exportar_historico_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    desde, hasta = _rango_fechas(request)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            leftMargin=18, rightMargin=18,
                            topMargin=24, bottomMargin=24)
    estilos = getSampleStyleSheet()
    historia = [Paragraph('Reporte Histórico de Atenciones', estilos['Title'])]

    rango = 'Todo el historial'
    if desde or hasta:
        rango = f"Desde {desde or 'inicio'} hasta {hasta or 'hoy'}"
    historia.append(Paragraph(f'Rango: {rango}', estilos['Italic']))
    historia.append(Paragraph(
        'La edad se calcula a la fecha de atención, no a la fecha actual.',
        estilos['Italic']))
    historia.append(Spacer(1, 12))

    encabezado = ['Fecha', 'Nombre', 'Apellido', 'Edad', 'Sexo', 'Cédula',
                  'Dirección', 'Teléfono', 'F. Nac.', 'Diagnóstico', 'Conducta']
    filas = []
    for h in services.reporte_historico(desde, hasta,
                                        request.GET.get('q') or None):
        filas.append([str(h['fecha']), h['nombre'], h['apellido'],
                      str(h['edad'] if h['edad'] is not None else ''),
                      h['sexo'], h['cedula'], h['direccion'], h['telefono'],
                      str(h['fecha_nacimiento'] or ''), h['diagnostico'],
                      h['conducta']])

    t = Table([encabezado] + filas, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#bcd6f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1c3d6e')),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#a8bcd9')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#eef4fc')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    historia.append(t)

    doc.build(historia)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="reporte_historico.pdf"')
    return response

import io

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from . import services


@login_required
def dashboard(request):
    contexto = {
        'resumen': services.resumen_general(),
        'citas_mes': services.citas_por_mes(),
        'citas_estado': services.citas_por_estado(),
        'citas_especialidad': services.citas_por_especialidad(),
        'especialidades_atendidas': services.especialidades_atendidas(),
        'enfermedades_top': services.enfermedades_frecuentes(),
        'enfermedades_categoria': services.enfermedades_por_categoria(),
        'sintomas_top': services.sintomas_frecuentes(),
        'pacientes_por_sintoma': services.pacientes_por_sintoma(),
        'antecedentes_top': services.antecedentes_frecuentes(),
        'promedio_parametros': services.promedio_mediciones_por_parametro(),
        'pacientes_mes': services.pacientes_atendidos_por_mes(),
        'pacientes_sexo': services.pacientes_por_sexo(),
        'pacientes_edad': services.pacientes_por_edad(),
        'pacientes_etnia': services.pacientes_por_etnia(),
        'pacientes_ubicacion': services.pacientes_por_ubicacion(),
    }
    return render(request, 'estadistica/dashboard.html', contexto)


@login_required
def exportar_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    desde = request.GET.get('desde') or None
    hasta = request.GET.get('hasta') or None

    wb = Workbook()
    negrita = Font(bold=True)

    # -- Hoja 1: Resumen --
    ws = wb.active
    ws.title = 'Resumen'
    ws.append(['Estadísticas del Consultorio'])
    ws['A1'].font = Font(bold=True, size=14)
    ws.append([])
    resumen = services.resumen_general()
    for clave, valor in resumen.items():
        ws.append([clave.replace('_', ' ').title(), valor])
    ws.append([])
    ws.append(['Enfermedades más frecuentes', 'Total'])
    ws[ws.max_row][0].font = negrita
    ws[ws.max_row][1].font = negrita
    for r in services.enfermedades_frecuentes():
        ws.append([r['valor'], r['total']])
    ws.append([])
    ws.append(['Síntoma', 'Pacientes distintos'])
    ws[ws.max_row][0].font = negrita
    ws[ws.max_row][1].font = negrita
    for r in services.pacientes_por_sintoma():
        ws.append([r['sintoma'], r['pacientes']])
    ws.append([])
    ws.append(['Citas por mes', 'Total'])
    ws[ws.max_row][0].font = negrita
    ws[ws.max_row][1].font = negrita
    for r in services.citas_por_mes():
        ws.append([r['mes'].strftime('%Y-%m') if r['mes'] else '', r['total']])

    # -- Hoja 2: Pacientes --
    ws2 = wb.create_sheet('Pacientes')
    encabezado = ['ID', 'Nombre', 'Cédula', 'Sexo', 'Edad',
                  'Fecha Nacimiento', 'Etnia', 'Sangre',
                  'Ubicación (Estado)', 'Teléfono']
    ws2.append(encabezado)
    for i, _ in enumerate(encabezado, 1):
        ws2.cell(row=1, column=i).font = negrita
    for p in services.pacientes_exportables():
        ws2.append([p['id'], p['nombre'], p['cedula'], p['sexo'],
                    p['edad'], str(p['fecha_nacimiento'] or ''), p['etnia'],
                    p['sangre'], p['ubicacion'], p['telefono']])

    # -- Hoja 3: Visitas --
    ws3 = wb.create_sheet('Visitas')
    encabezado = ['Fecha', 'Día', 'Paciente', 'Sexo', 'Edad', 'Médico',
                  'Especialidad', 'Tipo', 'Estado', 'Enfermedades', 'Síntomas']
    ws3.append(encabezado)
    for i, _ in enumerate(encabezado, 1):
        ws3.cell(row=1, column=i).font = negrita
    for v in services.visitas_exportables(desde, hasta):
        ws3.append([str(v['fecha']), v['dia_semana'], v['paciente'],
                    v['sexo'], v['edad'], v['medico'], v['especialidad'],
                    v['tipo'], v['estado'], v['enfermedades'], v['sintomas']])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (
        'attachment; filename="estadisticas_consultorio.xlsx"')
    wb.save(response)
    return response


@login_required
def exportar_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    desde = request.GET.get('desde') or None
    hasta = request.GET.get('hasta') or None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            leftMargin=36, rightMargin=36,
                            topMargin=36, bottomMargin=36)
    estilos = getSampleStyleSheet()
    historia = []

    historia.append(Paragraph('Estadísticas del Consultorio',
                              estilos['Title']))
    rango = 'Todo el historial'
    if desde or hasta:
        rango = f"Desde {desde or 'inicio'} hasta {hasta or 'hoy'}"
    historia.append(Paragraph(f'Rango de visitas: {rango}',
                              estilos['Italic']))
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

    # Resumen
    resumen = services.resumen_general()
    tabla('Resumen General', ['Indicador', 'Total'],
          [[k.replace('_', ' ').title(), str(v)] for k, v in resumen.items()])

    # Pacientes con sus características
    tabla('Pacientes Registrados',
          ['Nombre', 'Cédula', 'Sexo', 'Edad', 'Etnia',
           'Sangre', 'Ubicación', 'Teléfono'],
          [[p['nombre'], p['cedula'], p['sexo'], str(p['edad'] or ''),
            p['etnia'], p['sangre'], p['ubicacion'], p['telefono']]
           for p in services.pacientes_exportables()])

    # Visitas: quiénes llegaron, cuándo, qué se les hizo
    tabla('Visitas al Consultorio',
          ['Fecha', 'Día', 'Paciente', 'Sexo', 'Edad', 'Médico',
           'Especialidad', 'Tipo', 'Estado', 'Enfermedades', 'Síntomas'],
          [[str(v['fecha']), v['dia_semana'], v['paciente'], v['sexo'],
            str(v['edad'] or ''), v['medico'], v['especialidad'], v['tipo'],
            v['estado'], v['enfermedades'], v['sintomas']]
           for v in services.visitas_exportables(desde, hasta)])

    # Síntomas: cuántos pacientes distintos (ej. tos)
    tabla('Pacientes por Síntoma',
          ['Síntoma', 'Pacientes'],
          [[r['sintoma'], str(r['pacientes'])]
           for r in services.pacientes_por_sintoma()])

    doc.build(historia)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="estadisticas_consultorio.pdf"')
    return response

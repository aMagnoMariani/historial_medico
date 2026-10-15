from django.urls import path
from . import views

app_name = 'identificacion'

urlpatterns = [
    path('pacientes/', views.lista_pacientes, name='lista_pacientes'),
    path('paciente/<int:pk>/', views.detalle_paciente, name='detalle_paciente'),
    path('paciente/<int:pk>/historial/', views.historial_paciente, name='historial_paciente'),
    path('registrar/', views.registrar_paciente, name='registrar_paciente'),
    path('medicos/', views.gestion_medicos, name='gestion_medicos'),
    path('especialidades/', views.gestion_especialidades, name='gestion_especialidades'),
    path('tipos-identificacion/', views.gestion_tipos_identificacion, name='gestion_tipos_identificacion'),
    path('direcciones/', views.gestion_direcciones, name='gestion_direcciones'),
    path('catalogo/<str:tipo>/', views.gestion_catalogo_persona, name='gestion_catalogo_persona'),
    path('api/direcciones/', views.api_direcciones, name='api_direcciones'),
    path('api/antecedentes/', views.api_antecedentes, name='api_antecedentes'),
    path('api/crear-sector/', views.api_crear_sector, name='api_crear_sector'),
]

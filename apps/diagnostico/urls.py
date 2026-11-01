from django.urls import path
from . import views

app_name = 'diagnostico'

urlpatterns = [
    path('historial/', views.historial_medico, name='historial_medico'),
    path('api/buscar/', views.api_buscar_historial, name='api_buscar_historial'),
    # Sin ID: listado de citas en espera para atender
    path('atender/', views.atender_cita, name='atender_cita'),
    # Con ID: atiende una cita concreta
    path('atender/<int:cita_id>/', views.atender_cita, name='atender_cita_id'),
    path('catalogo-enfermedades/', views.gestion_catalogo_enfermedades,
         name='gestion_catalogo_enfermedades'),
]

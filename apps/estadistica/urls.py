from django.urls import path

from . import views

app_name = 'estadistica'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    # Ubicación jerárquica: Monagas -> Municipio -> Parroquia -> Sector
    path('ubicacion/', views.por_ubicacion, name='por_ubicacion'),
    path('ubicacion/<int:padre_id>/', views.por_ubicacion, name='por_ubicacion_nivel'),
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('historico/excel/', views.exportar_historico_excel, name='exportar_historico_excel'),
    path('historico/pdf/', views.exportar_historico_pdf, name='exportar_historico_pdf'),
]

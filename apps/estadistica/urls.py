from django.urls import path

from . import views

app_name = 'estadistica'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_pdf, name='exportar_pdf'),
]

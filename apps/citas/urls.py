from django.urls import path
from . import views

app_name = 'citas'

urlpatterns = [
    path('lista/', views.lista_citas, name='lista_citas'),
    path('api/buscar/', views.api_buscar_citas, name='api_buscar_citas'),
]

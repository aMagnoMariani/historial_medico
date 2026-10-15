from django.urls import path
from . import views

app_name = 'mediciones'

urlpatterns = [
    path('config/', views.gestion_config_mediciones, name='gestion_config_mediciones'),
]

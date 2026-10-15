from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('roles/', views.gestion_roles_permisos, name='gestion_roles_permisos'),
    path('usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('configuracion/', views.configuracion, name='configuracion'),
]

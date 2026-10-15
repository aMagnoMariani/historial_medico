"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

def index_redirect(request):
    return redirect('usuarios:login')

urlpatterns = [
    path('', index_redirect, name='index'),
    path('admin/', admin.site.urls),
    path('usuarios/', include('apps.usuarios.urls')),
    path('estadistica/', include('apps.estadistica.urls')),
    path('identificacion/', include('apps.identificacion.urls')),
    path('citas/', include('apps.citas.urls')),
    path('diagnostico/', include('apps.diagnostico.urls')),
    path('mediciones/', include('apps.mediciones.urls')),
]

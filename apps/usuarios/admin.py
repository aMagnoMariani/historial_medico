from django.contrib import admin

from .models import Permiso, Rol, RolPermiso, Usuario


class RolPermisoInline(admin.TabularInline):
    model = RolPermiso
    extra = 1


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'estado')
    inlines = [RolPermisoInline]


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion')
    search_fields = ('codigo',)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'rol', 'persona', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('username',)

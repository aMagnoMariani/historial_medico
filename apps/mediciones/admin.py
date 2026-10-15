from django.contrib import admin

from .models import (EquipoParametros, Equipos, MedicionesCabecera,
                     MedicionesDetalles, Parametros)

admin.site.register(Equipos)
admin.site.register(Parametros)
admin.site.register(EquipoParametros)


class DetallesInline(admin.TabularInline):
    model = MedicionesDetalles
    extra = 1


@admin.register(MedicionesCabecera)
class MedicionesCabeceraAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'fecha_toma')
    inlines = [DetallesInline]

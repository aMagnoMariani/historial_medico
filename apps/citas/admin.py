from django.contrib import admin

from .models import Cita


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'fecha_atencion', 'estado_cita_id')
    list_filter = ('fecha_atencion',)
    search_fields = ('paciente__persona__nombre__descripcion',)

from django.contrib import admin

from .models import (Direccion, Especialidad, Etnia, Identificacion, Medico,
                     Nombres, Paciente, Persona, Sangre, Discapacidad)

admin.site.register(Nombres)
admin.site.register(Direccion)
admin.site.register(Etnia)
admin.site.register(Sangre)
admin.site.register(Especialidad)
admin.site.register(Identificacion)
admin.site.register(Discapacidad)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('nombre_id', 'apellido_id', 'fecha_nacimiento', 'sexo')
    search_fields = ('nombre_id__descripcion', 'apellido_id__descripcion')


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('persona', 'especialidad', 'estado')
    list_filter = ('especialidad', 'estado')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('persona',)
    search_fields = ('persona__nombre_id__descripcion',)
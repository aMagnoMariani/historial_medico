from django.contrib import admin

from .models import (Direccion, Especialidad, Etnia, Identificacion, Medico,
                     Nombres, Paciente, Persona, Sangre)

admin.site.register(Nombres)
admin.site.register(Direccion)
admin.site.register(Etnia)
admin.site.register(Sangre)
admin.site.register(Especialidad)
admin.site.register(Identificacion)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'fecha_nacimiento', 'sexo')
    search_fields = ('nombre__descripcion', 'apellido__descripcion')


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('persona', 'especialidad', 'estado')
    list_filter = ('especialidad', 'estado')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('persona',)
    search_fields = ('persona__nombre__descripcion',)

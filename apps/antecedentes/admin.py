from django.contrib import admin

from .models import AntecedentesSalud


@admin.register(AntecedentesSalud)
class AntecedentesSaludAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'descrip', 'valor')
    search_fields = ('descrip',)

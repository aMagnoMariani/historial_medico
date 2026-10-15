from django.contrib import admin

from .models import Consulta, Diagnostico, Enfermedad, Sintomas


class SintomasInline(admin.TabularInline):
    model = Sintomas
    extra = 1


class EnfermedadInline(admin.TabularInline):
    model = Enfermedad
    extra = 1


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    inlines = [SintomasInline, EnfermedadInline]


admin.site.register(Consulta)

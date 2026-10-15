from django.db import models

from apps.citas.models import Cita


class Consulta(models.Model):
    cita = models.ForeignKey(Cita, models.DO_NOTHING, db_column='cita_id')
    tipo_consulta = models.IntegerField()

    class Meta:
        db_table = '"clinica"."consulta"'


class Diagnostico(models.Model):
    consulta = models.ForeignKey(Consulta, models.DO_NOTHING,
                                 db_column='consulta_id')

    class Meta:
        db_table = '"clinica"."diagnostico"'
        verbose_name = 'Diagnóstico'
        verbose_name_plural = 'Diagnósticos'


class Enfermedad(models.Model):
    # NOTA: estructura jerárquica id, dsc, depid, tipo
    dsc = models.CharField(max_length=100, null=True, blank=True)
    depid = models.IntegerField(null=True, blank=True)
    tipo = models.IntegerField(null=True, blank=True)
    valor = models.CharField(max_length=20, null=True, blank=True)
    diagnostico = models.ForeignKey(Diagnostico, models.DO_NOTHING,
                                    db_column='diagnostico_id')

    class Meta:
        db_table = '"clinica"."enfermedad"'
        verbose_name_plural = 'Enfermedades'

    def __str__(self):
        return self.valor


class Sintomas(models.Model):
    sintoma = models.CharField(max_length=20)
    diagnostico = models.ForeignKey(Diagnostico, models.DO_NOTHING,
                                    db_column='diagnostico_id')

    class Meta:
        db_table = '"clinica"."sintomas"'
        verbose_name_plural = 'Síntomas'

    def __str__(self):
        return self.sintoma

class EnfermedadCatalogo(models.Model):
    dsc = models.CharField(max_length=100)
    depid = models.ForeignKey('self', models.SET_NULL, null=True, blank=True, db_column='depid', related_name='hijos')
    tipo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = '"clinica"."enfermedad_catalogo"'
        verbose_name_plural = 'Catálogo de Enfermedades'

    def __str__(self):
        return self.dsc

from django.db import models

class AntecedenteCategoria(models.Model):
    dsc = models.CharField(max_length=100, verbose_name='Descripción')
    dep_id = models.ForeignKey(
        'self', models.SET_NULL, null=True, blank=True, 
        db_column='depid', related_name='hijos'
    )
    tipo = models.IntegerField(verbose_name='Nivel/Tipo')

    class Meta:
        db_table = '"clinica"."antecedente_categoria"'
        verbose_name = 'Categoría de Antecedente'
        verbose_name_plural = 'Categorías de Antecedentes'

    def __str__(self):
        return self.dsc


class AntecedentesSalud(models.Model):
    descrip = models.CharField(max_length=20, verbose_name='Descripción')
    antecedente_salud_id = models.ForeignKey(
        AntecedenteCategoria, models.DO_NOTHING, 
        db_column='antecedente_salud_id'
    )
    valor = models.CharField(max_length=255)
    paciente = models.ForeignKey(
        'identificacion.Paciente', 
        models.DO_NOTHING, db_column='paciente_id'
    )

    class Meta:
        db_table = '"clinica"."antecedentes_salud"'
        verbose_name_plural = 'Antecedentes de salud'

    def __str__(self):
        return f'{self.antecedente_salud_id}: {self.valor}'

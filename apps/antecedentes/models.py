from django.db import models


class AntecedentesSalud(models.Model):
    """Antecedentes de salud del paciente.

    Estructura de ancla:
        id 0                = NINGUNO
        tipo: 1 = Categoría (Personal / Familiar), 2 = Antecedente
        antecedente_salud_id apunta SIEMPRE a una fila: 0 si es raíz
    """
    descrip = models.CharField(max_length=20)
    antecedente_salud_id = models.IntegerField(default=0)
    valor = models.CharField(max_length=100)
    tipo = models.IntegerField(default=2)
    paciente = models.ForeignKey(
        'identificacion.Paciente',
        models.DO_NOTHING, db_column='paciente_id'
    )

    class Meta:
        db_table = '"clinica"."antecedentes_salud"'
        verbose_name_plural = 'Antecedentes de salud'

    def __str__(self):
        return f'{self.descrip}: {self.valor}'

    def padre(self):
        if self.antecedente_salud_id:
            return AntecedentesSalud.objects.filter(
                pk=self.antecedente_salud_id).first()
        return None

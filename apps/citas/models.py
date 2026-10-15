from django.db import models

from apps.identificacion.models import Medico, Paciente


class Cita(models.Model):
    medico = models.ForeignKey(Medico, models.DO_NOTHING, db_column='medico_id')
    paciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='paciente_id')
    fecha_atencion = models.DateField()
    fecha_creacion = models.TimeField()
    estado_cita_id = models.IntegerField()
    tipo_cita = models.CharField(max_length=20, blank=True, null=True, choices=[('PRIMERA', 'Primera Vez'), ('RUTINA', 'Rutina')])

    class Meta:
        db_table = '"clinica"."cita"'

    def __str__(self):
        return f'Cita {self.paciente} con {self.medico} ({self.fecha_atencion})'

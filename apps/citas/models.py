from django.db import models

from apps.identificacion.models import Medico, Paciente


class TipoCita(models.TextChoices):
    """Motivo por el que se agenda la cita (columna cita.tipo_cita)."""
    PRIMERA = 'PRIMERA', 'Primera Vez'
    RUTINA = 'RUTINA', 'Rutina'
    SEGUIMIENTO = 'SEGUIMIENTO', 'Seguimiento'
    CONTROL = 'CONTROL', 'Control'
    EMERGENCIA = 'EMERGENCIA', 'Emergencia'


class Cita(models.Model):
    medico = models.ForeignKey(Medico, models.DO_NOTHING, db_column='medico_id')
    paciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='paciente_id')
    fecha_atencion = models.DateField()
    fecha_creacion = models.TimeField()
    estado_cita_id = models.IntegerField()
    # Motivo de la cita: primera vez, rutina, seguimiento, control, emergencia
    tipo_cita = models.CharField(max_length=20, choices=TipoCita.choices,
                                 null=True, blank=True)

    class Meta:
        db_table = '"clinica"."cita"'

    def __str__(self):
        return f'Cita {self.paciente} con {self.medico} ({self.fecha_atencion})'

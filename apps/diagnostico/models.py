from django.db import models
from django.contrib.postgres.fields import ArrayField

from apps.citas.models import Cita


class Consulta(models.Model):
    cita = models.ForeignKey(Cita, models.DO_NOTHING, db_column='cita_id')
    tipo_consulta = models.IntegerField()

    class Meta:
        db_table = '"clinica"."consulta"'

    def __str__(self):
        return f'Consulta {self.id}'


class Conducta(models.Model):
    """Conducta medica (engresado, remitido, derivado, observado, despacho...).

    Esquema SQL:
        id           SERIAL PK
        conducta     varchar[]  NOT NULL  (acciones medicas)
        descripcion  varchar            (observaciones del medico)
    """
    conducta = ArrayField(models.TextField())
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = '"clinica"."conducta"'
        verbose_name = 'Conducta Medica'
        verbose_name_plural = 'Conductas Medicas'

    def __str__(self):
        return ', '.join(self.conducta) if self.conducta else 'Sin conducta'


class Diagnostico(models.Model):
    """Diagnostico de un paciente en una consulta.

    Esquema SQL:
        id           SERIAL PK
        consulta_id  integer  NOT NULL
        descr        varchar(40) NOT NULL
        conducta_id  integer  NOT NULL
    """
    consulta = models.ForeignKey(Consulta, models.DO_NOTHING,
                                 db_column='consulta_id')
    descr = models.CharField(max_length=40)
    conducta = models.ForeignKey(Conducta, models.DO_NOTHING,
                                 db_column='conducta_id')

    class Meta:
        db_table = '"clinica"."diagnostico"'
        verbose_name = 'Diagnostico'
        verbose_name_plural = 'Diagnosticos'

    def __str__(self):
        return f'Diagnostico {self.id}: {self.descr}'


class Enfermedad(models.Model):
    """Enfermedades registradas en un diagnostico.

    Estructura de ancla:
        id 0            = NINGUNO
        tipo: 1 = Categoría (raíz), 2 = Enfermedad
        enfermedad_id   apunta SIEMPRE a una fila: 0 si es categoría
    """
    desc = ArrayField(models.CharField(max_length=20), db_column='"desc"')
    valor = models.CharField(max_length=20)
    tipo = models.IntegerField(default=0)
    enfermedad_id = models.IntegerField(default=0)
    diagnostico = models.ForeignKey(Diagnostico, models.DO_NOTHING,
                                    db_column='diagnostico_id')

    class Meta:
        db_table = '"clinica"."enfermedad"'
        verbose_name_plural = 'Enfermedades'

    def __str__(self):
        if self.desc:
            return ', '.join(self.desc[:2]) + ('...' if len(self.desc) > 2 else '')
        return f'Enfermedad {self.id}'

    def padre(self):
        if self.enfermedad_id:
            return Enfermedad.objects.filter(pk=self.enfermedad_id).first()
        return None

    def hijos(self):
        return Enfermedad.objects.filter(
            enfermedad_id=self.id).order_by('valor')


class Sintomas(models.Model):
    """Sintomas registrados en un diagnostico.

    Estructura de ancla:
        id 0      = NINGUNO
        tipo: 1 = Categoría (raíz), 2 = Síntoma
        depende   apunta SIEMPRE a una fila: 0 si es categoría
    """
    desc = models.CharField(max_length=20, db_column='"desc"')
    depende = models.IntegerField(default=0)
    tipo = models.IntegerField(default=1)
    diagnostico = models.ForeignKey(Diagnostico, models.DO_NOTHING,
                                    db_column='diagnostico_id')

    class Meta:
        db_table = '"clinica"."sintomas"'
        verbose_name_plural = 'Sintomas'

    def __str__(self):
        return self.desc

    def padre(self):
        if self.depende:
            return Sintomas.objects.filter(pk=self.depende).first()
        return None

    def hijos(self):
        return Sintomas.objects.filter(depende=self.id).order_by('desc')

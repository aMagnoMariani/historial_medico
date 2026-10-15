from django.db import models

from apps.identificacion.models import Paciente


class Equipos(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_tecnologia = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)

    class Meta:
        db_table = '"clinica"."equipos"'

    def __str__(self):
        return f'{self.nombre} ({self.marca} {self.modelo})'


class Parametros(models.Model):
    dsc = models.CharField(max_length=100, verbose_name='Descripción')
    dep_id = models.IntegerField(null=True, blank=True,
                                 verbose_name='Dependencia (id)')
    dep_dsc = models.CharField(max_length=100, null=True, blank=True,
                               verbose_name='Dependencia (descripción)')
    unidad = models.CharField(max_length=20)

    class Meta:
        db_table = '"clinica"."parametros"'
        unique_together = ('id', 'dsc')
        verbose_name_plural = 'Parámetros'

    def __str__(self):
        return f'{self.dsc} ({self.unidad})'


class EquipoParametros(models.Model):
    equipo = models.ForeignKey(Equipos, models.DO_NOTHING, db_column='equipo_id')
    parametro = models.ForeignKey(Parametros, models.DO_NOTHING,
                                  db_column='parametro_id')

    class Meta:
        db_table = '"clinica"."equipo_parametros"'
        verbose_name_plural = 'Equipo-Parámetros'


class MedicionesCabecera(models.Model):
    fecha_toma = models.DateTimeField(auto_now_add=True)
    paciente = models.ForeignKey(Paciente, models.DO_NOTHING,
                                 db_column='paciente_id')

    class Meta:
        db_table = '"clinica"."mediciones_cabecera"'
        verbose_name = 'Medición (cabecera)'
        verbose_name_plural = 'Mediciones (cabecera)'


class MedicionesDetalles(models.Model):
    medicion = models.ForeignKey(MedicionesCabecera, models.CASCADE,
                                 db_column='medicion_id')
    equipo_parametro = models.ForeignKey(EquipoParametros, models.DO_NOTHING,
                                         db_column='equipo_parametro_id')
    valor_arrojado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = '"clinica"."mediciones_detalles"'
        verbose_name = 'Medición (detalle)'
        verbose_name_plural = 'Mediciones (detalles)'

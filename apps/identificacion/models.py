from django.db import models


class TipoNombre(models.TextChoices):
    NOMBRE = 'NOMBRE', 'Nombre'
    APELLIDO = 'APELLIDO', 'Apellido'


class Sexo(models.TextChoices):
    MASCULINO = 'M', 'Masculino'
    FEMENINO = 'F', 'Femenino'
    OTRO = 'O', 'Otro'


class Nombres(models.Model):
    tipo = models.CharField(max_length=10, choices=TipoNombre.choices)
    descripcion = models.CharField(max_length=30)

    class Meta:
        db_table = '"clinica"."nombres"'
        verbose_name_plural = 'Nombres'

    def __str__(self):
        return self.descripcion


class Direccion(models.Model):
    dsc = models.CharField(max_length=100, null=True, blank=True)
    depid = models.ForeignKey(
        'self', models.SET_NULL, null=True, blank=True,
        db_column='depid',
        related_name='subdivisiones')
    tipo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = '"clinica"."direccion"'
        verbose_name_plural = 'Direcciones'

    def __str__(self):
        return self.dsc


class Etnia(models.Model):
    tipo_etnia = models.CharField(max_length=10)

    class Meta:
        db_table = '"clinica"."etnia"'

    def __str__(self):
        return self.tipo_etnia


class Sangre(models.Model):
    tipo_sangre = models.CharField(max_length=20)

    class Meta:
        db_table = '"clinica"."sangre"'

    def __str__(self):
        return self.tipo_sangre


class Discapacidad(models.Model):
    tipo_discapacidad = models.CharField(max_length=50)

    class Meta:
        db_table = '"clinica"."discapacidad"'
        verbose_name_plural = 'Discapacidades'

    def __str__(self):
        return self.tipo_discapacidad


class Especialidad(models.Model):
    descripcion = models.CharField(max_length=30)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = '"clinica"."especialidad"'
        verbose_name_plural = 'Especialidades'

    def __str__(self):
        return self.descripcion


class Persona(models.Model):
    nombre = models.ForeignKey(Nombres, models.PROTECT, db_column='nombre_id',
                               related_name='+')
    apellido = models.ForeignKey(Nombres, models.PROTECT, db_column='apellido_id',
                                 related_name='+')
    fecha_nacimiento = models.DateField()
    direccion = models.ForeignKey(Direccion, models.PROTECT, db_column='direccion_id')
    sexo = models.CharField(max_length=1, choices=Sexo.choices, null=True, blank=True)
    etnia = models.ForeignKey(Etnia, models.SET_NULL, null=True, blank=True,
                              db_column='etnia_id')
    sangre = models.ForeignKey(Sangre, models.SET_NULL, null=True, blank=True,
                               db_column='sangre_id')
    discapacidad = models.ForeignKey(Discapacidad, models.SET_NULL, null=True,
                                     blank=True, db_column='discapacidad_id')
    telefono = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = '"clinica"."persona"'
        verbose_name_plural = 'Personas'

    def __str__(self):
        return f'{self.nombre} {self.apellido}'


class Identificacion(models.Model):
    persona = models.ForeignKey(Persona, models.CASCADE, db_column='persona_id',
                                related_name='identificaciones',
                                null=True, blank=True)
    dsc = models.CharField(max_length=50, null=True, blank=True)
    depid = models.ForeignKey(
        'self', models.SET_NULL, null=True, blank=True,
        db_column='depid', related_name='subtipos')
    tipo = models.IntegerField(null=True, blank=True)
    valor = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = '"clinica"."identificacion"'
        verbose_name_plural = 'Identificaciones'

    def __str__(self):
        return f'{self.dsc}: {self.valor}'


class Medico(models.Model):
    persona = models.ForeignKey(Persona, models.CASCADE, db_column='persona_id')
    especialidad = models.ForeignKey(Especialidad, models.RESTRICT,
                                     db_column='especialidad_id')
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = '"clinica"."medico"'
        verbose_name = 'Médico'
        verbose_name_plural = 'Médicos'

    def __str__(self):
        return f'Dr(a). {self.persona} - {self.especialidad}'


class Paciente(models.Model):
    persona = models.ForeignKey(Persona, models.DO_NOTHING, db_column='persona_id')

    class Meta:
        db_table = '"clinica"."paciente"'
        verbose_name_plural = 'Pacientes'

    def __str__(self):
        return str(self.persona)

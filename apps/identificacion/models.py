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
    """Jerarquía: Estado -> Municipio -> Parroquia -> Calle/Sector.

    Estructura de ancla:
      * id 0 = NINGUNO (nunca se edita ni se borra)
      * tipo: 1=Estado, 2=Municipio, 3=Parroquia, 4=Calle/Sector
      * divicion_politica_id apunta SIEMPRE a una fila: 0 si es raíz
    """
    division_politica = models.CharField(max_length=50, default='')
    valor = models.CharField(max_length=100)
    tipo = models.IntegerField(default=0)
    divicion_politica_id = models.IntegerField(default=0)

    class Meta:
        db_table = '"clinica"."direccion"'
        verbose_name_plural = 'Direcciones'

    def __str__(self):
        return self.valor or ''

    def padre(self):
        if self.divicion_politica_id:
            return Direccion.objects.filter(pk=self.divicion_politica_id).first()
        return None

    def hijos(self):
        return Direccion.objects.filter(
            divicion_politica_id=self.id).order_by('valor')

    def ruta(self):
        """Estado › Municipio › Parroquia › Sector"""
        partes, actual, vistos = [], self, set()
        while actual and actual.id not in vistos:
            vistos.add(actual.id)
            if actual.id:
                partes.append(actual.valor)
            actual = (Direccion.objects.filter(id=actual.divicion_politica_id).first()
                      if actual.divicion_politica_id else None)
        return ' › '.join(reversed(partes)) or 'Sin dirección'


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
    discapacidad = models.CharField(max_length=40)

    class Meta:
        db_table = '"clinica"."discapacidad"'
        verbose_name_plural = 'Discapacidades'

    def __str__(self):
        return self.discapacidad


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
    sexo = models.CharField(max_length=1, choices=Sexo.choices, default=Sexo.OTRO)
    etnia = models.ForeignKey(Etnia, models.PROTECT, db_column='etnia_id')
    sangre = models.ForeignKey(Sangre, models.PROTECT, db_column='sangre_id')
    discapacidad = models.ForeignKey(Discapacidad, models.PROTECT,
                                     db_column='discapacidad_id')
    # persona.telefono: varchar(20) NULL  (agregado al esquema)
    telefono = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = '"clinica"."persona"'
        verbose_name_plural = 'Personas'

    def __str__(self):
        return f'{self.nombre} {self.apellido}'


class Identificacion(models.Model):
    """Tipos de documento (Cédula, Pasaporte...) y sus subtipos.

    Estructura de ancla:
      * id 0 = NINGUNO
      * tipo: 1=Documento (catálogo), 2=Subtipo
      * descripcion_id apunta SIEMPRE a una fila: 0 si es raíz
    """
    persona = models.ForeignKey(Persona, models.CASCADE, db_column='persona_id',
                                related_name='identificaciones')
    descripcion = models.CharField(max_length=50)
    descripcion_id = models.IntegerField(default=0)
    valor = models.CharField(max_length=100)
    tipo = models.IntegerField(default=0)

    class Meta:
        db_table = '"clinica"."identificacion"'
        verbose_name_plural = 'Identificaciones'

    def __str__(self):
        return f'{self.descripcion}: {self.valor}'

    def padre(self):
        if self.descripcion_id:
            return Identificacion.objects.filter(pk=self.descripcion_id).first()
        return None

    def subtipos(self):
        return Identificacion.objects.filter(descripcion_id=self.id).order_by('id')


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

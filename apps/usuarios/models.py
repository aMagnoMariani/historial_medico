from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.identificacion.models import Persona


class Permiso(models.Model):
    codigo = models.CharField(max_length=50, unique=True,
                              help_text='Ej: citas.crear, citas.editar')
    descripcion = models.CharField(max_length=100)

    class Meta:
        db_table = '"clinica"."permiso"'

    def __str__(self):
        return f'{self.codigo} - {self.descripcion}'


class Rol(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=100, blank=True)
    permisos = models.ManyToManyField(Permiso, through='RolPermiso',
                                      related_name='roles')
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = '"clinica"."rol"'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre


class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, models.CASCADE, db_column='rol_id')
    permiso = models.ForeignKey(Permiso, models.CASCADE, db_column='permiso_id')

    class Meta:
        db_table = '"clinica"."rol_permiso"'
        unique_together = ('rol', 'permiso')

    def __str__(self):
        return f'{self.rol} -> {self.permiso}'


class UsuarioManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('El username es obligatorio')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


class Usuario(AbstractUser):
    persona = models.ForeignKey(Persona, models.SET_NULL, null=True, blank=True,
                                db_column='persona_id')
    rol = models.ForeignKey(Rol, models.PROTECT, db_column='rol_id',
                            null=True, blank=True)

    objects = UsuarioManager()

    class Meta:
        db_table = '"clinica"."usuario"'

    def tiene_permiso(self, codigo):
        if self.is_superuser:
            return True
        if not self.rol:
            return False
        return self.rol.permisos.filter(codigo=codigo).exists()

    def __str__(self):
        return f'{self.username} ({self.rol})'

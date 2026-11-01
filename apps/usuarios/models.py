from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.identificacion.models import Persona


class Permiso(models.Model):
    """Permiso del sistema, organizado por módulo y acción.

    El código es 'modulo.accion', por ejemplo 'pacientes.ver'.
    """
    codigo = models.CharField(max_length=60, unique=True)
    modulo = models.CharField(max_length=40, db_index=True, default='', blank=True)
    accion = models.CharField(max_length=20, db_index=True, default='', blank=True)
    descripcion = models.CharField(max_length=120, blank=True, default='')

    class Meta:
        db_table = '"clinica"."permiso"'
        ordering = ['modulo', 'accion']

    def __str__(self):
        return self.codigo


class Rol(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=150, blank=True)
    permisos = models.ManyToManyField(Permiso, through='RolPermiso',
                                      related_name='roles')
    estado = models.BooleanField(default=True)
    # Los roles predefinidos no se pueden eliminar
    predefinido = models.BooleanField(default=False)

    class Meta:
        db_table = '"clinica"."rol"'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre

    def codigos_permisos(self):
        return set(self.permisos.values_list('codigo', flat=True))


class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, models.CASCADE, db_column='rol_id')
    permiso = models.ForeignKey(Permiso, models.CASCADE, db_column='permiso_id')

    class Meta:
        db_table = '"clinica"."rol_permiso"'
        unique_together = ('rol', 'permiso')

    def __str__(self):
        return f'{self.rol} -> {self.permiso}'


class UsuarioPermiso(models.Model):
    """Permisos propios del usuario.

    Al crear un usuario se copian los permisos de su rol; después se pueden
    ajustar uno por uno (por eso el permiso efectivo es el del usuario).
    """
    usuario = models.ForeignKey('Usuario', models.CASCADE,
                                db_column='usuario_id', related_name='permisos_propios')
    permiso = models.ForeignKey(Permiso, models.CASCADE, db_column='permiso_id')

    class Meta:
        db_table = '"clinica"."usuario_permiso"'
        unique_together = ('usuario', 'permiso')

    def __str__(self):
        return f'{self.usuario} -> {self.permiso}'


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
        return self.create_user(username, password=password, **extra_fields)


class Usuario(AbstractUser):
    persona = models.ForeignKey(Persona, models.SET_NULL, null=True, blank=True,
                                db_column='persona_id')
    rol = models.ForeignKey(Rol, models.PROTECT, db_column='rol_id',
                            null=True, blank=True)
    permisos = models.ManyToManyField(Permiso, through='UsuarioPermiso',
                                      related_name='usuarios')

    objects = UsuarioManager()

    class Meta:
        db_table = '"clinica"."usuario"'

    # -----------------------------------------------------------------
    #  Tríada usuario → rol → permiso
    # -----------------------------------------------------------------
    def codigos_permisos(self):
        """Códigos de permiso efectivos del usuario.

        El superusuario de Django siempre tiene todo. El resto usa sus
        permisos propios, que se copian del rol al crearlo.
        """
        if self.is_superuser:
            from .modulos import todos_los_permisos
            return {c for c, _, _, _ in todos_los_permisos()}
        return set(self.permisos.values_list('codigo', flat=True))

    def tiene_permiso(self, codigo):
        if self.is_superuser:
            return True
        return codigo in self.codigos_permisos()

    def puede_eliminar(self):
        """Solo el administrador puede eliminar."""
        if self.is_superuser:
            return True
        return any(c.endswith('.eliminar') for c in self.codigos_permisos())

    def es_admin(self):
        if self.is_superuser:
            return True
        return bool(self.rol and self.rol.nombre.lower() == 'superadmin')

    def __str__(self):
        return f'{self.username} ({self.rol})'

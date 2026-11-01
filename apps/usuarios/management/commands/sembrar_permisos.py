"""Crea los permisos por módulo y los roles predefinidos del sistema.

Uso:
    python manage.py sembrar_permisos

Es idempotente: se puede ejecutar todas las veces que haga falta.
"""
from django.core.management.base import BaseCommand

from apps.usuarios.modulos import sembrar_permisos_y_roles, MODULOS, todos_los_permisos


class Command(BaseCommand):
    help = 'Siembra los permisos por módulo y los roles predefinidos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Módulos definidos: {len(MODULOS)}'))
        self.stdout.write(f'Permisos definidos: {len(todos_los_permisos())}')

        creados_p, creados_r = sembrar_permisos_y_roles()

        self.stdout.write(self.style.SUCCESS(
            f'Permisos creados: {creados_p} | Roles creados: {creados_r}'))
        self.stdout.write(self.style.SUCCESS(
            'Listo. Los permisos de eliminar solo los tiene el administrador.'))

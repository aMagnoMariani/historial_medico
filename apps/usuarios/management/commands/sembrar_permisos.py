"""Crea los permisos por módulo, los roles predefinidos y las filas ancla.

Uso:
    python manage.py sembrar_permisos

Es idempotente: se puede ejecutar todas las veces que haga falta.
"""

from django.core.management.base import BaseCommand

from apps.usuarios.modulos import sembrar_permisos_y_roles, MODULOS, todos_los_permisos
from apps import catalog


class Command(BaseCommand):
    help = 'Siembra permisos, roles y filas estructurales (anclas)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Módulos definidos: {len(MODULOS)}'))
        self.stdout.write(f'Permisos definidos: {len(todos_los_permisos())}')

        creados_p, creados_r = sembrar_permisos_y_roles()
        self.stdout.write(self.style.SUCCESS(
            f'Permisos creados: {creados_p} | Roles creados: {creados_r}'))

        # --- Filas estructurales que el sistema necesita para funcionar ---
        diag = catalog.diagnostico_comodin()      # persona/cita/consulta/diag/conducta
        self.stdout.write(self.style.SUCCESS(
            f'Diagnóstico del catálogo: id={diag.id} (descr={diag.descr!r})'))

        # Anclas de los árboles (id 0 = NINGUNO). enfermedad y sintomas cuelgan
        # del diagnóstico comodín; el resto se crean sueltas.
        from apps.diagnostico.models import Enfermedad, Sintomas
        from apps.identificacion.models import Direccion, Identificacion
        from apps.antecedentes.models import AntecedentesSalud

        creadas = 0
        if not Direccion.objects.filter(id=0).exists():
            Direccion.objects.create(id=0, division_politica='NINGUNO',
                                     valor='NINGUNO', tipo=0,
                                     divicion_politica_id=0)
            creadas += 1
        if not Identificacion.objects.filter(id=0).exists():
            Identificacion.objects.create(id=0, descripcion='NINGUNO',
                                          descripcion_id=0, valor='TIPO',
                                          tipo=0, persona=None)
            creadas += 1
        if not Enfermedad.objects.filter(id=0).exists():
            Enfermedad.objects.create(id=0, desc=['NINGUNO'], valor='NINGUNO',
                                      enfermedad_id=0, tipo=0,
                                      diagnostico=diag)
            creadas += 1
        if not Sintomas.objects.filter(id=0).exists():
            Sintomas.objects.create(id=0, desc='NINGUNO', depende=0, tipo=0,
                                    diagnostico=diag)
            creadas += 1
        if not AntecedentesSalud.objects.filter(id=0).exists():
            pac = catalog.persona_catalogo()
            from apps.identificacion.models import Paciente
            paciente, _ = Paciente.objects.get_or_create(persona=pac)
            AntecedentesSalud.objects.create(id=0, descrip='NINGUNO',
                                             antecedente_salud_id=0,
                                             valor='NINGUNO', tipo=0,
                                             paciente=paciente)
            creadas += 1
        self.stdout.write(self.style.SUCCESS(
            f'Filas ancla NINGUNO creadas ahora: {creadas} '
            f'(total en BD: {Direccion.objects.filter(id=0).count() + Identificacion.objects.filter(id=0).count() + Enfermedad.objects.filter(id=0).count() + Sintomas.objects.filter(id=0).count() + AntecedentesSalud.objects.filter(id=0).count()})'))

        self.stdout.write(self.style.SUCCESS(
            'Listo. Los permisos de eliminar solo los tiene el administrador.'))

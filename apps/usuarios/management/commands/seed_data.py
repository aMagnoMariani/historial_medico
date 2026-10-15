from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.usuarios.models import Rol, Permiso, RolPermiso
from apps.identificacion.models import Persona, Nombres, Direccion, Especialidad, Medico, Paciente
from apps.citas.models import Cita
from django.utils import timezone
import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea el usuario admin, roles, permisos y datos de prueba'

    def handle(self, *args, **options):
        self.stdout.write("Sembrando datos...")

        # 1. Crear Permisos
        permisos_dict = {
            'pacientes.ver': 'Ver lista y detalle de pacientes',
            'pacientes.editar': 'Crear y editar pacientes',
            'citas.gestionar': 'Gestionar citas médicas',
            'estadistica.ver': 'Acceder al panel de estadísticas',
        }
        perm_objs = {}
        for codigo, desc in permisos_dict.items():
            p, _ = Permiso.objects.get_or_create(codigo=codigo, defaults={'descripcion': desc})
            perm_objs[codigo] = p

        # 2. Crear Rol SuperAdmin
        rol_admin, _ = Rol.objects.get_or_create(nombre='SuperAdmin', defaults={'descripcion': 'Acceso total'})
        for p in perm_objs.values():
            RolPermiso.objects.get_or_create(rol=rol_admin, permiso=p)

        # 3. Crear Usuario admin/admin
        if not User.objects.filter(username='admin').exists():
            # USAR kwargs para evitar el TypeError del Manager
            admin_user = User.objects.create_superuser(
                username='admin', 
                password='admin', 
                email='admin@clinica.com'
            )
            admin_user.rol = rol_admin
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Usuario admin creado con éxito"))
        else:
            self.stdout.write("El usuario admin ya existe")

        # 4. Datos de prueba básicos
        dir_casa, _ = Direccion.objects.get_or_create(division_politica='Ciudad', valor='Calle Falsa 123')
        
        n1, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion='Juan')
        a1, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion='Pérez')
        n2, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion='María')
        a2, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion='García')
        
        esp_gen, _ = Especialidad.objects.get_or_create(descripcion='Medicina General')
        esp_ped, _ = Especialidad.objects.get_or_create(descripcion='Pediatría')

        p_med, _ = Persona.objects.get_or_create(
            nombre=n1, apellido=a1, fecha_nacimiento='1980-01-01', direccion=dir_casa, sexo='M'
        )
        medico, _ = Medico.objects.get_or_create(persona=p_med, especialidad=esp_gen)

        p_pac, _ = Persona.objects.get_or_create(
            nombre=n2, apellido=a2, fecha_nacimiento='1995-05-10', direccion=dir_casa, sexo='F'
        )
        paciente, _ = Paciente.objects.get_or_create(persona=p_pac)

        Cita.objects.get_or_create(
            medico=medico, paciente=paciente, 
            fecha_atencion=datetime.date.today(), 
            fecha_creacion=datetime.time(10, 0), 
            estado_cita_id=1
        )

        self.stdout.write(self.style.SUCCESS("Datos de prueba creados con éxito"))

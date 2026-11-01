"""Helpers para garantizar que nunca se inserten NULL en columnas NOT NULL.

El esquema SQL exige NOT NULL en:
  persona: direccion_id, sexo, etnia_id, sangre_id, discapacidad_id
  identificacion: persona_id, descripcion, valor
  antecedentes_salud: descrip, antecedente_salud_id, valor, paciente_id
  direccion: division_politica, valor
"""

import datetime

from apps.identificacion.models import (
    Nombres, Direccion, Etnia, Sangre, Discapacidad, Persona, Identificacion,
    Especialidad, Medico, Paciente,
)
from apps.citas.models import Cita
from apps.diagnostico.models import Consulta, Diagnostico, Conducta

# Tipos de antecedente (se guardan en antecedentes_salud.descrip, varchar(20))
TIPOS_ANTECEDENTE = [
    ('Antecedente Personal', 'Antecedente Personal'),
    ('Antecedente Familiar', 'Antecedente Familiar'),
]


# =====================================================================
#  NIVELES DE LAS TABLAS AUTORREFERENCIADAS
# =====================================================================
#  Regla para todas: id 0 es la fila ancla NINGUNO (nunca se edita ni se
#  borra), el campo del padre apunta SIEMPRE a una fila (0 si es raíz) y
#  `tipo` indica el nivel: 1 = raíz del árbol.
#
#  Ejemplo de direccion:
#     0  NINGUNO     0  0   <- ancla
#     1  MONAGAS     0  1   <- Estado
#     2  MATURIN     1  2   <- Municipio
#     3  PALO NEGRO  2  3   <- Parroquia
# =====================================================================

ANCLA_ID = 0
ANCLA_NOMBRE = 'NINGUNO'

# --- Niveles de cada tabla (valor, etiqueta) ---
TIPOS_DIRECCION = [(1, 'Estado'), (2, 'Municipio'),
                   (3, 'Parroquia'), (4, 'Calle / Sector')]

TIPOS_IDENTIFICACION = [(1, 'Documento'), (2, 'Subtipo')]

TIPOS_ENFERMEDAD = [(1, 'Categoría'), (2, 'Enfermedad')]

TIPOS_SINTOMA = [(1, 'Categoría'), (2, 'Síntoma')]

TIPOS_ANTECEDENTE = [(1, 'Categoría'), (2, 'Antecedente')]


# =====================================================================
#  VALORES POR DEFECTO (evitan dejar columnas NOT NULL vacías)
# =====================================================================

def etnia_default():
    # etnia.tipo_etnia es varchar(10)
    obj, _ = Etnia.objects.get_or_create(tipo_etnia='N/A')
    return obj.id


def sangre_default():
    # sangre.tipo_sangre es varchar(20)
    obj, _ = Sangre.objects.get_or_create(tipo_sangre='Sin especificar')
    return obj.id


def discapacidad_default():
    # discapacidad.discapacidad es varchar(40)
    obj, _ = Discapacidad.objects.get_or_create(discapacidad='Ninguna')
    return obj.id


def direccion_default():
    obj, _ = Direccion.objects.get_or_create(
        division_politica='Estado', valor='Sin especificar',
        tipo=1, divicion_politica_id=0)
    return obj.id


# =====================================================================
#  FILAS "COMODINES"
#  identificacion.persona_id y valor son NOT NULL, así que las filas de
#  catálogo usan una persona y un valor de relleno.
# =====================================================================

# Fecha centinela: identifica la cita interna (nunca se atiende)
FECHA_COMODIN = '1900-01-01'
# Marca del diagnóstico que guarda el catálogo
DESCR_CATALOGO = '__CATALOGO__'


def _nombre_comodin(descripcion):
    obj, _ = Nombres.objects.get_or_create(tipo='NOMBRE', descripcion=descripcion)
    return obj


def _apellido_comodin(descripcion):
    obj, _ = Nombres.objects.get_or_create(tipo='APELLIDO', descripcion=descripcion)
    return obj


def persona_catalogo():
    persona = Persona.objects.filter(
        nombre__descripcion='CATALOGO', apellido__descripcion='SISTEMA').first()
    if persona:
        return persona
    return Persona.objects.create(
        nombre=_nombre_comodin('CATALOGO'),
        apellido=_apellido_comodin('SISTEMA'),
        fecha_nacimiento='1900-01-01',
        direccion_id=direccion_default(),
        sexo='O',
        etnia_id=etnia_default(),
        sangre_id=sangre_default(),
        discapacidad_id=discapacidad_default(),
    )


def tipo_identificacion_default():
    persona = persona_catalogo()
    obj = Identificacion.objects.filter(
        persona=persona, descripcion='Cedula').first()
    if obj:
        return obj
    return Identificacion.objects.create(
        persona=persona, descripcion='Cedula', descripcion_id=0,
        valor='TIPO', tipo=1)


def cita_comodin():
    obj = Cita.objects.filter(fecha_atencion=FECHA_COMODIN).first()
    if obj:
        return obj
    persona = persona_catalogo()
    paciente, _ = Paciente.objects.get_or_create(persona=persona)
    especialidad, _ = Especialidad.objects.get_or_create(
        descripcion='Sin especificar', defaults={'estado': True})
    medico, _ = Medico.objects.get_or_create(
        persona=persona, especialidad=especialidad, defaults={'estado': True})
    return Cita.objects.create(
        medico=medico,
        paciente=paciente,
        fecha_atencion=FECHA_COMODIN,
        fecha_creacion=datetime.time(0, 0),
        estado_cita_id=1,
        tipo_cita='RUTINA',
    )


def consulta_comodin():
    cita = cita_comodin()
    obj = Consulta.objects.filter(cita=cita).first()
    if obj:
        return obj
    return Consulta.objects.create(cita=cita, tipo_consulta=0)


def conducta_comodin():
    obj = Conducta.objects.filter(conducta=['observado']).first()
    if obj:
        return obj
    return Conducta.objects.create(conducta=['observado'])


def diagnostico_comodin():
    """Diagnóstico que almacena el catálogo de enfermedades y síntomas."""
    obj = Diagnostico.objects.filter(descr=DESCR_CATALOGO).first()
    if obj:
        return obj
    consulta = consulta_comodin()
    return Diagnostico.objects.create(
        consulta=consulta, descr=DESCR_CATALOGO, conducta=conducta_comodin())

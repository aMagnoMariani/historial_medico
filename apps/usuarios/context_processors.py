"""Context processor: expone los permisos del usuario a todas las plantillas.

Permite que el sidebar muestre solo los módulos que el usuario puede ver
y que los botones de editar/eliminar aparezcan según sus permisos.
"""


def permisos(request):
    usuario = getattr(request, 'user', None)
    codigos = set()
    if usuario is not None and usuario.is_authenticated:
        codigos = usuario.codigos_permisos()

    def puede(codigo_permiso):
        if usuario is not None and usuario.is_superuser:
            return True
        return codigo_permiso in codigos

    def puede_eliminar():
        if usuario is not None and usuario.is_superuser:
            return True
        return any(c.endswith('.eliminar') for c in codigos)

    return {
        'permisos_usuario': codigos,
        'puede': puede,
        'puede_eliminar': puede_eliminar,
        'es_admin': usuario.es_admin() if (usuario is not None
                                           and usuario.is_authenticated) else False,
    }

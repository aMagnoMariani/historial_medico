from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

# Acción del formulario -> permiso que exige
ACCIONES_PERMISO = {
    'crear': 'crear',
    'editar': 'editar',
    'activar': 'editar',
    'desactivar': 'editar',
    'eliminar': 'eliminar',
}


def sin_permiso(request, codigo_permiso):
    """Devuelve una redirección si el usuario no tiene el permiso.

    Uso dentro de un POST que hace varias acciones:
        rechazo = sin_permiso(request, 'medicos.crear')
        if rechazo:
            return rechazo
    """
    if request.user.tiene_permiso(codigo_permiso):
        return None
    messages.error(request, 'No tienes permiso para realizar esta acción.')
    return redirect('usuarios:home')


def valida_accion(request, action, modulo):
    """Valida 'action' contra el permiso 'modulo.accion'.

    Devuelve una redirección si no tiene permiso, o None si puede seguir.
    """
    accion = ACCIONES_PERMISO.get(action)
    if not accion:
        return None
    return sin_permiso(request, f'{modulo}.{accion}')


def permiso_requerido(codigo_permiso):
    """Restringe el acceso a una vista según el permiso del usuario.

    El permiso es 'modulo.accion' (ej: 'pacientes.ver').
    Si el usuario no lo tiene, se le muestra un mensaje y vuelve al inicio.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')

            if request.user.tiene_permiso(codigo_permiso):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'No tienes permiso para acceder a esta sección.')
            return redirect('usuarios:home')
        return _wrapped_view
    return decorator

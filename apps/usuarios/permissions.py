from django.core.exceptions import PermissionDenied
from functools import wraps

def permiso_requerido(codigo_permiso):
    """
    Decorador para restringir el acceso a vistas basado en la tríada Rol-Permiso.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')
            
            if request.user.tiene_permiso(codigo_permiso):
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied("No tienes el permiso necesario: " + codigo_permiso)
        return _wrapped_view
    return decorator

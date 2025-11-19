from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(*allowed_roles):
    """
    Decorador que restringe el acceso a vistas según el rol del usuario.
    
    Uso:
        @role_required(User.Roles.ADMIN_BARBERIA, User.Roles.SUPERADMIN)
        def mi_vista(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Debes iniciar sesión.")
                return redirect("login")
            
            if request.user.rol not in allowed_roles:
                messages.error(request, "No tienes permisos para acceder a esta página.")
                return redirect("route_by_role")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

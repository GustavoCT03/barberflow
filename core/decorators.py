from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from core.models import Perfil

def rol_requerido(rol):
    def _decorator(view_func):
        @wraps(view_func):
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.perfil.rol != rol:
                messages.error(request, "No tienes permisos para esta seccion.")
                return redirect("route_by_role")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return _decorator

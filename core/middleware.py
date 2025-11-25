# core/middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve

from django.contrib.auth import get_user_model
from core.models import Nosotros, Barbero, Licencia

User = get_user_model()


def get_nosotros_for_user(user):
    """
    Resuelve la 'barbería/Nosotros' asociada al usuario.

    - BARBERO: usa barbero.nosotros (ya existe en el modelo Barbero)
    - ADMIN_BARBERIA: intenta inferirla por el nombre (bootstrap crea
      'Admin {nos.nombre}') y, si no, toma la primera.
    - Otros roles: None
    """
    if not user.is_authenticated:
        return None

    # Caso barbero (ya estaba bien modelado)
    if user.rol == User.Roles.BARBERO and hasattr(user, "barbero"):
        return user.barbero.nosotros

    # Caso admin de barbería
    if user.rol == User.Roles.ADMIN_BARBERIA:
        qs = Nosotros.objects.all()
        # Heurística: en bootstrap el admin se crea como "Admin {nos.nombre}"
        for nos in qs:
            if nos.nombre in user.nombre:
                return nos
        # Si no matchea por nombre, al menos devolvemos el primero
        return qs.first()

    return None


class PlanRequiredMiddleware(MiddlewareMixin):
    """
    HU30: Middleware que bloquea el acceso a paneles y gestión
    si la licencia del tenant (Nosotros) está vencida o inactiva.

    Reglas:
    - Solo se aplica a usuarios ADMIN_BARBERIA y BARBERO.
    - Ignora:
      * /admin/
      * /accounts/
      * /static/, /media/
      * /bootstrap (para inicializar datos)
    - Solo protege URLs de panel/gestión (prefijos definidos).
    """

    PROTECTED_PREFIXES = (
        "/panel/",
        "/reservas/",
        "/scheduling/",
        "/servicios/",
    )

    EXCLUDED_PREFIXES = (
        "/admin/",
        "/accounts/",
        "/static/",
        "/media/",
        "/bootstrap",
    )

    def process_request(self, request):
        path = request.path

        # 1) Rutas excluidas
        for pref in self.EXCLUDED_PREFIXES:
            if path.startswith(pref):
                return None  # dejar pasar

        user = request.user

        # 2) Solo aplica a admin de barbería y barbero logueados
        if not user.is_authenticated:
            return None

        if user.rol not in (User.Roles.ADMIN_BARBERIA, User.Roles.BARBERO):
            return None

        # 3) Solo aplica a rutas 'de trabajo'
        if not any(path.startswith(pref) for pref in self.PROTECTED_PREFIXES):
            return None

        # 4) Resolver tenant (Nosotros)
        nosotros = get_nosotros_for_user(user)
        if not nosotros:
            # Si no hay barbería asociada, dejamos pasar pero mostramos aviso suave
            messages.warning(
                request,
                "Tu usuario aún no está asociado a una barbería correctamente. "
                "Contacta al administrador del sistema."
            )
            return None

        # 5) Verificar licencia
        licencia = getattr(nosotros, "licencia", None)
        if not licencia:
            messages.error(
                request,
                "Tu barbería no tiene una licencia activa asignada. "
                "Contacta al administrador del sistema."
            )
            # Lo mandamos al home o a la ruta por rol
            try:
                return redirect("route_by_role")
            except Exception:
                return redirect("home")

        if not licencia.esta_activa():
            messages.error(
                request,
                "La licencia de tu barbería está vencida o inactiva. "
                "Renueva tu plan para seguir usando BarberFlow."
            )
            try:
                return redirect("route_by_role")
            except Exception:
                return redirect("home")

        # 6) Si todo OK, continuar
        return None

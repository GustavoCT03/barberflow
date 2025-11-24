from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.models import Servicio, User
from core.decorators import role_required
from .forms_servicios import ServicioForm


def get_nosotros_from_user(user):
    """Helper para obtener la barbería del usuario admin"""
    if hasattr(user, "barbero") and getattr(user.barbero, "nosotros", None):
        return user.barbero.nosotros
    return None


# ============================================================
# LISTAR SERVICIOS (HU02)
# ============================================================
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def servicio_list(request):
    """
    Lista todos los servicios de la barbería del admin.
    """
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    servicios = Servicio.objects.filter(barberia__nosotros=nosotros).order_by("-activo", "nombre")
    
    context = {
        "servicios": servicios,
        "nosotros": nosotros,
    }
    return render(request, "dashboard/servicio_list.html", context)


# ============================================================
# CREAR SERVICIO (HU02)
# ============================================================
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def servicio_crear(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    form = ServicioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        servicio = form.save(commit=False)
        # Asigna la barbería correctamente
        servicio.barberia = nosotros.barberias.first()  # O ajusta según tu modelo
        servicio.save()
        messages.success(request, f"Servicio '{servicio.nombre}' creado con éxito.")
        return redirect("servicio_list")

    context = {
        "form": form,
        "modo": "crear",
        "titulo": "Crear Nuevo Servicio",
    }
    return render(request, "dashboard/servicio_form.html", context)


# ============================================================
# EDITAR SERVICIO (HU02)
# ============================================================
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def servicio_editar(request, servicio_id):
    """
    Edita un servicio existente.
    """
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    servicio = get_object_or_404(Servicio, id=servicio_id, barberia__nosotros=nosotros)
    form = ServicioForm(request.POST or None, instance=servicio)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Servicio '{servicio.nombre}' actualizado con éxito.")
        return redirect("servicio_list")

    context = {
        "form": form,
        "modo": "editar",
        "titulo": f"Editar Servicio: {servicio.nombre}",
        "servicio": servicio,
    }
    return render(request, "dashboard/servicio_form.html", context)


# ============================================================
# ELIMINAR SERVICIO (HU02)
# ============================================================
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def servicio_eliminar(request, servicio_id):
    """
    Elimina un servicio (confirmación requerida).
    """
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    servicio = get_object_or_404(Servicio, id=servicio_id, barberia__nosotros=nosotros)
    
    if request.method == "POST":
        nombre = servicio.nombre
        servicio.delete()
        messages.success(request, f"Servicio '{nombre}' eliminado con éxito.")
        return redirect("servicio_list")

    context = {
        "servicio": servicio,
    }
    return render(request, "dashboard/servicio_confirm_delete.html", context)


# ============================================================
# ACTIVAR/DESACTIVAR SERVICIO (HU02)
# ============================================================
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def servicio_toggle_activo(request, servicio_id):
    """
    Activa o desactiva un servicio sin eliminarlo.
    """
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    servicio = get_object_or_404(Servicio, id=servicio_id, barberia__nosotros=nosotros)
    servicio.activo = not servicio.activo
    servicio.save()
    
    estado = "activado" if servicio.activo else "desactivado"
    messages.success(request, f"Servicio '{servicio.nombre}' {estado} con éxito.")
    return redirect("servicio_list")
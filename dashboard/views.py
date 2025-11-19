from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from core.models import (
    Nosotros,
    Sucursal,
    InvitacionBarbero,
    User,
    Barbero,
)
from core.decorators import role_required
from .forms import SucursalCreateForm, SucursalUpdateForm


# Helper: obtener la barbería (Nosotros) asociada al usuario
def get_nosotros_from_user(user):
    if hasattr(user, "barbero") and getattr(user.barbero, "nosotros", None):
        return user.barbero.nosotros
    return None


# Helpers de licencia
def _licencia_activa(licencia):
    try:
        return licencia.esta_activa()
    except Exception:
        exp = getattr(licencia, "fecha_expiracion", None)
        activa_flag = getattr(licencia, "activa", True)
        return bool(activa_flag and (exp is None or exp >= timezone.now()))


def _puede_agregar_sucursal(nosotros, licencia):
    try:
        return licencia.puede_agregar_sucursal(nosotros)
    except Exception:
        max_s = getattr(licencia, "max_sucursales", None)
        if max_s is None:
            return True
        return Sucursal.objects.filter(nosotros=nosotros).count() < max_s


def _puede_agregar_barbero(nosotros, licencia):
    try:
        return licencia.puede_agregar_barbero(nosotros)
    except Exception:
        max_b = getattr(licencia, "max_barberos", None)
        if max_b is None:
            return True
        return Barbero.objects.filter(nosotros=nosotros, activo=True).count() < max_b


# Superadmin: panel de licencias
@login_required
@role_required(User.Roles.SUPERADMIN)
def panel_licencias(request):
    return render(request, "dashboard/panel_licencias.html")


# Admin de barbería: panel principal
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def panel_admin_barberia(request):
    return render(request, "dashboard/admin_sucursal.html")


# Crear sucursal (Admin de barbería) con validación de licencia
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def sucursal_crear(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    licencia = getattr(nosotros, "licencia", None)
    if not licencia:
        messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
        return redirect("panel_admin_barberia")
    if not _licencia_activa(licencia):
        messages.error(request, "Tu licencia está vencida. Renueva para crear sucursales.")
        return redirect("panel_admin_barberia")
    if not _puede_agregar_sucursal(nosotros, licencia):
        max_s = getattr(licencia, "max_sucursales", 0)
        messages.error(request, f"Límite de sucursales alcanzado ({max_s}) para tu plan.")
        return redirect("panel_admin_barberia")

    form = SucursalCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        suc = form.save(commit=False)
        suc.nosotros = nosotros
        suc.save()
        messages.success(request, "Sucursal creada con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/sucursal_form.html", {"form": form, "modo": "crear"})


# Editar sucursal (Admin de barbería)
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def sucursal_editar(request, sucursal_id):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    suc = get_object_or_404(Sucursal, id=sucursal_id, nosotros=nosotros)
    form = SucursalUpdateForm(request.POST or None, instance=suc)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sucursal actualizada con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/sucursal_form.html", {"form": form, "modo": "editar", "sucursal": suc})


# Eliminar sucursal (Admin de barbería)
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def sucursal_eliminar(request, sucursal_id):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    suc = get_object_or_404(Sucursal, id=sucursal_id, nosotros=nosotros)
    if request.method == "POST":
        suc.delete()
        messages.success(request, "Sucursal eliminada con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/sucursal_confirm_delete.html", {"sucursal": suc})


# Crear invitación para barbero (Admin de barbería) con validación de licencia y límites
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def crear_invitacion_barbero(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    licencia = getattr(nosotros, "licencia", None)
    if not licencia:
        messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
        return redirect("panel_admin_barberia")
    if not _licencia_activa(licencia):
        messages.error(request, "Tu licencia está vencida. Renueva para invitar barberos.")
        return redirect("panel_admin_barberia")
    if not _puede_agregar_barbero(nosotros, licencia):
        max_b = getattr(licencia, "max_barberos", 0)
        messages.error(request, f"Límite de barberos alcanzado ({max_b}) para tu plan.")
        return redirect("panel_admin_barberia")

    if request.method == "POST":
        email = request.POST.get("email")
        sucursal_id = request.POST.get("sucursal_id")
        sucursal = Sucursal.objects.filter(id=sucursal_id, nosotros=nosotros).first()

        if User.objects.filter(email=email).exists():
            messages.error(request, "Ya existe un usuario con ese email.")
            return redirect("panel_admin_barberia")

        inv = InvitacionBarbero.objects.create(
            nosotros=nosotros,
            sucursal=sucursal,
            email=email
        )
        messages.success(request, f"Invitación generada con éxito. Enlace: /registro/barbero/{inv.token}/")
        return redirect("panel_admin_barberia")

    sucursales = Sucursal.objects.filter(nosotros=nosotros, activo=True)
    return render(request, "dashboard/invitaciones_form.html", {"sucursales": sucursales})


# Crear barbero directamente (Admin de barbería) con validación de licencia y límites
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def barbero_crear(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    licencia = getattr(nosotros, "licencia", None)
    if not licencia:
        messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
        return redirect("panel_admin_barberia")
    if not _licencia_activa(licencia):
        messages.error(request, "Tu licencia está vencida. Renueva para crear barberos.")
        return redirect("panel_admin_barberia")
    if not _puede_agregar_barbero(nosotros, licencia):
        max_b = getattr(licencia, "max_barberos", 0)
        messages.error(request, f"Límite de barberos alcanzado ({max_b}) para tu plan.")
        return redirect("panel_admin_barberia")

    if request.method == "POST":
        email = request.POST.get("email")
        nombre = request.POST.get("nombre")
        password = request.POST.get("password") or User.objects.make_random_password()

        if not email or not nombre:
            messages.error(request, "Nombre y email son obligatorios.")
            return redirect("panel_admin_barberia")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Ya existe un usuario con ese email.")
            return redirect("panel_admin_barberia")

        user = User.objects.create_user(
            email=email,
            password=password,
            nombre=nombre,
            rol=User.Roles.BARBERO
        )
        Barbero.objects.create(
            user=user,
            nosotros=nosotros,
            nombre=nombre,
            activo=True
        )
        messages.success(request, f"Barbero '{nombre}' creado con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/barbero_form.html")


# Activar/desactivar barbero (Admin de barbería) con validación al activar
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def barbero_toggle_activo(request, barbero_id):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    barbero = get_object_or_404(Barbero, id=barbero_id, nosotros=nosotros)

    # Si vamos a activar, validar límites de licencia
    if not barbero.activo:
        licencia = getattr(nosotros, "licencia", None)
        if not licencia:
            messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
            return redirect("panel_admin_barberia")
        if not _licencia_activa(licencia):
            messages.error(request, "Tu licencia está vencida. Renueva para activar barberos.")
            return redirect("panel_admin_barberia")
        if not _puede_agregar_barbero(nosotros, licencia):
            max_b = getattr(licencia, "max_barberos", 0)
            messages.error(request, f"Límite de barberos alcanzado ({max_b}) para tu plan.")
            return redirect("panel_admin_barberia")

    barbero.activo = not barbero.activo
    barbero.save()
    estado = "activado" if barbero.activo else "desactivado"
    messages.success(request, f"Barbero '{barbero.nombre}' {estado} con éxito.")
    return redirect("panel_admin_barberia")


# Panel barbero
@login_required
@role_required(User.Roles.BARBERO)
def panel_barbero(request):
    return render(request, "dashboard/panel_barbero.html")


# Panel cliente
@login_required
@role_required(User.Roles.CLIENTE)
def panel_cliente(request):
    return render(request, "dashboard/panel_cliente.html")
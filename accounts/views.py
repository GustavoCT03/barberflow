from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from .forms import RegistroClienteForm, LoginForm
from core.models import  Nosotros, Cliente, Barbero, InvitacionBarbero, User


# Create your views here.

User = get_user_model()
def home(request):
    return render(request, "home.html")
def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data.get("email") or form.cleaned_data.get("username")
        user = authenticate(request, username=form.cleaned_data["email"], password=form.cleaned_data["password"])
        if user:
            login(request, user)
            request.session.set_expiry(60 * 60 * 24 * 30 if form.cleaned_data.get("remember_me") else 0)
            return redirect("route_by_role")
        messages.error(request, "Credenciales inválidas.")
    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")
def registro_cliente(request):
    form = RegistroClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Cliente.objects.get_or_create(user=user)
            login(request, user)
            request.session.set_expiry(60 + 60 * 24 * 30 if form.cleaned_data.get("remember_me") else 0)
        return redirect("route_by_role")
    return render(request, "accounts/registro_cliente.html", {"form": form})


@login_required  
def route_by_role(request):
    rol = request.user.rol
    if rol == User.Roles.SUPERADMIN:
        return redirect("panel_licencias")
    if rol == User.Roles.ADMIN_BARBERIA:
        return redirect("panel_admin_barberia")
    if rol == User.Roles.BARBERO:
        return redirect("panel_barbero")
    return redirect("panel_cliente")


from django.utils import timezone

def registro_barbero_por_token(request, token):
    inv = get_object_or_404(InvitacionBarbero, token=token)
    if not inv.valido():
        messages.error(request, "Invitación inválida o expirada.")
        return redirect("login")

    class RegistroBarberoForm(RegistroClienteForm):
        pass

    form = RegistroBarberoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            user.rol = User.Roles.BARBERO
            user.save(update_fields=["rol"])
            Barbero.objects.create(
                nosotros=inv.nosotros,
                user=user,
                nombre=user.nombre,
                sucursal_principal=inv.sucursal,
            )
            inv.usado = True
            inv.save(update_fields=["usado"])
            login(request, user)
            request.session.set_expiry(60 * 60 * 24 * 30 if form.cleaned_data.get("remember_me") else 0)
            return redirect("route_by_role")
    return render(request, "accounts/registro_barbero.html", {"form": form, "invitacion": inv})
    

    
@login_required
def post_login_router(request):
    rol = request.user.rol
    if rol == User.Roles.CLIENTE:
        return redirect("dashboard:cliente")
    if rol == User.Roles.BARBERO:
        return redirect("dashboard:barbero")
    if rol == User.Roles.ADMIN_BARBERIA:
        return redirect("dashboards:admin_sucursal")
    if rol == User.Roles.SUPERADMIN:
        return redirect("dashboard:superadmin")
    messages.error(request, "Rol de usuario no reconocido.")
    return redirect("login")
def aceptar_invitacion_barbero(request, token):
    """Barbero acepta invitación y completa registro"""
    invitacion = get_object_or_404(InvitacionBarbero, token=token)
    
    # Validar si ya fue usada o expiró
    if invitacion.usado:
        messages.error(request, "Esta invitación ya fue utilizada")
        return redirect('login')
    
    if invitacion.fecha_expiracion < timezone.now():
        messages.error(request, "Esta invitación ha expirado")
        return redirect('login')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        telefono = request.POST.get('telefono')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, "Las contraseñas no coinciden")
        else:
            # Crear usuario
            user = User.objects.create_user(
                email=invitacion.email,
                nombre=nombre,
                telefono=telefono,
                password=password,
                rol='barbero'
            )
            
            # Crear barbero
            Barbero.objects.create(
                user=user,
                barberia=invitacion.barberia,
                sucursal_principal=invitacion.sucursal,
                nombre=nombre,
                telefono=telefono
            )
            
            # Marcar invitación como usada
            invitacion.usado = True
            invitacion.save()
            
            messages.success(request, "¡Registro exitoso! Ya puedes iniciar sesión")
            return redirect('login')
    
    return render(request, 'accounts/aceptar_invitacion.html', {
        'invitacion': invitacion
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from .forms import RegistroClienteForm, LoginForm
from core.models import Perfil, Nosotros, Cliente, Barbero, InvitacionBarbero, User


# Create your views here.

User = get_user_model()

def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request, username=form.cleaned_data["username"], password=form.cleaned_data["password"])
        if user:
            login(request, user)
            if form.cleaned_data_get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            return redirect("route_by_role")
        messages.error(request, "Credenciales invalidas")
    return render(request, "accounts/login.html", {"form": form})
def logout_view(request):
    logout(request)
    return redirect("login")
def registro_cliente(request):
    form = RegistroClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            perfil = user.perfil
            perfil.rol = Perfil.Rol.Cliente
            perfil.save()
            Cliente.objects.create(user=user, nombre=f"{user.first_name} {user.last_name}".strip() or user.username)
            login(request, user)
        return redirect("route_by_role")
    return render(request, "accounts/registro_cliente.html", {"form": form})
@login_required  # Add this decorator to ensure user is authenticated
def route_by_role(request):  # Rename to match urls.py
    rol = request.user.perfil.rol
    if rol == Perfil.Rol.SUPERADMIN:  # Case is correct here
        return redirect("panel_licencias")
    if rol == Perfil.Rol.ADMIN_BARBERIA:  # Fix ROL -> Rol
        return redirect("panel_admin_barberia")
    if rol == Perfil.Rol.BARBERO:  # Fix ROL -> Rol
        return redirect("panel_barbero")
    return redirect("panel_cliente")


from django.utils import timezone

def registro_barbero_por_token(request, token):
    inv = get_object_or_404(InvitacionBarbero, token=token)
    if not inv.valido():
        messages.error(request, "Invitacion invalida o expirada.")
        return redirect("login")
    class RegistroBarberoForm(RegistroClienteForm):
        pass
    form = RegistroBarberoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            perfil = user.perfil
            perfil.rol = Perfil.Rol.BERBERO
            perfil.nosotros = inv.nosotros
            perfil.save()
            Barbero.objects.create(
                nosotros=inv.nosotros,
                user=user,
                nombre=f"{user.firstname} {user.last_name}".strip() or user.username,
                sucursal_principal=inv.sucursal
            )
            inv.usado = True
            inv.save()
            login(request, user)
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 *60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            return redirect("route_by_roule")
        return render(request, "accounts/registro_barbero.html", {"form": form, "invitacion":inv})
    

    
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

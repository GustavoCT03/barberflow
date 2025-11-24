from django.shortcuts import render, get_object_or_404, redirect
from core.decorators import role_required
from core.models import User
from core.models import Plan, Licencia, Nosotros
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import Plan, Licencia, Nosotros
from core.decorators import role_required
from core.models import User
from django.contrib import messages
from django.http import HttpResponse


@login_required
@role_required(User.Roles.SUPERADMIN)
def panel_licencias(request):
    return render(request, "licensing/panel_licencias.html")


@login_required
@role_required(User.Roles.SUPERADMIN)
def planes_list(request):
    planes = Plan.objects.all()
    return render(request, "licensing/planes_list.html", {"planes": planes})


@login_required
@role_required(User.Roles.SUPERADMIN)
def plan_crear(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        periodicidad = request.POST.get("periodicidad")
        precio = request.POST.get("precio")
        max_barberos = request.POST.get("max_barberos")
        max_sucursales = request.POST.get("max_sucursales")

        Plan.objects.create(
            nombre=nombre,
            periodicidad=periodicidad,
            precio=precio,
            max_barberos=max_barberos,
            max_sucursales=max_sucursales
        )
        messages.success(request, "Plan creado exitosamente.")
        return redirect("planes_list")

    return render(request, "licensing/plan_form.html")

@login_required
@role_required(User.Roles.SUPERADMIN)
def plan_editar(request, plan_id):
    return HttpResponse("Editar plan (pendiente)")


@login_required
@role_required(User.Roles.SUPERADMIN)
def plan_eliminar(request, plan_id):
    return HttpResponse("Eliminar plan (pendiente)")


@login_required
@role_required(User.Roles.SUPERADMIN)
def licencias_list(request):
    return HttpResponse("Listado de licencias (pendiente)")


@login_required
@role_required(User.Roles.SUPERADMIN)
def barberias_list(request):
    return HttpResponse("Listado de barberías (pendiente)")

@role_required(User.Roles.SUPERADMIN)
def panel_principal(request):
    return render(request, "superadmin/panel.html")

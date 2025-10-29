from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render
from django.contrib import messages
from django.db import transaction
from core.models import Nosotros, Sucursal, InvitacionBarbero, Perfil
from core.decorators import rol_requerido
from  .forms import SucursalCreateForm, SucursalUpdateForm

# Create your views here.
## Nosotros para poder ver las licencias y administrar ##
@login_required
@rol_requerido("superadmin")
def panel_licencias(request):
    nosotros = Nosotros.objects.all().order_by("-creado")
    return render(request, "dashboard/panel_licencias.html", {"nosotros": nosotros})

## para el administrador de lar barberia"
@login_required
@rol_requerido("admin_barberia")
def panel_admin_barberia(request):
    nosotros = request.user.perfil.nosotros
    sucursales = Sucursal.objects.filter(nosotros=nosotros).order_by("-creado")
    invitaciones = InvitacionBarbero.objetcs.filter(nosotros=nosotros).order_by("-creado")[:10]
    return render(request, "dashboard/panel_admin_barberia.html", {"sucursales": sucursales, "invitaciones": invitaciones})
@login_required
@rol_requerido("admin_barberia")
def sucursal_crear(request):
    nosotros = request.user.perfil.nosotros
    form = SucursalCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        suc = form.save(commit=False)
        suc.nosotors = nosotros
        suc.save()
        messages.success(request, "Sucursal creada con exito.")
        return redirect("panel_admin_barberia")
    return render(request, "dashboard/sucursal_form.html", {"form": form, "modo": "crear"})
@login_required
@rol_requerido("admin_barberia")
def sucursal_editar(request, sucursal_id):
    nosotros = request.user.perfil.nosotros
    suc = get_object_or_404(Sucursal, id=sucursal_id, nosotros=nosotros)
    form = SucursalUpdateForm(request.POST or None, instance=suc)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sucursal actualizado con exito.")
        return redirect("panel_admin_barberia")
    return render(request, "dashboard/sucursal_form.html", {"form": form, "modo": "editar", "sucursal": suc})
@login_required
@rol_requerido("admin_barberia")
def sucursal_eliminar(request, sucursal_id):
    nosotros = request.user.perfil.nosotros
    suc = get_object_or_404(Sucursal, id=sucursal_id, nosotros=nosotros)
    if request.method == "POST":
        suc.delete()
        messages.success(request, "Sucursal eliminada con exito.")
        return redirect("panel_admin_barberia")
    return render(request, "dashboard/sucursal_confirm_delete.html", {"sucursal": suc})

#### Gererar las invitaciones para que los barberos se regustren####
from django.utils import timezone
import uuid
@login_required
@rol_requerido("admin_barberia")
def crear_invitacion_barbero(request):
    nosotros = request.user.perfil.nosotros
    if request.method == "POST":
        email = request.POST.get("email")
        sucursal_id = request.POST.get("sucursal_id")
        sucursal = Sucursal.objects.filter(id=sucursal_id, nosotros=nosotros).first()
        inv = InvitacionBarbero.objects.create(nosotros=nosotros, sucursal=sucursal, email=email)
        messages.success(request, f"Invitacion generada con exito. Enlace: /registro/barbero/{inv.token}/")
        return redirect("panel:admin_barberia")
    sucursales = Sucursal.objects.filter(nosotros=nosotros, activo=True)
    return render(request, "dashboard/Invitaciones_form.html", {"sucursales": sucursales})

####Barbero:#######
@login_required
@rol_requerido("barbero")
def panel_barbero(request):
    return render(request, "dashboard/ánel_barbero.html")

#######Cliente##########
@login_required
@rol_requerido("cliente")
def panel_cliente(request):
    return render(request, "dashboard/panel_cliente.html")




    


               
 
                                                    


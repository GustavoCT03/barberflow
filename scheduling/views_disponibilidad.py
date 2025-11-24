from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from core.models import HorarioDisponibilidad
from .forms import HorarioDisponibilidadForm

@login_required
def disponibilidad_list(request):
    disponibilidades = HorarioDisponibilidad.objects.filter(barbero__user=request.user)
    return render(request, 'scheduling/disponibilidad_list.html', {
        'disponibilidades': disponibilidades,
    })

@login_required
def disponibilidad_create(request):
    if request.method == 'POST':
        form = HorarioDisponibilidadForm(request.POST)
        if form.is_valid():
            disponibilidad = form.save(commit=False)
            disponibilidad.barbero = request.user.barbero
            # Validar solapamiento
            solapado = HorarioDisponibilidad.objects.filter(
                barbero=disponibilidad.barbero,
                dia_semana=disponibilidad.dia_semana,
                hora_inicio__lt=disponibilidad.hora_fin,
                hora_fin__gt=disponibilidad.hora_inicio,
            ).exists()
            if solapado:
                messages.error(request, "Ya existe una franja solapada para ese día.")
            else:
                disponibilidad.save()
                messages.success(request, "Disponibilidad creada correctamente.")
                return redirect('scheduling_disponibilidad:disponibilidad_list')
    else:
        form = HorarioDisponibilidadForm()
    return render(request, 'scheduling/disponibilidad_form.html', {'form': form, 'crear': True})

@login_required
def disponibilidad_update(request, pk):
    disponibilidad = get_object_or_404(HorarioDisponibilidad, pk=pk, barbero__user=request.user)
    if request.method == 'POST':
        form = HorarioDisponibilidadForm(request.POST, instance=disponibilidad)
        if form.is_valid():
            nueva = form.save(commit=False)
            solapado = HorarioDisponibilidad.objects.filter(
                barbero=nueva.barbero,
                dia_semana=nueva.dia_semana,
                hora_inicio__lt=nueva.hora_fin,
                hora_fin__gt=nueva.hora_inicio,
            ).exclude(pk=pk).exists()
            if solapado:
                messages.error(request, "Ya existe una franja solapada para ese día.")
            else:
                nueva.save()
                messages.success(request, "Disponibilidad actualizada correctamente.")
                return redirect('scheduling_disponibilidad:disponibilidad_list')
    else:
        form = HorarioDisponibilidadForm(instance=disponibilidad)
    return render(request, 'scheduling/disponibilidad_form.html', {'form': form, 'crear': False})

@login_required
def disponibilidad_delete(request, pk):
    disponibilidad = get_object_or_404(HorarioDisponibilidad, pk=pk, barbero__user=request.user)
    if request.method == 'POST':
        disponibilidad.delete()
        messages.success(request, "Disponibilidad eliminada correctamente.")
        return redirect('scheduling_disponibilidad:disponibilidad_list')
    return render(request, 'scheduling/disponibilidad_confirm_delete.html', {'disponibilidad': disponibilidad})
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from core.models import Barberia, Sucursal, Servicio, Barbero, HorarioDisponibilidad
from .models import Cita, Valoracion, WaitlistEntry
from .forms import ValoracionForm, WaitlistForm

@login_required
def seleccionar_barberia(request):
    barberias = Barberia.objects.filter(activa=True)
    return render(request, 'scheduling/seleccionar_barberia.html', {'barberias': barberias})

@login_required
def seleccionar_sucursal(request, barberia_id):
    barberia = get_object_or_404(Barberia, id=barberia_id, activa=True)
    sucursales = barberia.sucursales.filter(activo=True)
    return render(request, 'scheduling/seleccionar_sucursal.html', {'barberia': barberia, 'sucursales': sucursales})

@login_required
def seleccionar_servicio(request, sucursal_id):
    sucursal = get_object_or_404(Sucursal, id=sucursal_id, activo=True)
    servicios = sucursal.barberia.servicios.filter(activo=True)
    return render(request, 'scheduling/seleccionar_servicio.html', {'sucursal': sucursal, 'servicios': servicios})

@login_required
def seleccionar_barbero_fecha(request, sucursal_id, servicio_id):
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)
    barberos = Barbero.objects.filter(sucursal_principal=sucursal, user__is_active=True)
    fecha_seleccionada = request.GET.get('fecha', timezone.now().date().isoformat())
    disponibilidad = {}
    barberos_info = []
    for barbero in barberos:
        slots = obtener_slots_disponibles(barbero, fecha_seleccionada, servicio.duracion_minutos)
        promedio = barbero.valoraciones.aggregate(models.Avg('puntuacion'))['puntuacion__avg']
        total_valoraciones = barbero.valoraciones.count()
        barberos_info.append({
            'barbero': barbero,
            'promedio': round(promedio, 1) if promedio else 0,
            'total': total_valoraciones,
            'slots': slots
        })
        if slots:
            disponibilidad[barbero.id] = slots
    return render(request, 'scheduling/seleccionar_barbero_fecha.html', {
        'sucursal': sucursal,
        'servicio': servicio,
        'barberos_info': barberos_info,
        'disponibilidad': disponibilidad,
        'fecha_seleccionada': fecha_seleccionada
    })

def obtener_slots_disponibles(barbero, fecha_str, duracion_minutos):
    fecha = datetime.fromisoformat(fecha_str).date()
    dia_semana = fecha.weekday()
    disponibilidades = HorarioDisponibilidad.objects.filter(barbero=barbero, dia_semana=dia_semana, activo=True)
    if not disponibilidades.exists():
        return []
    slots = []
    for disp in disponibilidades:
        hora_actual = timezone.make_aware(datetime.combine(fecha, disp.hora_inicio))
        hora_fin = timezone.make_aware(datetime.combine(fecha, disp.hora_fin))
        while hora_actual + timedelta(minutes=duracion_minutos) <= hora_fin:
            cita_existente = Cita.objects.filter(
                barbero=barbero,
                fecha_hora=hora_actual,
                estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
            ).exists()
            if not cita_existente:
                slots.append(hora_actual.time())
            hora_actual += timedelta(minutes=30)
    return slots

@login_required
def confirmar_reserva(request, sucursal_id, servicio_id, barbero_id):
    if request.method == 'POST':
        fecha_hora_str = request.POST.get('fecha_hora')
        try:
            fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M:%S')
            fecha_hora = timezone.make_aware(fecha_hora)
            barbero = get_object_or_404(Barbero, id=barbero_id)
            servicio = get_object_or_404(Servicio, id=servicio_id)
            sucursal = get_object_or_404(Sucursal, id=sucursal_id)
            Cita.objects.create(
                cliente=request.user,
                barbero=barbero,
                sucursal=sucursal,
                servicio=servicio,
                fecha_hora=fecha_hora,
                estado=Cita.Estado.PENDIENTE,
                precio=servicio.precio
            )
            messages.success(request, f'Cita reservada para {fecha_hora.strftime("%d/%m/%Y %H:%M")}')
            return redirect('scheduling:mis_citas')
        except ValueError as e:
            messages.error(request, f'Formato de fecha inválido: {e}')
        except Exception as e:
            messages.error(request, f'Error al reservar: {e}')
    return redirect('scheduling:seleccionar_barberia')

@login_required
def mis_citas(request):
    citas = Cita.objects.filter(cliente=request.user).select_related('barbero__user', 'servicio', 'sucursal').order_by('-fecha_hora')
    return render(request, 'scheduling/mis_citas.html', {'citas': citas})

@login_required
def cancelar_cita(request, cita_id):
    if request.method == 'POST':
        cita = get_object_or_404(Cita, id=cita_id, cliente=request.user)
        if cita.estado in [Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]:
            if (cita.fecha_hora - timezone.now()).total_seconds() >= 7200:
                cita.estado = Cita.Estado.CANCELADA_CLIENTE
                cita.cancelado_en = timezone.now()
                cita.save(update_fields=['estado', 'cancelado_en'])
                messages.success(request, "Cita cancelada.")
            else:
                messages.error(request, "No se puede cancelar con menos de 2 horas.")
        else:
            messages.warning(request, "Esta cita no se puede cancelar.")
    return redirect('scheduling:mis_citas')

@login_required
def valorar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user, estado=Cita.Estado.COMPLETADA)
    if hasattr(cita, 'valoracion'):
        messages.warning(request, "Ya valoraste esta cita.")
        return redirect('scheduling:mis_citas')
    if request.method == 'POST':
        form = ValoracionForm(request.POST)
        if form.is_valid():
            v = form.save(commit=False)
            v.cita = cita
            v.cliente = request.user
            v.barbero = cita.barbero
            v.save()
            messages.success(request, "Valoración registrada.")
            return redirect('scheduling:mis_citas')
    else:
        form = ValoracionForm()
    return render(request, 'scheduling/valorar_cita.html', {'form': form, 'cita': cita})

@login_required
def ver_valoraciones_barbero(request, barbero_id):
    barbero = get_object_or_404(Barbero, id=barbero_id)
    valoraciones = Valoracion.objects.filter(barbero=barbero).select_related('cliente', 'cita')
    promedio = valoraciones.aggregate(models.Avg('puntuacion'))['puntuacion__avg'] or 0
    return render(request, 'scheduling/valoraciones_barbero.html', {
        'barbero': barbero,
        'valoraciones': valoraciones,
        'promedio': round(promedio, 1),
        'total': valoraciones.count()
    })

@login_required
def unirse_waitlist(request, barbero_id, servicio_id):
    barbero = get_object_or_404(Barbero, id=barbero_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == 'POST':
        form = WaitlistForm(request.POST)
        if form.is_valid():
            fecha_dia = form.cleaned_data['fecha_dia']
            existe = WaitlistEntry.objects.filter(
                cliente=request.user,
                barbero=barbero,
                servicio=servicio,
                fecha_dia=fecha_dia,
                activo=True,
                utilizado=False
            ).exists()
            if existe:
                messages.info(request, "Ya estás en la lista de espera ese día.")
            else:
                WaitlistEntry.objects.create(
                    cliente=request.user,
                    barbero=barbero,
                    servicio=servicio,
                    fecha_dia=fecha_dia
                )
                messages.success(request, "Te uniste a la lista de espera.")
            return redirect('scheduling:seleccionar_barbero_fecha', barbero.sucursal_principal_id, servicio.id)
    else:
        form = WaitlistForm()
    return render(request, 'scheduling/unirse_waitlist.html', {'form': form, 'barbero': barbero, 'servicio': servicio})
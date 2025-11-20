from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Barberia, Sucursal, Servicio, Barbero, HorarioDisponibilidad
from .models import Cita

@login_required
def seleccionar_barberia(request):
    """Paso 1: Cliente selecciona barbería"""
    barberias = Barberia.objects.filter(activa=True)
    return render(request, 'scheduling/seleccionar_barberia.html', {
        'barberias': barberias
    })

@login_required
def seleccionar_sucursal(request, barberia_id):
    """Paso 2: Selecciona sucursal de la barbería"""
    barberia = get_object_or_404(Barberia, id=barberia_id, activa=True)
    sucursales = barberia.sucursales.filter(activo=True)  # ← CAMBIADO: activo
    return render(request, 'scheduling/seleccionar_sucursal.html', {
        'barberia': barberia,
        'sucursales': sucursales
    })

@login_required
def seleccionar_servicio(request, sucursal_id):
    """Paso 3: Selecciona servicio"""
    sucursal = get_object_or_404(Sucursal, id=sucursal_id, activo=True)
    servicios = sucursal.barberia.servicios.filter(activo=True)
    return render(request, 'scheduling/seleccionar_servicio.html', {
        'sucursal': sucursal,
        'servicios': servicios
    })

@login_required
def seleccionar_barbero_fecha(request, sucursal_id, servicio_id):
    """Paso 4: Selecciona barbero y fecha/hora"""
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    barberos = Barbero.objects.filter(
        sucursal_principal=sucursal,
        user__is_active=True
    )
    
    fecha_seleccionada = request.GET.get('fecha', timezone.now().date().isoformat())
    
    disponibilidad = {}
    for barbero in barberos:
        slots = obtener_slots_disponibles(barbero, fecha_seleccionada, servicio.duracion_minutos)
        if slots:
            disponibilidad[barbero.id] = slots
    
    return render(request, 'scheduling/seleccionar_barbero_fecha.html', {
        'sucursal': sucursal,
        'servicio': servicio,
        'barberos': barberos,
        'disponibilidad': disponibilidad,
        'fecha_seleccionada': fecha_seleccionada
    })

def obtener_slots_disponibles(barbero, fecha_str, duracion_minutos):
    """Calcula slots de 30 min disponibles para un barbero en una fecha"""
    fecha = datetime.fromisoformat(fecha_str).date()
    dia_semana = fecha.weekday()
    
    disponibilidades = HorarioDisponibilidad.objects.filter(
        barbero=barbero,
        dia_semana=dia_semana,
        activo=True
    )
    
    if not disponibilidades.exists():
        return []
    
    slots = []
    for disp in disponibilidades:
        # Hacer timezone-aware
        hora_actual = timezone.make_aware(datetime.combine(fecha, disp.hora_inicio))
        hora_fin = timezone.make_aware(datetime.combine(fecha, disp.hora_fin))
        
        while hora_actual + timedelta(minutes=duracion_minutos) <= hora_fin:
            cita_existente = Cita.objects.filter(
                barbero=barbero,
                fecha_hora=hora_actual,
                estado__in=['pendiente', 'confirmada']
            ).exists()
            
            if not cita_existente:
                slots.append(hora_actual.time())
            
            hora_actual += timedelta(minutes=30)
    
    return slots

@login_required
def confirmar_reserva(request, sucursal_id, servicio_id, barbero_id):
    """Paso 5: Confirmar y crear la cita"""
    if request.method == 'POST':
        fecha_hora_str = request.POST.get('fecha_hora')
        
        try:
            # Parsear correctamente el datetime
            fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M:%S')
            # Hacer timezone-aware
            fecha_hora = timezone.make_aware(fecha_hora)
            
            barbero = get_object_or_404(Barbero, id=barbero_id)
            servicio = get_object_or_404(Servicio, id=servicio_id)
            sucursal = get_object_or_404(Sucursal, id=sucursal_id)
            
            cita = Cita.objects.create(
                cliente=request.user,
                barbero=barbero,
                sucursal=sucursal,
                servicio=servicio,
                fecha_hora=fecha_hora,
                estado='pendiente',
                precio=servicio.precio
            )
            
            messages.success(request, f'Cita reservada para {fecha_hora.strftime("%d/%m/%Y %H:%M")}')
            return redirect('scheduling:mis_citas')
            
        except ValueError as e:
            messages.error(request, f'Error en el formato de fecha: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al reservar: {str(e)}')
    
    return redirect('scheduling:seleccionar_barberia')

@login_required
def mis_citas(request):
    """Ver citas del cliente"""
    citas = Cita.objects.filter(
        cliente=request.user
    ).select_related('barbero__user', 'servicio', 'sucursal').order_by('-fecha_hora')
    
    return render(request, 'scheduling/mis_citas.html', {
        'citas': citas
    })
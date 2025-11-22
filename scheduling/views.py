from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from core.models import Barberia, Sucursal, Servicio, Barbero, HorarioDisponibilidad
from .models import Cita, Valoracion, WaitlistEntry
from .forms import ValoracionForm, WaitlistForm
from .utils import verificar_firma
from .utils import enviar_notificacion
from django.db import transaction
from django.db.models import Avg, Count, Sum, Q
from django.contrib import messages
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
    """HU24: Slots dinámicos sin solapamiento"""
    fecha = datetime.fromisoformat(fecha_str).date()
    dia_semana = fecha.weekday()
    
    # Validar que no sea una fecha pasada
    if fecha < timezone.now().date():
        return []
    
    disponibilidades = HorarioDisponibilidad.objects.filter(
        barbero=barbero, 
        dia_semana=dia_semana, 
        activo=True
    ).order_by('hora_inicio')
    
    if not disponibilidades.exists():
        return []
    
    slots = []
    intervalo = timedelta(minutes=30)  # Slots cada 30 min
    
    for disp in disponibilidades:
        hora_actual = timezone.make_aware(datetime.combine(fecha, disp.hora_inicio))
        hora_fin = timezone.make_aware(datetime.combine(fecha, disp.hora_fin))
        
        while hora_actual + timedelta(minutes=duracion_minutos) <= hora_fin:
            # Validar que no haya citas en ese slot ni overlapping
            hora_fin_servicio = hora_actual + timedelta(minutes=duracion_minutos)
            
            conflicto = Cita.objects.filter(
                barbero=barbero,
                estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
                fecha_hora__lt=hora_fin_servicio,  # Termina después de que empieza este slot
                fecha_hora__gte=hora_actual - timedelta(minutes=duracion_minutos)  # Empieza antes de que termina este slot
            ).exists()
            
            if not conflicto and hora_actual >= timezone.now():
                slots.append(hora_actual.time())
            
            hora_actual += intervalo
    
    return slots

@login_required
def confirmar_reserva(request, sucursal_id, servicio_id, barbero_id):
    """Crear cita y notificar al barbero (HU25)"""
    if request.method != 'POST':
        return redirect('scheduling:seleccionar_barberia')

    fecha_hora_str = request.POST.get('fecha_hora')
    if not fecha_hora_str:
        messages.error(request, "Falta fecha/hora")
        return redirect('scheduling:seleccionar_barberia')

    try:
        fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M:%S')
        fecha_hora = timezone.make_aware(fecha_hora)
    except ValueError:
        messages.error(request, "Formato de fecha inválido")
        return redirect('scheduling:seleccionar_barberia')

    barbero = get_object_or_404(Barbero, id=barbero_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)

    # Validaciones básicas
    if fecha_hora < timezone.now():
        messages.error(request, "No puedes reservar en el pasado")
        return redirect('scheduling:seleccionar_barberia')

    conflicto = Cita.objects.filter(
        barbero=barbero,
        fecha_hora=fecha_hora,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
    ).exists()
    if conflicto:
        messages.error(request, "Ese horario ya no está disponible")
        return redirect('scheduling:seleccionar_barberia')

    try:
        with transaction.atomic():
            cita = Cita.objects.create(
                cliente=request.user,
                barbero=barbero,
                sucursal=sucursal,
                servicio=servicio,
                fecha_hora=fecha_hora,
                estado=Cita.Estado.PENDIENTE,
                precio=servicio.precio
            )

            # HU25: Notificación tiempo real al barbero
            enviar_notificacion(
                user_id=barbero.user_id,
                tipo='nueva_cita',
                mensaje=f'Nueva cita {servicio.nombre} con {request.user.nombre} el {fecha_hora.strftime("%d/%m %H:%M")}',
                data={'cita_id': cita.id, 'fecha': fecha_hora.isoformat()}
            )

        messages.success(request, f'Cita reservada para {fecha_hora.strftime("%d/%m/%Y %H:%M")}')
    except Exception as e:
        messages.error(request, f'Error al reservar: {e}')

    return redirect('scheduling:mis_citas')

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
                
                # HU09: Notificar waitlist
                from .tasks import notificar_primer_waitlist
                notificar_primer_waitlist.delay(
                    barbero_id=cita.barbero_id,
                    servicio_id=cita.servicio_id,
                    fecha_dia_iso=cita.fecha_hora.date().isoformat()
                )
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
def confirmar_cita_por_enlace(request, token):
    """Cliente confirma cita desde el enlace del email (HU06)"""
    payload = verificar_firma(token, max_age=60*60*4)  # 4h de validez
    if not payload:
        messages.error(request, "Enlace inválido o expirado")
        return redirect('home')
    
    try:
        _, cita_id, accion = payload.split(':')
        cita = Cita.objects.get(id=int(cita_id))
        
        if accion == 'confirmar':
            cita.marcar_confirmada()
            messages.success(request, f"✓ Cita confirmada para {cita.fecha_hora.strftime('%d/%m %H:%M')}")
        return redirect('scheduling:mis_citas')
    except Exception as e:
        messages.error(request, "Error al procesar confirmación")
        return redirect('home')
@login_required
def historial_citas(request):
    """HU16: Historial completo de citas con filtros"""
    estado = request.GET.get('estado', '')
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')
    
    citas = Cita.objects.filter(cliente=request.user).select_related(
        'barbero__user', 'servicio', 'sucursal'
    )
    
    if estado:
        citas = citas.filter(estado=estado)
    if desde:
        citas = citas.filter(fecha_hora__date__gte=desde)
    if hasta:
        citas = citas.filter(fecha_hora__date__lte=hasta)
    
    citas = citas.order_by('-fecha_hora')
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(citas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estados': Cita.Estado.choices,
        'filtros': {
            'estado': estado,
            'desde': desde,
            'hasta': hasta
        }
    }
    return render(request, 'scheduling/historial_citas.html', context)
@login_required
def reprogramar_cita(request, cita_id):
    """HU11: Cliente reprograma su cita"""
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user)
    
    if not cita.puede_modificar():
        messages.error(request, "No puedes reprogramar esta cita (menos de 2h o estado inválido)")
        return redirect('scheduling:mis_citas')
    
    if cita.reprogramado_count >= 3:
        messages.error(request, "Has alcanzado el límite de 3 reprogramaciones")
        return redirect('scheduling:mis_citas')
    
    if request.method == 'POST':
        nueva_fecha_str = request.POST.get('fecha_hora')
        try:
            nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M:%S')
            nueva_fecha = timezone.make_aware(nueva_fecha)
            
            # Validar que el slot esté disponible
            conflicto = Cita.objects.filter(
                barbero=cita.barbero,
                fecha_hora=nueva_fecha,
                estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
            ).exclude(id=cita.id).exists()
            
            if conflicto:
                messages.error(request, "Ese horario ya no está disponible")
                return redirect('scheduling:reprogramar_cita', cita_id)
            
            cita.reprogramar(nueva_fecha)
            messages.success(request, f"Cita reprogramada para {nueva_fecha.strftime('%d/%m/%Y %H:%M')}")
            return redirect('scheduling:mis_citas')
            
        except ValueError as e:
            messages.error(request, f"Formato de fecha inválido: {e}")
    
    # Obtener slots disponibles
    fecha_actual = cita.fecha_hora.date().isoformat()
    slots = obtener_slots_disponibles(cita.barbero, fecha_actual, cita.servicio.duracion_minutos)
    
    context = {
        'cita': cita,
        'slots': slots,
        'fecha_actual': fecha_actual
    }
    return render(request, 'scheduling/reprogramar_cita.html', context)
@login_required
def buscar_barberos(request):
    sucursal_id_raw = request.GET.get('sucursal')
    servicio_id_raw = request.GET.get('servicio')
    min_valoracion_raw = request.GET.get('valoracion')

    sucursal_id = sucursal_id_raw if sucursal_id_raw and sucursal_id_raw.isdigit() else None
    servicio_id = int(servicio_id_raw) if servicio_id_raw and servicio_id_raw.isdigit() else None
    min_valoracion = float(min_valoracion_raw) if min_valoracion_raw else None

    barberos = Barbero.objects.filter(activo=True)

    if sucursal_id:
        barberos = barberos.filter(
            Q(sucursal_principal_id=sucursal_id) |
            Q(sucursales_adicionales__id=sucursal_id)
        )

    if servicio_id:
        barberos = barberos.filter(servicios__id=servicio_id)

    if min_valoracion is not None:
        barberos = barberos.annotate(
            promedio_valoracion=Avg('valoraciones__puntuacion')
        ).filter(promedio_valoracion__gte=min_valoracion)

    barberos = barberos.distinct().select_related('user', 'sucursal_principal')

    barberos_data = []
    for b in barberos:
        stats = b.valoraciones.aggregate(promedio=Avg('puntuacion'), total=Count('id'))
        barberos_data.append({
            'barbero': b,
            'promedio': round(stats['promedio'] or 0, 1),
            'total_valoraciones': stats['total']
        })

    context = {
        'barberos_data': barberos_data,
        'sucursales': Sucursal.objects.filter(activo=True),
        'servicios': Servicio.objects.all(),
        'filtros': {
            'sucursal_id': sucursal_id,
            'servicio_id': servicio_id,
            'min_valoracion': min_valoracion_raw
        }
    }
    return render(request, 'scheduling/buscar_barberos.html', context)
# ...existing code...

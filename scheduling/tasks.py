from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from .models import Cita
from .utils import generar_token_waitlist

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_email_confirmacion(self, cita_id: int):
    try:
        cita = Cita.objects.get(id=cita_id)
        if cita.confirmada_email:
            return "skip"
        send_mail(
            subject="Confirmación de tu cita",
            message=f"Tu cita con {cita.barbero.nombre} el {cita.fecha_hora.strftime('%d/%m %H:%M')} está registrada.",
            from_email=None,
            recipient_list=[cita.cliente.email],
            fail_silently=True,
        )
        cita.confirmada_email = True
        cita.save(update_fields=["confirmada_email"])
        return "ok"
    except Cita.DoesNotExist:
        return "no_existe"
    except Exception as e:
        raise self.retry(exc=e)

@shared_task
def enviar_recordatorios():
    from django.core.mail import send_mail
    from django.conf import settings
    from .utils import firmar
    
    ahora = timezone.now()
    inicio = ahora + timedelta(hours=2)
    fin = inicio + timedelta(minutes=10)
    
    qs = Cita.objects.filter(
        fecha_hora__gte=inicio,
        fecha_hora__lte=fin,
        recordatorio_enviado=False,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).select_related('cliente', 'barbero', 'servicio')
    
    enviados = 0
    for cita in qs:
        token_confirmar = firmar(f"cita:{cita.id}:confirmar")
        enlace = f"{settings.SITE_URL}/scheduling/confirmar/{token_confirmar}/"
        
        send_mail(
            subject="⏰ Recordatorio: Tu cita en 2 horas",
            message=f"Hola {cita.cliente.nombre},\n\nEn 2 horas tienes cita con {cita.barbero.nombre} ({cita.servicio.nombre}) a las {cita.fecha_hora.strftime('%H:%M')}.\n\nConfirma aquí: {enlace}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cita.cliente.email],
            fail_silently=True,
        )
        cita.recordatorio_enviado = True
        cita.save(update_fields=["recordatorio_enviado"])
        enviados += 1
    
    return f"recordatorios={enviados}"

@shared_task
def limpiar_waitlist_expirada():
    from .models import WaitlistEntry
    ahora = timezone.now()
    qs = WaitlistEntry.objects.filter(
        activo=True,
        notificado_en__isnull=False,
        expiracion_notificacion__lt=ahora,
        utilizado=False
    )
    count = qs.update(activo=False)
    return f"waitlist_expirada={count}"

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def notificar_primer_waitlist(self, barbero_id, servicio_id, fecha_dia_iso):
    from .models import WaitlistEntry
    fecha_dia = datetime.fromisoformat(fecha_dia_iso).date()
    entry = WaitlistEntry.objects.filter(
        barbero_id=barbero_id,
        servicio_id=servicio_id,
        fecha_dia=fecha_dia,
        activo=True,
        utilizado=False,
        notificado_en__isnull=True
    ).order_by('creado_en').first()
    if not entry:
        return "sin_entry"
    entry.notificado_en = timezone.now()
    entry.expiracion_notificacion = entry.notificado_en + timedelta(minutes=15)
    entry.save(update_fields=['notificado_en', 'expiracion_notificacion'])
    token = generar_token_waitlist(entry.id)
    path = reverse('scheduling:waitlist_reclamar', args=[token])
    base = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    link = f"{base}{path}"
    mensaje = (
        f"Se liberó un turno para {entry.servicio.nombre} con {entry.barbero.nombre} el {fecha_dia}.\n"
        f"Reserva antes de 15 minutos:\n{link}"
    )
    send_mail(
        subject="Slot disponible",
        message=mensaje,
        from_email=None,
        recipient_list=[entry.cliente.email],
        fail_silently=True,
    )
    return f"notificado_entry={entry.id}"

GRACIA_NO_SHOW_MIN = 15  # minutos

@shared_task
def marcar_no_show_citas():
    ahora = timezone.now()
    limite = ahora - timedelta(minutes=GRACIA_NO_SHOW_MIN)
    qs = Cita.objects.filter(
        fecha_hora__lt=limite,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA, Cita.Estado.EN_PROCESO]
    )
    total = qs.count()
    if not total:
        return "no_show=0"
    with transaction.atomic():
        for cita in qs.select_for_update():
            cita.marcar_no_show()
    return f"no_show={total}"
@shared_task
def enviar_recordatorios_24h():
    """HU35: Recordatorios 24 horas antes"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    ahora = timezone.now()
    inicio = ahora + timedelta(hours=24)
    fin = inicio + timedelta(minutes=30)
    
    citas = Cita.objects.filter(
        fecha_hora__gte=inicio,
        fecha_hora__lte=fin,
        recordatorio_24h_enviado=False,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).select_related('cliente', 'barbero', 'servicio', 'sucursal')
    
    enviados = 0
    for cita in citas:
        from .utils import firmar
        token_cancelar = firmar(f"cita:{cita.id}:cancelar")
        enlace_cancelar = f"{settings.SITE_URL}/scheduling/cancelar/{token_cancelar}/"
        
        send_mail(
            subject="📅 Recordatorio: Tu cita mañana",
            message=f"""Hola {cita.cliente.nombre},

Te recordamos tu cita para mañana:
📅 Fecha: {cita.fecha_hora.strftime('%d/%m/%Y')}
🕐 Hora: {cita.fecha_hora.strftime('%H:%M')}
💈 Barbero: {cita.barbero.nombre}
📍 Sucursal: {cita.sucursal.nombre} - {cita.sucursal.direccion}
✂️ Servicio: {cita.servicio.nombre}
💰 Precio: ${cita.precio}

Si necesitas cancelar: {enlace_cancelar}

¡Te esperamos!
BarberFlow
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cita.cliente.email],
            fail_silently=True,
        )
        
        cita.recordatorio_24h_enviado = True
        cita.save(update_fields=['recordatorio_24h_enviado'])
        enviados += 1
    
    return f"recordatorios_24h={enviados}"
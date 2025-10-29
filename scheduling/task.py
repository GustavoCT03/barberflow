from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

@shared_task
def enviar_confirmacion_t_menos_2h(reserva_id):
    # Busca reserva y envía correo con enlace firmado para confirmar/cancelar
    # (implementar lógica real con tokens/time windows)
    # send_mail(asunto, cuerpo, from, [to])
    return f"OK T-2h {reserva_id}"

@shared_task
def notificar_waitlist(reserva_id):
    # Notifica al primero en cola y abre ventana 15 minutos
    return f"OK waitlist {reserva_id}"

@shared_task
def reasignar_por_barbero_ausente(turno_id):
    # Busca alternativa en misma franja y ofrece al cliente
    return f"OK reasignación {turno_id}"


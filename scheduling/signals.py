from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cita
from .tasks import enviar_email_confirmacion
from core.models import ProgramaFidelidad

@receiver(post_save, sender=Cita)
def cita_post_save(sender, instance: Cita, created, **kwargs):
    if created:
        enviar_email_confirmacion.delay(instance.id)
    else:
        if instance.estado == Cita.Estado.CONFIRMADA and not instance.confirmada_email:
            enviar_email_confirmacion.delay(instance.id)
        if instance.reprogramado_count > 0 and instance.recordatorio_enviado:
            instance.recordatorio_enviado = False
            instance.save(update_fields=["recordatorio_enviado"])
@receiver(post_save, sender=Cita)
def otorgar_puntos_fidelidad(sender, instance, created, **kwargs):
    """HU42: Otorgar puntos al completar cita"""
    if instance.estado == Cita.Estado.COMPLETADA and not created:
        barberia = instance.sucursal.barberia
        try:
            programa = ProgramaFidelidad.objects.get(barberia=barberia, activo=True)
            puntos = programa.puntos_por_cita
            if puntos > 0:
                instance.cliente.agregar_puntos(barberia.id, puntos, instance)
        except ProgramaFidelidad.DoesNotExist:
            pass
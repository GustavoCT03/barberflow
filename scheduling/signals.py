from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cita
from .tasks import enviar_email_confirmacion

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
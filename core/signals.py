from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Cliente

@receiver(post_save, sender=User)
def crear_cliente_automatico(sender, instance, created, **kwargs):
    """
    Crea automáticamente un perfil Cliente cuando se registra un usuario con rol CLIENTE.
    """
    if created and instance.rol == User.Roles.CLIENTE:
        Cliente.objects.get_or_create(user=instance)
        
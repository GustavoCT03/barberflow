from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Perfil, Cliente

@receiver(post_save, sender=User)
def create_perfiles(sender, instance: User, created, **kwargs):
    if not created:
        return
    # Crea Perfil con el rol actual del usuario
    Perfil.objects.get_or_create(user=instance, defaults={"rol": instance.rol})
    # Si es cliente, crea su perfil de Cliente
    if instance.rol == User.Roles.CLIENTE:
        Cliente.objects.get_or_create(user=instance)
        
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Cliente

@receiver(post_save, sender=User)
def create_perfiles(sender, instance: User, created, **kwargs):
    if created and instance.rol == User.Rol.CLIENTE:
        Cliente.objects.get_or_create(user=instance)
        
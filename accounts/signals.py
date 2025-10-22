from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Perfil

User = get_user_model()

def crear_perfil(sender, isntance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)
        
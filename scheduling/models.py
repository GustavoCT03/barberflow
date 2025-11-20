from django.db import models
from django.conf import settings
from core.models import Barbero, Sucursal, Servicio

class Cita(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('no_show', 'No Show'),
    ]
    
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas_scheduling')
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='citas_scheduling')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='citas_scheduling')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas_scheduling')
    fecha_hora = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scheduling_cita'
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f"Cita {self.id} - {self.cliente.nombre} con {self.barbero.nombre}"
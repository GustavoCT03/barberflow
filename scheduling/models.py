from django.db import models
from django.conf import settings
from core.models import Barbero, Sucursal, Servicio
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib import admin
from decimal import Decimal
from django.core.exceptions import ValidationError
class Promocion(models.Model):
    class TipoDescuento(models.TextChoices):
        PORCENTAJE = 'porcentaje', 'Porcentaje'
        MONTO_FIJO = 'monto_fijo', 'Monto Fijo'
    
    barberia = models.ForeignKey('core.Barberia', on_delete=models.CASCADE, related_name='promociones')
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True, help_text="Código que ingresa el cliente")
    tipo_descuento = models.CharField(max_length=20, choices=TipoDescuento.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Porcentaje o monto fijo")
    
    # Restricciones
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    usos_maximos = models.IntegerField(default=0, help_text="0 = ilimitado")
    usos_actuales = models.IntegerField(default=0)
    monto_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Aplicabilidad
    servicios = models.ManyToManyField('core.Servicio', blank=True, help_text="Vacío = todos")
    solo_nuevos_clientes = models.BooleanField(default=False)
    
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bf_promociones'
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
    
    def calcular_descuento(self, monto):
        """Calcula el descuento aplicado al monto"""
        if self.tipo_descuento == self.TipoDescuento.PORCENTAJE:
            return monto * (self.valor / 100)
        return min(self.valor, monto)
    
    def es_valida(self, cliente=None, servicio=None, monto=0):
        """Valida si la promoción se puede aplicar"""
        from django.utils import timezone
        
        if not self.activo:
            return False, "Promoción inactiva"
        
        hoy = timezone.now().date()
        if not (self.fecha_inicio <= hoy <= self.fecha_fin):
            return False, "Promoción fuera de vigencia"
        
        if self.usos_maximos > 0 and self.usos_actuales >= self.usos_maximos:
            return False, "Promoción agotada"
        
        if monto < self.monto_minimo:
            return False, f"Monto mínimo: ${self.monto_minimo}"
        
        if self.servicios.exists() and servicio and servicio not in self.servicios.all():
            return False, "Promoción no válida para este servicio"
        
        if self.solo_nuevos_clientes and cliente:
            if Cita.objects.filter(cliente=cliente, estado=Cita.Estado.COMPLETADA).exists():
                return False, "Solo para nuevos clientes"
        
        return True, "Válida"
class Cita(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        CONFIRMADA = 'confirmada', 'Confirmada'
        EN_PROCESO = 'en_proceso', 'En Proceso'
        COMPLETADA = 'completada', 'Completada'
        CANCELADA_CLIENTE = 'cancelada_cliente', 'Cancelada por Cliente'
        CANCELADA_ADMIN = 'cancelada_admin', 'Cancelada por Admin'
        NO_SHOW = 'no_show', 'No Show'

    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas_scheduling')
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='citas_scheduling')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='citas_scheduling')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas_scheduling')
    fecha_hora = models.DateTimeField(db_index=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True)

    promocion = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas')
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0)


    confirmada_en = models.DateTimeField(null=True, blank=True)
    cancelado_en = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.CharField(max_length=150, blank=True)
    reprogramado_count = models.PositiveIntegerField(default=0)
    ultima_reprogramacion = models.DateTimeField(null=True, blank=True)

    confirmada_email = models.BooleanField(default=False)
    recordatorio_enviado = models.BooleanField(default=False)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    recordatorio_24h_enviado = models.BooleanField(default=False)
    motivo_cancelacion = models.TextField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    nota_interna = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'scheduling_cita'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['fecha_hora']),
            models.Index(fields=['barbero', 'fecha_hora']),
            models.Index(fields=['cliente', 'fecha_hora']),
        ]

    def __str__(self):
        return f"Cita {self.id} - {self.cliente.nombre} con {self.barbero.nombre}"
    def debe_enviar_recordatorio(self):
        """HU1: Verifica si debe enviarse recordatorio (24h antes)"""
        ahora = timezone.now()
        tiempo_hasta_cita = self.fecha_hora - ahora
        
        # Entre 23 y 25 horas antes
        if timedelta(hours=23) <= tiempo_hasta_cita <= timedelta(hours=25):
            # Verificar que no se haya enviado ya
            from core.models import NotificacionEmail
            ya_enviado = NotificacionEmail.objects.filter(
                cita=self,
                tipo=NotificacionEmail.TipoNotificacion.RECORDATORIO_CITA,
                exitoso=True
            ).exists()
            
            return not ya_enviado
        
        return False
    
    def obtener_datos_email_recordatorio(self):
        """HU1: Obtiene datos formateados para el email de recordatorio"""
        return {
            'cliente_nombre': self.cliente.nombre,
            'fecha': self.fecha_hora.strftime('%d/%m/%Y'),
            'hora': self.fecha_hora.strftime('%H:%M'),
            'barbero': self.barbero.nombre,
            'servicio': self.servicio.nombre,
            'precio': f"${self.precio:,.0f}",
            'sucursal': self.sucursal.nombre,
            'sucursal_direccion': self.sucursal.direccion,
            'cita_id': self.id
        }

    def puede_modificar(self):
        if self.estado not in [self.Estado.PENDIENTE, self.Estado.CONFIRMADA]:
            return False
        return (self.fecha_hora - timezone.now()) >= timedelta(hours=2)

    def puede_cancelar(self):
        """HU2: Verifica si la cita puede ser cancelada (>2h anticipación)"""
        if self.estado not in [self.Estado.PENDIENTE, self.Estado.CONFIRMADA]:
            return False, "Solo puedes cancelar citas pendientes o confirmadas"
        
        ahora = timezone.now()
        tiempo_restante = self.fecha_hora - ahora
        
        if tiempo_restante < timedelta(hours=2):
            return False, "Debes cancelar con al menos 2 horas de anticipación"
        
        return True, "Puedes cancelar esta cita"
    
    def cancelar(self, usuario):
        """HU2: Cancela la cita y registra en log"""
        puede, mensaje = self.puede_cancelar()
        
        if not puede:
            raise ValidationError(mensaje)
        
        self.estado = self.Estado.CANCELADA
        self.save(update_fields=['estado'])
        
        # Registrar en log de actividad
        from core.models import LogActividad
        LogActividad.objects.create(
            usuario=usuario,
            accion=f"Canceló cita #{self.id}",
            detalles=f"Cliente: {self.cliente.nombre}, Fecha: {self.fecha_hora}, Barbero: {self.barbero.nombre}"
        )
        
        # Enviar email de confirmación
        self._enviar_email_cancelacion()
    
    def _enviar_email_cancelacion(self):
        """HU2: Envía email confirmando la cancelación"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        from core.models import NotificacionEmail
        
        context = {
            'cliente_nombre': self.cliente.nombre,
            'fecha': self.fecha_hora.strftime('%d/%m/%Y'),
            'hora': self.fecha_hora.strftime('%H:%M'),
            'barbero': self.barbero.nombre,
            'servicio': self.servicio.nombre,
            'sucursal': self.sucursal.nombre,
            'cita_id': self.id
        }
        
        try:
            html_message = render_to_string('emails/cancelacion_cita.html', context)
            plain_message = render_to_string('emails/cancelacion_cita.txt', context)
            
            send_mail(
                subject=f'Cancelación confirmada - Cita #{self.id}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.cliente.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            NotificacionEmail.objects.create(
                destinatario=self.cliente,
                cita=self,
                tipo=NotificacionEmail.TipoNotificacion.CANCELACION_CITA,
                asunto=f'Cancelación confirmada - Cita #{self.id}',
                exitoso=True
            )
        except Exception as e:
            NotificacionEmail.objects.create(
                destinatario=self.cliente,
                cita=self,
                tipo=NotificacionEmail.TipoNotificacion.CANCELACION_CITA,
                asunto=f'Cancelación confirmada - Cita #{self.id}',
                exitoso=False,
                error=str(e)
            )

    def marcar_confirmada(self):
        if self.estado == self.Estado.PENDIENTE:
            self.estado = self.Estado.CONFIRMADA
            self.confirmada_en = timezone.now()
            self.save()

    def marcar_no_show(self):
        if self.estado in [self.Estado.CONFIRMADA, self.Estado.EN_PROCESO]:
            self.estado = self.Estado.NO_SHOW
            self.save()

    def completar(self):
        if self.estado in [self.Estado.CONFIRMADA, self.Estado.EN_PROCESO]:
            self.estado = self.Estado.COMPLETADA
            self.save()

    def reprogramar(self, nueva_fecha_hora: datetime):
        if not self.puede_modificar():
            raise ValueError("No se puede reprogramar.")
        self.fecha_hora = nueva_fecha_hora
        self.reprogramado_count += 1
        self.ultima_reprogramacion = timezone.now()
        self.estado = self.Estado.PENDIENTE
        self.recordatorio_enviado = False
        self.save()
class Valoracion(models.Model):
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name='valoracion')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='valoraciones')
    puntuacion = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comentario = models.TextField(blank=True, null=True)
    creada_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = 'scheduling_valoracion'
        ordering = ['-creada_en']
        unique_together = ('cita', 'cliente')

    def __str__(self):
        return f"Valoración cita {self.cita_id} - {self.puntuacion}"
class WaitlistEntry(models.Model):
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='waitlist_entries')
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='waitlist_entries')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='waitlist_entries')
    fecha_dia = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)
    notificado_en = models.DateTimeField(null=True, blank=True)
    expiracion_notificacion = models.DateTimeField(null=True, blank=True)
    utilizado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'scheduling_waitlist'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['barbero', 'fecha_dia', 'activo']),
        ]

    def ventana_activa(self):
        return self.activo and self.notificado_en and timezone.now() < self.expiracion_notificacion

    def __str__(self):
        return f"WL {self.id} {self.cliente} {self.fecha_dia}"
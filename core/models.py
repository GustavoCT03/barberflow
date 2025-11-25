from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import timedelta
import re




def get_expiration_date():
    return timezone.now() + timedelta(days=7)
# =========================
# USER
# =========================
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser requiere is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser requiere is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin"
        ADMIN_BARBERIA = "admin_barberia", "Admin Barbería"
        BARBERO = "barbero", "Barbero"
        CLIENTE = "cliente", "Cliente"

    email = models.EmailField(unique=True, db_index=True)
    nombre = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CLIENTE, db_index=True)
    barberia = models.ForeignKey('core.Barberia', on_delete=models.SET_NULL, null=True, blank=True)
    puntos_fidelidad = models.JSONField(default=dict, blank=True, help_text="{'barberia_id': puntos}")
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["nombre"]

    def __str__(self):
        return f"{self.nombre} <{self.email}>"
    
    def obtener_puntos(self, barberia_id):
        """HU42: Obtener puntos de fidelidad de una barbería"""
        if not isinstance(self.puntos_fidelidad, dict):
            self.puntos_fidelidad = {}
            self.save(update_fields=['puntos_fidelidad'])
        return self.puntos_fidelidad.get(str(barberia_id), 0)
    
    def agregar_puntos(self, barberia_id, puntos, cita=None):
        """HU42: Agregar puntos al cliente por cita completada"""
        barberia_id_str = str(barberia_id)
        
        if not isinstance(self.puntos_fidelidad, dict):
            self.puntos_fidelidad = {}
        
        self.puntos_fidelidad[barberia_id_str] = self.puntos_fidelidad.get(barberia_id_str, 0) + puntos
        self.save(update_fields=['puntos_fidelidad'])
        
        # Registrar historial
        HistorialPuntos.objects.create(
            cliente=self,
            barberia_id=barberia_id,
            tipo=HistorialPuntos.TipoMovimiento.GANADOS,
            puntos=puntos,
            cita=cita,
            descripcion=f"Ganados por cita #{cita.id}" if cita else "Puntos ganados"
        )
        
        return self.puntos_fidelidad[barberia_id_str]
    
    def canjear_puntos(self, barberia_id, puntos):
        """HU42: Canjear puntos por descuento"""
        barberia_id_str = str(barberia_id)
        
        if not isinstance(self.puntos_fidelidad, dict):
            self.puntos_fidelidad = {}
        
        saldo_actual = self.puntos_fidelidad.get(barberia_id_str, 0)
        
        if saldo_actual < puntos:
            return False, "Puntos insuficientes"
        
        self.puntos_fidelidad[barberia_id_str] = saldo_actual - puntos
        self.save(update_fields=['puntos_fidelidad'])
        
        # Registrar historial
        HistorialPuntos.objects.create(
            cliente=self,
            barberia_id=barberia_id,
            tipo=HistorialPuntos.TipoMovimiento.CANJEADOS,
            puntos=-puntos,
            descripcion="Canjeados en reserva"
        )
        
        return True, self.puntos_fidelidad[barberia_id_str]
    
    def obtener_todas_las_barberias_con_puntos(self):
        """Obtener lista de barberías donde el usuario tiene puntos"""
        if not isinstance(self.puntos_fidelidad, dict):
            return []
        
        resultado = []
        for barberia_id, puntos in self.puntos_fidelidad.items():
            if puntos > 0:
                try:
                    barberia = Barberia.objects.get(id=int(barberia_id))
                    try:
                        programa = ProgramaFidelidad.objects.get(barberia=barberia, activo=True)
                        valor_monetario = puntos * float(programa.pesos_por_punto)
                    except ProgramaFidelidad.DoesNotExist:
                        valor_monetario = 0
                    
                    resultado.append({
                        'barberia': barberia,
                        'puntos': puntos,
                        'valor': valor_monetario
                    })
                except Barberia.DoesNotExist:
                    pass
        
        return resultado


phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Teléfono 7–15 dígitos (opcional +)."
)


class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cliente")
    telefono = models.CharField(max_length=16, validators=[phone_validator], blank=True, null=True)
    acepta_sms = models.BooleanField(default=False)
    acepta_email = models.BooleanField(default=True)
    puntos = models.IntegerField(default=0)

    def __str__(self):
        return f"Cliente {self.user.nombre}"


# =========================
# BARBERÍA / SUCURSAL
# =========================
class Nosotros(models.Model):
    nombre = models.CharField(max_length=150)
    plan = models.CharField(max_length=50, default="trial")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Barberia(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE, related_name="barberias")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Barbería"
        verbose_name_plural = "Barberías"

    def __str__(self):
        return f"{self.nombre} ({self.nosotros.nombre})"


class Sucursal(models.Model):
    barberia = models.ForeignKey(Barberia, on_delete=models.CASCADE, related_name="sucursales")
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.barberia.nombre})"


class Barbero(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE, related_name="barberos")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=120)
    sucursal_principal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# =========================
# INVITACIONES BARBERO (HU03)
# =========================
class InvitacionBarbero(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE, related_name="invitaciones")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name="invitaciones", null=True, blank=True)  # ← agregado null/blank
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    usado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.fecha_expiracion:
            self.fecha_expiracion = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({'usado' if self.usado else 'pendiente'})"


# =========================
# SERVICIOS
# =========================
class Servicio(models.Model):
    barberia = models.ForeignKey(Barberia, on_delete=models.CASCADE, related_name="servicios")
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    duracion_minutos = models.PositiveIntegerField(default=30)
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"


class HorarioDisponibilidad(models.Model):
    class DiaSemana(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.IntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["barbero", "dia_semana", "hora_inicio"]
        unique_together = ["barbero", "dia_semana", "hora_inicio"]

    def __str__(self):
        return f"{self.barbero.nombre} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"


# =========================
# VALORACIONES
# =========================



# =========================
# PROMOCIONES
# =========================
class Promocion(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE, related_name="promociones")
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    codigo = models.CharField(max_length=20, unique=True, blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activa = models.BooleanField(default=True)
    clientes = models.ManyToManyField(Cliente, blank=True, related_name="promociones_recibidas")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.titulo} ({self.descuento_porcentaje}% OFF)"

    def esta_vigente(self):
        hoy = timezone.now().date()
        return self.activa and self.fecha_inicio <= hoy <= self.fecha_fin
class ProgramaFidelidad(models.Model):
    barberia = models.ForeignKey(Barberia, on_delete=models.CASCADE, related_name="programa_fidelidad")
    puntos_por_cita = models.PositiveIntegerField(default=10, help_text="Puntos ganados por cita completada")
    pesos_por_punto = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=100,
        validators=[MinValueValidator(0)],
        help_text="Valor en pesos de cada punto"
    )
    minimo_canje = models.PositiveIntegerField(default=50, help_text="Mínimo de puntos para canjear")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Programa de Fidelidad"
        verbose_name_plural = "Programas de Fidelidad"

    def __str__(self):
        return f"Programa {self.barberia.nombre} ({self.puntos_por_cita}pts/cita)"
class HistorialPuntos(models.Model):
    class TipoMovimiento(models.TextChoices):
        GANADOS = "ganados", "Ganados"
        CANJEADOS = "canjeados", "Canjeados"
        EXPIRARON = "expiraron", "Expiraron"
        AJUSTE = "ajuste", "Ajuste Manual"

    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="historial_puntos")
    barberia = models.ForeignKey(Barberia, on_delete=models.CASCADE, related_name="historial_puntos")
    cita = models.ForeignKey("scheduling.Cita", on_delete=models.SET_NULL, null=True, blank=True, related_name="puntos_generados")
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    puntos = models.IntegerField(help_text="Positivo=ganados, Negativo=canjeados")
    descripcion = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Historial de Puntos"
        verbose_name_plural = "Historial de Puntos"

    def __str__(self):
        return f"{self.cliente.nombre} - {self.puntos}pts ({self.get_tipo_display()})"

# =========================
# PLANES / LICENCIAS
# =========================
class Plan(models.Model):
    class TipoPlan(models.TextChoices):
        TRIAL = "trial", "Trial"
        BASICO = "basico", "Básico"
        PROFESIONAL = "profesional", "Profesional"
        EMPRESARIAL = "empresarial", "Empresarial"

    class Periodicidad(models.TextChoices):
        MENSUAL = "mensual", "Mensual"
        ANUAL = "anual", "Anual"

    nombre = models.CharField(max_length=50, choices=TipoPlan.choices, unique=True)
    periodicidad = models.CharField(max_length=10, choices=Periodicidad.choices, default=Periodicidad.MENSUAL)
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    max_barberos = models.PositiveIntegerField(default=1)
    max_sucursales = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_nombre_display()} {self.get_periodicidad_display()} (${self.precio})"


class Licencia(models.Model):
    nosotros = models.OneToOneField(Nosotros, on_delete=models.CASCADE, related_name="licencia")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    fecha_inicio = models.DateField()
    fecha_expiracion = models.DateField()
    activa = models.BooleanField(default=True, db_index=True)
    pago_pendiente = models.BooleanField(default=False)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Licencia {self.nosotros.nombre} - {self.plan.nombre}"

    def esta_activa(self):
        hoy = timezone.now().date()
        return self.activa and not self.pago_pendiente and self.fecha_expiracion >= hoy

    def suspender(self):
        self.activa = False
        self.nosotros.activo = False
        self.nosotros.save()
        self.save()

class NotificacionEmail(models.Model):
    """HU1: Registro de emails enviados para evitar duplicados"""
    
    class TipoNotificacion(models.TextChoices):
        RECORDATORIO_CITA = "recordatorio_cita", "Recordatorio de Cita"
        CONFIRMACION_CITA = "confirmacion_cita", "Confirmación de Cita"
        CANCELACION_CITA = "cancelacion_cita", "Cancelación de Cita"
        CITA_COMPLETADA = "cita_completada", "Cita Completada"
        PROMOCION = "promocion", "Promoción"
    
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones_recibidas"
    )
    cita = models.ForeignKey(
        "scheduling.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificaciones_enviadas"
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoNotificacion.choices,
        default=TipoNotificacion.RECORDATORIO_CITA
    )
    asunto = models.CharField(max_length=200)
    enviado_el = models.DateTimeField(auto_now_add=True, db_index=True)
    exitoso = models.BooleanField(default=True)
    error = models.TextField(blank=True, help_text="Mensaje de error si falla")
    
    class Meta:
        ordering = ["-enviado_el"]
        verbose_name = "Notificación Email"
        verbose_name_plural = "Notificaciones Email"
        indexes = [
            models.Index(fields=["destinatario", "tipo", "enviado_el"]),
            models.Index(fields=["cita", "tipo"]),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} → {self.destinatario.email}"
class LogActividad(models.Model):
    class TipoAccion(models.TextChoices):
        CREAR_BARBERIA = "crear_barberia", "Crear Barbería"
        SUSPENDER_BARBERIA = "suspender_barberia", "Suspender Barbería"
        CAMBIAR_PLAN = "cambiar_plan", "Cambiar Plan"
        PAGO_EXITOSO = "pago_exitoso", "Pago Exitoso"
        PAGO_FALLIDO = "pago_fallido", "Pago Fallido"
        LOGIN = "login", "Login"
        ERROR_SISTEMA = "error_sistema", "Error Sistema"

    nosotros = models.ForeignKey(Nosotros, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=30, choices=TipoAccion.choices)
    descripcion = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} - {self.accion}"
class DiaExcepcional(models.Model):
    class TipoExcepcion(models.TextChoices):
        CERRADO = 'cerrado', 'Cerrado'
        HORARIO_ESPECIAL = 'horario_especial', 'Horario Especial'
    
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='dias_excepcionales')
    fecha = models.DateField()
    tipo = models.CharField(max_length=20, choices=TipoExcepcion.choices)
    
    # Solo si es horario especial
    hora_apertura = models.TimeField(null=True, blank=True)
    hora_cierre = models.TimeField(null=True, blank=True)
    
    motivo = models.CharField(max_length=200, blank=True, help_text="Ej: Día festivo, evento privado")
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bf_dias_excepcionales'
        unique_together = ['sucursal', 'fecha']
        verbose_name = 'Día Excepcional'
        verbose_name_plural = 'Días Excepcionales'
    
    def __str__(self):
        return f"{self.sucursal.nombre} - {self.fecha} ({self.get_tipo_display()})"
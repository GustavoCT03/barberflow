from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone
import uuid
# Create your models here.
def get_expiration_date():
    return timezone.now() + timezone.timedelta(days=7)
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email debe ser obligatorio")
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
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser debe tener is_superuser=True.")
        return self._create_user(email, password, **extra_fields)
class User(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin (Licencias)"
        ADMIN_BARBERIA = "admin_barberia", "Admin Barberia"
        BARBERO = "barbero", "Barbero"
        CLIENTE = "cliente", "Cliente"
    email = models.EmailField("Correo", unique=True, db_index=True)
    nombre = models.CharField("Nombre", max_length=150)
    rol = models.CharField("Rol", max_length=20, choices=Roles.choices, default=Roles.CLIENTE, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["nombre"]
    def __str__(self):
        return f"{self.nombre} <{self.email}>"
phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Ingrese un telefono valido entre 7 a 15 digito (opcionalmente con + al inicio)."
)
class Cliente(models.Model):
    """
    Perfil de cliente. El teléfono es OPCIONAL (para SMS si lo desea).
    El correo viene del User y es obligatorio para login/recordatorios/ofertas.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cliente")

    telefono = models.CharField(
        "Teléfono (opcional)",
        max_length=16,
        validators=[phone_validator],
        blank=True,   # <- opcional en formularios
        null=True,    # <- opcional en base de datos
    )
    acepta_sms = models.BooleanField(
        "Deseo recibir recordatorios por SMS (opcional)",
        default=False
    )
    acepta_email = models.BooleanField(
        "Deseo recibir correos de confirmación/ofertas",
        default=True
    )

    def __str__(self):
        return f"Cliente: {self.user.nombre} ({self.user.email})"
class Nosotros(models.Model):
    nombre = models.CharField(max_length=150)
    plan = models.CharField(max_length=50, default="trial")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Barberia(models.Model):
    """
    Representa una barbería que tiene licencia activa.
    Un Nosotros puede tener múltiples barberías (según su plan).
    """
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE, related_name="barberias")
    nombre = models.CharField("Nombre de la barbería", max_length=150)
    descripcion = models.TextField("Descripción", blank=True)
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
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=120)
    sucursal_principal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
class InvitacionBarbero(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    usado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField(default=get_expiration_date)

    def valido(self):
        return (not self.usado) and timezone.now() < self.expira

    def __str__(self):
        return f"{self.email} ({self.nosotros})"
    


    


class Servicio(models.Model):
    barberia = models.ForeignKey(Barberia, on_delete=models.CASCADE, related_name="servicios")
    nombre = models.CharField("Nombre del servicio", max_length=100)
    descripcion = models.TextField("Descripción", blank=True)
    duracion_minutos = models.PositiveIntegerField("Duración (min)", default=30)
    precio = models.DecimalField("Precio", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
    
    def __str__(self):
        return f"{self.nombre} - ${self.precio} ({self.duracion_minutos} min)"


    
class HorarioDisponibilidad(models.Model):
    """Esta wea es para q los weas de los barberos o veneckers pongan sus horarios disponibles para q los clientes culiaos puedan pedir hora"""
    class DiaSemana(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.IntegerField("Día de la semana", choices=DiaSemana.choices)
    hora_inicio = models.TimeField("Hora de inicio")
    hora_fin = models.TimeField("Hora de fin")
    activo = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ["barbero", "dia_semana", "hora_inicio"]
        verbose_name = "Horario de disponibilidad"
        verbose_name_plural = "Horarios de disponibilidad"
        unique_together = ["barbero", "dia_semana", "hora_inicio"]
    def __str__(self):
        return f"{self.barbero.nombre} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"
class Cita(models.Model):
    """
    Reserva de un cliente con un barbero para un servicio específico.
    """
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        EN_PROCESO = "en_proceso", "En Proceso"
        COMPLETADA = "completada", "Completada"
        CANCELADA_CLIENTE = "cancelada_cliente", "Cancelada por Cliente"
        CANCELADA_ADMIN = "cancelada_admin", "Cancelada por Admin"
        NO_ASISTIO = "no_asistio", "No Asistió"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="citas")
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name="citas")
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha = models.DateField("Fecha de la cita")
    hora_inicio = models.TimeField("Hora de inicio")
    hora_fin = models.TimeField("Hora de fin")
    
    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    notas_cliente = models.TextField("Notas del cliente", blank=True)
    notas_admin = models.TextField("Notas internas (admin)", blank=True)
    
    confirmada_email = models.BooleanField("Email de confirmación enviado", default=False)
    recordatorio_enviado = models.BooleanField("Recordatorio enviado", default=False)
    
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)
    cancelado_en = models.DateTimeField("Fecha de cancelación", null=True, blank=True)

    class Meta:
        ordering = ["-fecha", "-hora_inicio"]
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        indexes = [
            models.Index(fields=["fecha", "barbero"]),
            models.Index(fields=["cliente", "fecha"]),
        ]

    def __str__(self):
        return f"Cita {self.id} - {self.cliente.user.nombre} con {self.barbero.nombre} el {self.fecha} {self.hora_inicio}"

    def cancelar(self, cancelado_por="cliente"):
        """Marcar cita como cancelada"""
        self.estado = self.Estado.CANCELADA_CLIENTE if cancelado_por == "cliente" else self.Estado.CANCELADA_ADMIN
        self.cancelado_en = timezone.now()
        self.save()

    def confirmar_asistencia(self):
        """Marcar que el cliente llegó (HU22)"""
        self.estado = self.Estado.COMPLETADA
        self.save()

    def esta_activa(self):
        """Verifica si la cita está en estado que permite modificaciones"""
        return self.estado in [self.Estado.PENDIENTE, self.Estado.CONFIRMADA]


# ============================================================
# VALORACIONES / RESEÑAS (HU17, HU41, HU42)
# ============================================================
class Valoracion(models.Model):
    """
    Calificación que un cliente da a un barbero después de la cita.
    """
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name="valoracion")
    puntuacion = models.PositiveIntegerField(
        "Puntuación (1-5 estrellas)",
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentario = models.TextField("Comentario", blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "Valoración"
        verbose_name_plural = "Valoraciones"

    def __str__(self):
        return f"Valoración {self.puntuacion}★ - {self.cita.barbero.nombre} por {self.cita.cliente.user.nombre}"


# ============================================================
# PROMOCIONES (HU21, HU44)
# ============================================================
class Promocion(models.Model):
    """
    Descuentos o promociones que el admin de barbería envía a clientes.
    """
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE, related_name="promociones")
    titulo = models.CharField("Título", max_length=150)
    descripcion = models.TextField("Descripción")
    descuento_porcentaje = models.DecimalField(
        "Descuento (%)",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    codigo = models.CharField("Código promocional", max_length=20, unique=True, blank=True)
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin = models.DateField("Fecha de fin")
    activa = models.BooleanField(default=True)
    clientes = models.ManyToManyField(Cliente, blank=True, related_name="promociones_recibidas")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_inicio"]
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"

    def __str__(self):
        return f"{self.titulo} ({self.descuento_porcentaje}% OFF)"

    def esta_vigente(self):
        hoy = timezone.now().date()
        return self.activa and self.fecha_inicio <= hoy <= self.fecha_fin


# ============================================================
# PLANES DE LICENCIA SAAS (HU28, HU46, HU47)
# ============================================================
class Plan(models.Model):
    """
    Planes de suscripción (Trial, Básico, Profesional, Empresarial).
    """
    class TipoPlan(models.TextChoices):
        TRIAL = "trial", "Trial (7 días gratis)"
        BASICO = "basico", "Básico"
        PROFESIONAL = "profesional", "Profesional"
        EMPRESARIAL = "empresarial", "Empresarial"

    class Periodicidad(models.TextChoices):
        MENSUAL = "mensual", "Mensual"
        ANUAL = "anual", "Anual"

    nombre = models.CharField("Nombre del plan", max_length=50, choices=TipoPlan.choices, unique=True)
    periodicidad = models.CharField("Periodicidad", max_length=10, choices=Periodicidad.choices, default=Periodicidad.MENSUAL)
    precio = models.DecimalField("Precio", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    max_barberos = models.PositiveIntegerField("Máximo de barberos", default=1)
    max_sucursales = models.PositiveIntegerField("Máximo de sucursales", default=1)
    
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plan de licencia"
        verbose_name_plural = "Planes de licencia"

    def __str__(self):
        return f"{self.get_nombre_display()} - {self.get_periodicidad_display()} (${self.precio})"


# ============================================================
# LICENCIA ACTIVA (HU46, HU47)
# ============================================================
class Licencia(models.Model):
    """
    Licencia activa de una barbería. Vincula Nosotros con un Plan y fechas.
    """
    nosotros = models.OneToOneField(Nosotros, on_delete=models.CASCADE, related_name="licencia")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_expiracion = models.DateField("Fecha de expiración")
    
    activa = models.BooleanField(default=True, db_index=True)
    pago_pendiente = models.BooleanField("Pago pendiente", default=False)
    
    stripe_subscription_id = models.CharField("Stripe Subscription ID", max_length=100, blank=True)
    
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Licencia"
        verbose_name_plural = "Licencias"

    def __str__(self):
        return f"Licencia {self.nosotros.nombre} - {self.plan.nombre} (hasta {self.fecha_expiracion})"

    def esta_activa(self):
        """Verifica si la licencia está vigente"""
        hoy = timezone.now().date()
        return self.activa and not self.pago_pendiente and self.fecha_expiracion >= hoy

    def suspender(self):
        """Suspende la licencia (HU47)"""
        self.activa = False
        self.nosotros.activo = False
        self.nosotros.save()
        self.save()


# ============================================================
# LOGS DE ACTIVIDAD (HU31, HU45)
# ============================================================
class LogActividad(models.Model):
    """
    Registro de acciones importantes para auditoría SaaS.
    """
    class TipoAccion(models.TextChoices):
        CREAR_BARBERIA = "crear_barberia", "Crear Barbería"
        SUSPENDER_BARBERIA = "suspender_barberia", "Suspender Barbería"
        CAMBIAR_PLAN = "cambiar_plan", "Cambiar Plan"
        PAGO_EXITOSO = "pago_exitoso", "Pago Exitoso"
        PAGO_FALLIDO = "pago_fallido", "Pago Fallido"
        LOGIN = "login", "Login"
        ERROR_SISTEMA = "error_sistema", "Error del Sistema"

    nosotros = models.ForeignKey(Nosotros, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField("Acción", max_length=30, choices=TipoAccion.choices)
    descripcion = models.TextField("Descripción", blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    timestamp = models.DateTimeField("Fecha/Hora", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Log de actividad"
        verbose_name_plural = "Logs de actividad"

    def __str__(self):
        return f"{self.timestamp} - {self.accion} - {self.usuario or 'Sistema'}"
    




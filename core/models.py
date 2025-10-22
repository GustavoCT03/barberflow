from django.contrib.auth.base_user import AbstractBaseUser,   BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid
# Create your models here.
class UserManager(BaseUserManager):
    use_in_migrations = True
    def _create_user(self, username, email, password, **extra_fields):
        """""Aqui lo que hacemos es habilitar que se pueda crear y guardar un usuario cualqueira con email como identjficador principal, Por ende el emial es obligatorio y el telefono es opcional en el perfil."""
        if not email:
            raise ValueError("El email debe ser obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user( email, password, **extra_fields)
    def create_superuser(self,email, password=None, **extra_fields):
        extra_fields.set.default("is_staff", True)
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
    nombre = models.Charfield("Nombre", max_length=150)
    rol = models.CharField("Rol", max_length=20, choices=Roles.choices, default=Roles.CLIENTE)
    
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
    plan = models.Charfield(max_length=50, default="trial")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre  
    
class Perfil(models.Model):
    class Rol(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin (Licencias)"
        ADMIN_BARBERIA = "admin_barberia", "Admin Barberia"
        BARBERO = "barbero", "Barbero"
        Cliente = "cliente", "Cliente"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choiches=Rol.choiches, default=Rol.Cliente)
    nosotros = models.ForeignKey(Nosotros, on_delete=models.SET.NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} [{self.rol}]"
class Sucursal(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE)
    nombre = models.Charfield(max_length=150)
    direccion = models.Charfield(max_length=200, blank=True)
    telefono = models.Charfield(max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.nosotros.nombre})"
class Barbero(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.Charfield(max_length=120)
    sucursal_principal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
class InvitacionBarbero(models.Model):
    nosotros = models.ForeignKey(Nosotros, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    token = models.UUIDGField(default=uuid.uuid4, unique=True, editable=False)
    usado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField(default=lambda: timezone.now() + timezone.timedelta(days=7))
    def valido(self):
        return (not self.usado) and timezone.now() < self.expira
    def __str__(self):
        return f"{self.email ({self.nosotros})}"
    


    

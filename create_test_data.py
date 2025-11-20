import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BarberFlow.settings')
django.setup()

from core.models import User, Nosotros, Barberia, Sucursal, Servicio, Barbero, HorarioDisponibilidad
from datetime import time

# Crear superusuario licenciante
admin = User.objects.create_superuser(
    email='admin@barberflow.com',
    password='admin123',
    nombre='Super Admin'
)
admin.rol = 'superadmin'
admin.save()

# Crear licenciatario
nosotros = Nosotros.objects.create(
    nombre='BarberShop Pro',
    plan='profesional',
    activo=True
)

# Crear barbería
barberia = Barberia.objects.create(
    nosotros=nosotros,
    nombre='Barbería Centro',
    descripcion='La mejor barbería del centro',
    activa=True
)

# Crear sucursal
sucursal = Sucursal.objects.create(
    barberia=barberia,
    nombre='Sucursal Principal',
    direccion='Av. Principal 123',
    telefono='+56912345678',
    activo=True
)

# Crear servicios
corte = Servicio.objects.create(
    barberia=barberia,
    nombre='Corte de Cabello',
    descripcion='Corte clásico o moderno',
    duracion_minutos=30,
    precio=10000,
    activo=True
)

barba = Servicio.objects.create(
    barberia=barberia,
    nombre='Arreglo de Barba',
    descripcion='Recorte y perfilado',
    duracion_minutos=20,
    precio=7000,
    activo=True
)

# Crear barbero
user_barbero = User.objects.create_user(
    email='barbero@barberflow.com',
    password='barbero123',
    nombre='Juan Pérez'
)
user_barbero.rol = 'barbero'
user_barbero.save()

barbero = Barbero.objects.create(
    nosotros=nosotros,
    user=user_barbero,
    nombre='Juan Pérez',
    sucursal_principal=sucursal,
    activo=True
)

# Crear horarios (Lunes a Viernes 9:00-18:00)
for dia in range(5):  # 0=Lunes, 4=Viernes
    HorarioDisponibilidad.objects.create(
        barbero=barbero,
        dia_semana=dia,
        hora_inicio=time(9, 0),
        hora_fin=time(18, 0),
        activo=True
    )

# Crear cliente
user_cliente = User.objects.create_user(
    email='cliente@test.com',
    password='cliente123',
    nombre='María González'
)
user_cliente.rol = 'cliente'
user_cliente.save()

print("✅ Datos de prueba creados exitosamente!")
print("\n📋 Credenciales:")
print("Admin: admin@barberflow.com / admin123")
print("Barbero: barbero@barberflow.com / barbero123")
print("Cliente: cliente@test.com / cliente123")
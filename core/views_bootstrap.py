from django.http import HttpResponse
from django.utils import timezone
import datetime

from django.contrib.auth import get_user_model
from core.models import Nosotros, Plan, Licencia, Barbero
from scheduling.models import Sucursal

User = get_user_model()

def bootstrap_init(request):
    """
    Inicializa SuperAdmin, 3 barberías, 3 admins y 3 barberos.
    SOLO se ejecuta si la base está vacía.
    """
    mensajes = []

    # ------------------------------
    # 1. SUPERADMIN
    # ------------------------------
    if not User.objects.filter(rol=User.Roles.SUPERADMIN).exists():
        User.objects.create_user(
            email="superadmin@barberflow.cl",
            password="admin123",
            nombre="SuperAdmin",
            rol=User.Roles.SUPERADMIN,
        )
        mensajes.append("✔ SuperAdmin creado")
    else:
        mensajes.append("SuperAdmin ya existe")

    # ------------------------------
    # 2. PLAN ILIMITADO
    # ------------------------------
    if not Plan.objects.exists():
        plan = Plan.objects.create(
            nombre="empresarial",
            periodicidad="mensual",
            precio=0,
            max_barberos=999,
            max_sucursales=999,
            activo=True
        )
        mensajes.append("✔ Plan empresarial creado")
    else:
        plan = Plan.objects.first()
        mensajes.append("Plan ya existe")

    # ------------------------------
    # 3. CREAR 3 BARBERÍAS
    # ------------------------------
    barberias_creadas = []

    if Nosotros.objects.count() < 3:
        nombres = ["Barbería Alpha", "Barbería Bravo", "Barbería Charlie"]

        for nombre in nombres:
            b = Nosotros.objects.create(nombre=nombre, activo=True)
            barberias_creadas.append(b)
        mensajes.append("✔ 3 Barberías creadas")
    else:
        barberias_creadas = list(Nosotros.objects.all()[:3])
        mensajes.append("Ya existen barberías")

    # ------------------------------
    # 4. LICENCIAS PARA CADA BARBERÍA
    # ------------------------------
    for barberia in barberias_creadas:
        if not hasattr(barberia, "licencia"):
            Licencia.objects.create(
                nosotros=barberia,
                plan=plan,
                fecha_inicio=timezone.now().date(),
                fecha_expiracion=timezone.now().date() + datetime.timedelta(days=3650),
                activa=True,
            )
            mensajes.append(f"✔ Licencia creada para {barberia.nombre}")
        else:
            mensajes.append(f"Licencia ya existe para {barberia.nombre}")

    # ------------------------------
    # 5. ADMIN + BARBERO para cada barbería
    # ------------------------------
    for index, barberia in enumerate(barberias_creadas, start=1):

        # Crear Admin Barbería
        email_admin = f"admin{index}@barberflow.cl"
        if not User.objects.filter(email=email_admin).exists():
            admin = User.objects.create_user(
                email=email_admin,
                password="admin123",
                nombre=f"Admin {barberia.nombre}",
                rol=User.Roles.ADMIN_BARBERIA
            )
            admin.nosotros = barberia
            admin.save()
            mensajes.append(f"✔ Admin creado para {barberia.nombre}")
        else:
            admin = User.objects.get(email=email_admin)
            mensajes.append(f"Admin ya existe para {barberia.nombre}")

        # Crear Sucursal para asignar barbero
        sucursal, created = Sucursal.objects.get_or_create(
            barberia=barberia,
            nombre="Sucursal Principal",
            defaults={"direccion": "Dirección pendiente"}
        )

        # Crear Barbero
        email_barbero = f"barbero{index}@barberflow.cl"
        if not User.objects.filter(email=email_barbero).exists():
            u_barbero = User.objects.create_user(
                email=email_barbero,
                password="admin123",
                nombre=f"Barbero {barberia.nombre}",
                rol=User.Roles.BARBERO
            )
            barbero = Barbero.objects.create(
                user=u_barbero,
                nombre=u_barbero.nombre,
                nosotros=barberia,
                activo=True
            )
            mensajes.append(f"✔ Barbero creado para {barberia.nombre}")
        else:
            mensajes.append(f"Barbero ya existe para {barberia.nombre}")

    # ------------------------------
    # 6. Respuesta ZEN y profesional :D
    # ------------------------------
    html = "<h2>Bootstrap Ejecutado</h2><ul>"
    for m in mensajes:
        html += f"<li>{m}</li>"
    html += "</ul>"

    return HttpResponse(html)

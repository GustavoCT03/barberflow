from django.http import HttpResponse
from django.utils import timezone
import datetime

from django.contrib.auth import get_user_model
from core.models import (
    Nosotros, Barberia, Sucursal,
    Barbero, Plan, Licencia
)

User = get_user_model()


def bootstrap_init(request):
    """
    Inicializa la plataforma completa:
    - SuperAdmin
    - 3 Nosotros (Alpha, Bravo, Charlie)
    - 1 Barberia por cada Nosotros
    - 1 Sucursal por Barberia
    - 1 Admin Barberia por Nosotros
    - 1 Barbero por Nosotros
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
    # 2. PLAN EMPRESARIAL
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
    # 3. CREAR LOS 3 NOSOTROS
    # ------------------------------
    nombres = ["Alpha", "Bravo", "Charlie"]
    instancias_nosotros = []

    if Nosotros.objects.count() < 3:
        for n in nombres:
            inst = Nosotros.objects.create(nombre=f"Barberia {n}", activo=True)
            instancias_nosotros.append(inst)
        mensajes.append("✔ 3 entradas Nosotros creadas")
    else:
        instancias_nosotros = list(Nosotros.objects.all()[:3])
        mensajes.append("Ya existen entradas Nosotros")

    # ------------------------------
    # 4. CREAR BARBERIA + SUCURSAL + ADMIN + BARBERO
    # ------------------------------
    for idx, nos in enumerate(instancias_nosotros, start=1):

        # LICENCIA
        if not hasattr(nos, "licencia"):
            Licencia.objects.create(
                nosotros=nos,
                plan=plan,
                fecha_inicio=timezone.now().date(),
                fecha_expiracion=timezone.now().date() + datetime.timedelta(days=3650),
                activa=True,
            )
            mensajes.append(f"✔ Licencia creada para {nos.nombre}")
        else:
            mensajes.append(f"Licencia ya existe para {nos.nombre}")

        # BARBERIA
        barberia, _ = Barberia.objects.get_or_create(
            nosotros=nos,
            nombre=f"{nos.nombre} Central"
        )

        # SUCURSAL PRINCIPAL
        sucursal, _ = Sucursal.objects.get_or_create(
            barberia=barberia,
            nombre="Sucursal Principal",
            defaults={"direccion": "Direccion pendiente"}
        )

        # ADMIN BARBERIA
        email_admin = f"admin{idx}@barberflow.cl"
        if not User.objects.filter(email=email_admin).exists():
            admin = User.objects.create_user(
                email=email_admin,
                password="admin123",
                nombre=f"Admin {nos.nombre}",
                rol=User.Roles.ADMIN_BARBERIA
            )
            admin.nosotros = nos
            admin.barberia = barberia       # ← VITAL
            admin.save()
            mensajes.append(f"✔ Admin creado para {nos.nombre}")
        else:
            mensajes.append(f"Admin ya existe para {nos.nombre}")

        # BARBERO
        email_barbero = f"barbero{idx}@barberflow.cl"
        if not User.objects.filter(email=email_barbero).exists():
            ub = User.objects.create_user(
                email=email_barbero,
                password="admin123",
                nombre=f"Barbero {nos.nombre}",
                rol=User.Roles.BARBERO
            )

            Barbero.objects.create(
                user=ub,
                nombre=ub.nombre,
                nosotros=nos,
                sucursal_principal=sucursal,
                activo=True
            )

            mensajes.append(f"✔ Barbero creado para {nos.nombre}")
        else:
            mensajes.append(f"Barbero ya existe para {nos.nombre}")

    # ------------------------------
    # 5. RESPUESTA HTML
    # ------------------------------
    html = "<h2>Bootstrap Ejecutado</h2><ul>"
    for m in mensajes:
        html += f"<li>{m}</li>"
    html += "</ul>"

    return HttpResponse(html)

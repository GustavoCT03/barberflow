from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta 
from django.db.models import Count, Q, Avg
from datetime import date, timedelta
import csv
from django.http import HttpResponse
from django.db import models
from icalendar import Calendar, Event
from django.http import HttpResponse

from core.models import (
    Nosotros,
    Sucursal,
    InvitacionBarbero,
    User,
    Barbero,
    Servicio,
)
from core.decorators import role_required
from .forms import SucursalCreateForm, SucursalUpdateForm
from scheduling.forms   import ReagendarCitaForm, CancelarCitaForm, CompletarCitaForm
from scheduling.models import Cita,Promocion  # ← AGREGA ESTA LÍNEA
from .forms_servicios import ServicioForm
import json
from django.db.models.functions import TruncDate
from core.models import DiaExcepcional, HorarioDisponibilidad
from .forms_filtros import FiltroCitasAdminForm





# Helper: obtener la barbería (Nosotros) asociada al usuario
def get_nosotros_from_user(user):
    """
    Dado un usuario, devuelve la instancia de 'Nosotros' asociada.

    - Para BARBERO: usa Barbero.nosotros
    - Para ADMIN_BARBERIA: usa user.barberia.nosotros (campo que llenamos en bootstrap)
    """
    # Caso 1: Barbero
    if hasattr(user, "barbero") and user.barbero is not None:
        return user.barbero.nosotros

    # Caso 2: Admin de barbería
    if getattr(user, "rol", None) == User.Roles.ADMIN_BARBERIA:
        barberia = getattr(user, "barberia", None)
        if barberia is not None:
            return barberia.nosotros

    # Otros roles (superadmin, cliente, etc.) -> por ahora None
    return None

# Helpers de licencia
def _licencia_activa(licencia):
    try:
        return licencia.esta_activa()
    except Exception:
        exp = getattr(licencia, "fecha_expiracion", None)
        activa_flag = getattr(licencia, "activa", True)
        return bool(activa_flag and (exp is None or exp >= timezone.now()))


def _puede_agregar_sucursal(nosotros, licencia):
    try:
        return licencia.puede_agregar_sucursal(nosotros)
    except Exception:
        max_s = getattr(licencia, "max_sucursales", None)
        if max_s is None:
            return True
        return Sucursal.objects.filter(nosotros=nosotros).count() < max_s


def _puede_agregar_barbero(nosotros, licencia):
    try:
        return licencia.puede_agregar_barbero(nosotros)
    except Exception:
        max_b = getattr(licencia, "max_barberos", None)
        if max_b is None:
            return True
        return Barbero.objects.filter(nosotros=nosotros, activo=True).count() < max_b


# Superadmin: panel de licencias
@login_required
@role_required(User.Roles.SUPERADMIN)
def panel_licencias(request):
    return render(request, "dashboard/panel_licencias.html")


# Admin de barbería: panel principal
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def panel_admin_barberia(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("login")
    
    sucursales = Sucursal.objects.filter(barberia__nosotros=nosotros)
    servicios = Servicio.objects.filter(barberia__nosotros=nosotros, activo=True)[:5]
    
    # KPIs últimos 7 días
    hace_7 = timezone.now() - timedelta(days=7)
    citas_periodo = Cita.objects.filter(
        barbero__nosotros=nosotros,
        creada_en__gte=hace_7
    )
    
    total = citas_periodo.count()
    completadas = citas_periodo.filter(estado=Cita.Estado.COMPLETADA).count()
    no_shows = citas_periodo.filter(estado=Cita.Estado.NO_SHOW).count()
    
    # Tasa de ocupación (horas reservadas / horas disponibles)
    barberos_activos = Barbero.objects.filter(nosotros=nosotros, activo=True).count()
    horas_disponibles = barberos_activos * 8 * 7  # 8h/día, 7 días
    horas_reservadas = total * 0.5  # asume 30min promedio por cita
    
    ocupacion = int((horas_reservadas / horas_disponibles * 100)) if horas_disponibles else 0
    
    # Conversión lista espera (simplificado)
    conversion_15 = 0  # implementar cuando exista modelo Oferta15min
    
    kpi = {
        "ocupacion": ocupacion,
        "no_shows": no_shows,
        "conversion_15": conversion_15,
        "total_citas": total,
        "completadas": completadas,
    }
    
    context = {
        "nosotros": nosotros,
        "sucursales": sucursales,
        "servicios": servicios,
        "kpi": kpi,
    }
    return render(request, "dashboard/admin_sucursal.html", context)

def listar_citas_admin(request):
    """
    HU07: Vista para mostrar todas las citas de la barbería
    con filtros por fecha y barbero.
    """
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    # Base queryset
    citas = (
        Cita.objects.filter(barbero__nosotros=nosotros)
        .select_related("cliente", "servicio", "barbero", "sucursal")
        .order_by("fecha_hora")
    )

    # Form de filtros
    form = FiltroCitasAdminForm(request.GET or None, nosotros=nosotros)

    if form.is_valid():
        fecha = form.cleaned_data.get("fecha")
        barbero = form.cleaned_data.get("barbero")

        if fecha:
            citas = citas.filter(fecha_hora__date=fecha)

        if barbero:
            citas = citas.filter(barbero=barbero)

    return render(
        request,
        "dashboard/listar_citas_admin.html",
        {"citas": citas, "form": form}
    )
# Crear sucursal (Admin de barbería) con validación de licencia
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def sucursal_crear(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    licencia = getattr(nosotros, "licencia", None)
    if not licencia:
        messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
        return redirect("panel_admin_barberia")
    if not _licencia_activa(licencia):
        messages.error(request, "Tu licencia está vencida. Renueva para crear sucursales.")
        return redirect("panel_admin_barberia")
    if not _puede_agregar_sucursal(nosotros, licencia):
        max_s = getattr(licencia, "max_sucursales", 0)
        messages.error(request, f"Límite de sucursales alcanzado ({max_s}) para tu plan.")
        return redirect("panel_admin_barberia")

    form = SucursalCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        suc = form.save(commit=False)
        suc.nosotros = nosotros
        suc.save()
        messages.success(request, "Sucursal creada con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/sucursal_form.html", {"form": form, "modo": "crear"})


# Editar sucursal (Admin de barbería)
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def sucursal_editar(request, sucursal_id):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    suc = get_object_or_404(Sucursal, id=sucursal_id, nosotros=nosotros)
    form = SucursalUpdateForm(request.POST or None, instance=suc)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sucursal actualizada con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/sucursal_form.html", {"form": form, "modo": "editar", "sucursal": suc})


# Eliminar sucursal (Admin de barbería)
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def sucursal_eliminar(request, sucursal_id):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    suc = get_object_or_404(Sucursal, id=sucursal_id, nosotros=nosotros)
    if request.method == "POST":
        suc.delete()
        messages.success(request, "Sucursal eliminada con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/sucursal_confirm_delete.html", {"sucursal": suc})


# Crear invitación para barbero (Admin de barbería) con validación de licencia y límites
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def crear_invitacion_barbero(request):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    licencia = getattr(nosotros, "licencia", None)
    if not licencia:
        messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
        return redirect("panel_admin_barberia")
    if not _licencia_activa(licencia):
        messages.error(request, "Tu licencia está vencida. Renueva para invitar barberos.")
        return redirect("panel_admin_barberia")
    if not _puede_agregar_barbero(nosotros, licencia):
        max_b = getattr(licencia, "max_barberos", 0)
        messages.error(request, f"Límite de barberos alcanzado ({max_b}) para tu plan.")
        return redirect("panel_admin_barberia")

    if request.method == "POST":
        email = request.POST.get("email")
        sucursal_id = request.POST.get("sucursal_id")
        sucursal = Sucursal.objects.filter(id=sucursal_id, nosotros=nosotros).first()

        if User.objects.filter(email=email).exists():
            messages.error(request, "Ya existe un usuario con ese email.")
            return redirect("panel_admin_barberia")

        inv = InvitacionBarbero.objects.create(
            nosotros=nosotros,
            sucursal=sucursal,
            email=email
        )
        messages.success(request, f"Invitación generada con éxito. Enlace: /registro/barbero/{inv.token}/")
        return redirect("panel_admin_barberia")

    sucursales = Sucursal.objects.filter(nosotros=nosotros, activo=True)
    return render(request, "dashboard/invitaciones_form.html", {"sucursales": sucursales})


# Crear barbero directamente (Admin de barbería) con validación de licencia y límites
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def barbero_crear(request):
    """
    Permite al administrador crear directamente un barbero,
    sin esperar a que el barbero use la invitación.
    """

    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    # Validaciones de licencia
    licencia = getattr(nosotros, "licencia", None)
    if not licencia:
        messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
        return redirect("panel_admin_barberia")

    if not _licencia_activa(licencia):
        messages.error(request, "Tu licencia está vencida. Renueva para crear barberos.")
        return redirect("panel_admin_barberia")

    if not _puede_agregar_barbero(nosotros, licencia):
        max_b = getattr(licencia, "max_barberos", 0)
        messages.error(request, f"Límite de barberos alcanzado ({max_b}) para tu plan.")
        return redirect("panel_admin_barberia")

    if request.method == "POST":
        email = request.POST.get("email")
        nombre = request.POST.get("nombre")
        password = request.POST.get("password") or User.objects.make_random_password()

        if not email or not nombre:
            messages.error(request, "Nombre y email son obligatorios.")
            return redirect("barbero_crear")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Ya existe un usuario con ese email.")
            return redirect("barbero_crear")

        # Crear User
        user = User.objects.create_user(
            email=email,
            password=password,
            nombre=nombre,
            rol=User.Roles.BARBERO
        )

        # Crear Barbero
        Barbero.objects.create(
            user=user,
            nosotros=nosotros,
            nombre=nombre,
            activo=True
        )

        messages.success(request, f"Barbero '{nombre}' creado con éxito.")
        return redirect("panel_admin_barberia")

    return render(request, "dashboard/barbero_form.html")



# Activar/desactivar barbero (Admin de barbería) con validación al activar
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def barbero_toggle_activo(request, barbero_id):
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")

    barbero = get_object_or_404(Barbero, id=barbero_id, nosotros=nosotros)

    # Si vamos a activar, validar límites de licencia
    if not barbero.activo:
        licencia = getattr(nosotros, "licencia", None)
        if not licencia:
            messages.error(request, "Tu barbería no tiene una licencia activa asignada.")
            return redirect("panel_admin_barberia")
        if not _licencia_activa(licencia):
            messages.error(request, "Tu licencia está vencida. Renueva para activar barberos.")
            return redirect("panel_admin_barberia")
        if not _puede_agregar_barbero(nosotros, licencia):
            max_b = getattr(licencia, "max_barberos", 0)
            messages.error(request, f"Límite de barberos alcanzado ({max_b}) para tu plan.")
            return redirect("panel_admin_barberia")

    barbero.activo = not barbero.activo
    barbero.save()
    estado = "activado" if barbero.activo else "desactivado"
    messages.success(request, f"Barbero '{barbero.nombre}' {estado} con éxito.")
    return redirect("panel_admin_barberia")


# Panel barbero
@login_required
def panel_barbero(request):
    """Panel principal del barbero con agenda del día"""
    try:
        barbero = Barbero.objects.get(user=request.user)
    except Barbero.DoesNotExist:
        messages.error(request, "No tienes un perfil de barbero asignado")
        return redirect('login')
    
    # Obtener fecha seleccionada (hoy por defecto)
    fecha_str = request.GET.get('fecha', timezone.now().date().isoformat())
    fecha = datetime.fromisoformat(fecha_str).date()
    
    # Citas del día
    citas_dia = Cita.objects.filter(
        barbero=barbero,
        fecha_hora__date=fecha
    ).select_related('cliente', 'servicio', 'sucursal').order_by('fecha_hora')
    
    # Estadísticas del día
    total_citas = citas_dia.count()
    completadas = citas_dia.filter(estado='completada').count()
    pendientes = citas_dia.filter(estado='pendiente').count()
    
    context = {
        'barbero': barbero,
        'fecha': fecha,
        'citas_dia': citas_dia,
        'total_citas': total_citas,
        'completadas': completadas,
        'pendientes': pendientes,
    }
    
    return render(request, 'dashboard/panel_barbero.html', context)

@login_required
def marcar_cita_completada(request, cita_id):
    """HU22: Marcar cita como completada"""
    cita = get_object_or_404(Cita, id=cita_id)
    
    # Verificar que sea el barbero asignado
    try:
        barbero = Barbero.objects.get(user=request.user)
        if cita.barbero != barbero:
            messages.error(request, "No tienes permiso para esta cita")
            return redirect('panel_barbero')
    except Barbero.DoesNotExist:
        messages.error(request, "No eres un barbero registrado")
        return redirect('home')
    
    if cita.estado in [Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]:
        cita.completar()
        messages.success(request, f"Cita marcada como completada")
    else:
        messages.warning(request, "La cita no puede ser completada en su estado actual")
    
    return redirect('panel_barbero')


# Panel cliente
@login_required
@role_required(User.Roles.CLIENTE)
def panel_cliente(request):
    """HU48: Dashboard del cliente con estadísticas"""
    from django.db.models import Count, Sum, Avg
    
    total_citas = Cita.objects.filter(cliente=request.user).count()
    completadas = Cita.objects.filter(
        cliente=request.user,
        estado=Cita.Estado.COMPLETADA
    ).count()
    
    proximas = Cita.objects.filter(
        cliente=request.user,
        fecha_hora__gte=timezone.now(),
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
    ).select_related('barbero', 'servicio', 'sucursal').order_by('fecha_hora')[:5]
    
    # Barbero favorito
    barbero_fav = Cita.objects.filter(
        cliente=request.user,
        estado=Cita.Estado.COMPLETADA
    ).values('barbero__nombre').annotate(
        total=Count('id')
    ).order_by('-total').first()
    
    # Servicio más solicitado
    servicio_fav = Cita.objects.filter(
        cliente=request.user,
        estado=Cita.Estado.COMPLETADA
    ).values('servicio__nombre').annotate(
        total=Count('id')
    ).order_by('-total').first()
    
    # Gasto total
    gasto_total = Cita.objects.filter(
        cliente=request.user,
        estado=Cita.Estado.COMPLETADA
    ).aggregate(total=Sum('precio'))['total'] or 0
    
    # Puntos de fidelidad
    barberias_con_puntos = []
    for barberia_id, puntos in request.user.puntos_fidelidad.items():
        if puntos > 0:
            from core.models import Barberia, ProgramaFidelidad
            try:
                barberia = Barberia.objects.get(id=barberia_id)
                programa = ProgramaFidelidad.objects.get(barberia=barberia, activo=True)
                valor = float(puntos) * float(programa.pesos_por_punto)
                
                barberias_con_puntos.append({
                    'barberia': barberia,
                    'puntos': puntos,
                    'valor': valor
                })
            except (Barberia.DoesNotExist, ProgramaFidelidad.DoesNotExist):
                pass
    
    context = {
        'total_citas': total_citas,
        'completadas': completadas,
        'proximas_citas': proximas,
        'barbero_favorito': barbero_fav['barbero__nombre'] if barbero_fav else 'N/A',
        'servicio_favorito': servicio_fav['servicio__nombre'] if servicio_fav else 'N/A',
        'gasto_total': gasto_total,
        'barberias_con_puntos': barberias_con_puntos
    }
    return render(request, 'dashboard/panel_cliente.html', context)
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def exportar_citas_csv(request):
    """HU14: Exportar reporte de citas en CSV"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")
    
    # Filtros opcionales
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    
    citas = Cita.objects.filter(
        barbero__nosotros=nosotros
    ).select_related('cliente', 'barbero', 'servicio', 'sucursal').order_by('-fecha_hora')
    
    if desde:
        citas = citas.filter(fecha_hora__date__gte=desde)
    if hasta:
        citas = citas.filter(fecha_hora__date__lte=hasta)
    
    # Crear CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="citas_{timezone.now().date()}.csv"'
    response.write('\ufeff')  # BOM para Excel UTF-8
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Fecha', 'Hora', 'Cliente', 'Barbero', 'Servicio', 'Sucursal', 'Estado', 'Precio'])
    
    for c in citas:
        writer.writerow([
            c.id,
            c.fecha_hora.date(),
            c.fecha_hora.time(),
            c.cliente.nombre,
            c.barbero.nombre,
            c.servicio.nombre,
            c.sucursal.nombre,
            c.get_estado_display(),
            c.precio
        ])
    
    return response

@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def exportar_ingresos_csv(request):
    """HU14: Exportar reporte de ingresos por servicio"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")
    
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    
    citas = Cita.objects.filter(
        barbero__nosotros=nosotros,
        estado=Cita.Estado.COMPLETADA
    ).select_related('servicio')
    
    if desde:
        citas = citas.filter(fecha_hora__date__gte=desde)
    if hasta:
        citas = citas.filter(fecha_hora__date__lte=hasta)
    
    # Agrupar por servicio
    from django.db.models import Sum, Count
    resumen = citas.values('servicio__nombre').annotate(
        cantidad=Count('id'),
        total=Sum('precio')
    ).order_by('-total')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="ingresos_{timezone.now().date()}.csv"'
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['Servicio', 'Cantidad', 'Ingresos'])
    
    for r in resumen:
        writer.writerow([
            r['servicio__nombre'],
            r['cantidad'],
            r['total']
        ])
    
    return response
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def metricas_barberos(request):
    """HU43: Métricas individuales por barbero"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")
    
    desde = request.GET.get('desde', (timezone.now() - timedelta(days=30)).date())
    hasta = request.GET.get('hasta', timezone.now().date())
    
    barberos = Barbero.objects.filter(nosotros=nosotros, activo=True)
    estadisticas = []
    
    for barbero in barberos:
        citas = Cita.objects.filter(
            barbero=barbero,
            fecha_hora__date__gte=desde,
            fecha_hora__date__lte=hasta
        )
        
        total = citas.count()
        completadas = citas.filter(estado=Cita.Estado.COMPLETADA).count()
        canceladas = citas.filter(estado__in=[Cita.Estado.CANCELADA_CLIENTE, Cita.Estado.CANCELADA_ADMIN]).count()
        no_shows = citas.filter(estado=Cita.Estado.NO_SHOW).count()
        
        # Ingresos generados
        ingresos = citas.filter(estado=Cita.Estado.COMPLETADA).aggregate(
            total=models.Sum('precio')
        )['total'] or 0
        
        # Valoración promedio
        promedio_val = barbero.valoraciones.aggregate(
            avg=models.Avg('puntuacion')
        )['avg'] or 0
        
        estadisticas.append({
            'barbero': barbero,
            'total_citas': total,
            'completadas': completadas,
            'canceladas': canceladas,
            'no_shows': no_shows,
            'tasa_completado': int((completadas/total*100)) if total else 0,
            'ingresos': ingresos,
            'valoracion': round(promedio_val, 1)
        })
    
    context = {
        'estadisticas': estadisticas,
        'desde': desde,
        'hasta': hasta
    }
    return render(request, 'dashboard/metricas_barberos.html', context)
@login_required
def marcar_no_show(request, cita_id):
    """HU22 — Marcar cita como No-Show (barbero)"""

    # Obtener el barbero del usuario
    barbero = getattr(request.user, "barbero", None)
    if barbero is None:
        messages.error(request, "No eres un barbero registrado.")
        return redirect("home")

    # Asegurar que la cita pertenece al barbero
    cita = get_object_or_404(Cita, id=cita_id, barbero=barbero)

    # Estados permitidos en tu flujo real (según tu panel)
    estados_validos = [
        Cita.Estado.PENDIENTE,
        Cita.Estado.CONFIRMADA,
        Cita.Estado.EN_PROCESO,
    ]

    if cita.estado not in estados_validos:
        messages.warning(request, "No se puede marcar esta cita como No-Show.")
        return redirect("panel_barbero")

    # Marcar como no-show
    cita.estado = Cita.Estado.NO_SHOW
    cita.save()

    messages.success(request, "Cita marcada correctamente como No-Show.")
    return redirect("panel_barbero")

@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def estadisticas_ingresos(request):
    """HU30: Estadísticas de ingresos por período"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        messages.error(request, "No se encontró tu barbería asociada.")
        return redirect("panel_admin_barberia")
    
    periodo = request.GET.get('periodo', '30')  # días
    dias = int(periodo)
    
    fecha_inicio = timezone.now() - timedelta(days=dias)
    
    # Ingresos por día
    ingresos_diarios = Cita.objects.filter(
        barbero__nosotros=nosotros,
        estado=Cita.Estado.COMPLETADA,
        fecha_hora__gte=fecha_inicio
    ).annotate(
        dia=TruncDate('fecha_hora')
    ).values('dia').annotate(
        total=models.Sum('precio')
    ).order_by('dia')
    
    # Preparar datos para gráfico
    fechas = [item['dia'].strftime('%d/%m') for item in ingresos_diarios]
    montos = [float(item['total']) for item in ingresos_diarios]
    
    # Ingresos por servicio
    ingresos_servicios = Cita.objects.filter(
        barbero__nosotros=nosotros,
        estado=Cita.Estado.COMPLETADA,
        fecha_hora__gte=fecha_inicio
    ).values('servicio__nombre').annotate(
        total=models.Sum('precio'),
        cantidad=models.Count('id')
    ).order_by('-total')[:5]
    
    context = {
        'periodo': periodo,
        'fechas_json': json.dumps(fechas),
        'montos_json': json.dumps(montos),
        'ingresos_servicios': ingresos_servicios,
        'total_periodo': sum(montos),
        'promedio_diario': sum(montos) / dias if dias else 0
    }
    return render(request, 'dashboard/estadisticas_ingresos.html', context)
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def listar_promociones(request):
    """HU32: Listar promociones"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        return redirect("panel_admin_barberia")
    
    promociones = Promocion.objects.filter(
        barberia__nosotros=nosotros
    ).order_by('-creado_en')
    
    return render(request, 'dashboard/promociones_list.html', {
        'promociones': promociones
    })

@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def crear_promocion(request):
    """HU32: Crear promoción"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        return redirect("panel_admin_barberia")
    
    if request.method == 'POST':
        barberia = nosotros.barberias.first()
        
        promocion = Promocion.objects.create(
            barberia=barberia,
            nombre=request.POST['nombre'],
            codigo=request.POST['codigo'].upper(),
            tipo_descuento=request.POST['tipo_descuento'],
            valor=request.POST['valor'],
            fecha_inicio=request.POST['fecha_inicio'],
            fecha_fin=request.POST['fecha_fin'],
            usos_maximos=int(request.POST.get('usos_maximos', 0)),
            monto_minimo=request.POST.get('monto_minimo', 0),
            solo_nuevos_clientes='solo_nuevos' in request.POST
        )
        
        servicios_ids = request.POST.getlist('servicios')
        if servicios_ids:
            promocion.servicios.set(servicios_ids)
        
        messages.success(request, f"Promoción '{promocion.nombre}' creada exitosamente")
        return redirect('listar_promociones')
    
    servicios = Servicio.objects.filter(barberia__nosotros=nosotros)
    return render(request, 'dashboard/promocion_form.html', {
        'servicios': servicios
    })
@login_required
def exportar_agenda_ical(request):
    """HU37: Exportar agenda del barbero a iCal"""
    try:
        barbero = Barbero.objects.get(user=request.user)
    except Barbero.DoesNotExist:
        messages.error(request, "No eres un barbero registrado")
        return redirect('panel_barbero')
    
    # Crear calendario
    cal = Calendar()
    cal.add('prodid', '-//BarberFlow//ES')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', f'Agenda {barbero.nombre}')
    
    # Obtener citas próximas (30 días)
    fecha_inicio = timezone.now()
    fecha_fin = fecha_inicio + timedelta(days=30)
    
    citas = Cita.objects.filter(
        barbero=barbero,
        fecha_hora__gte=fecha_inicio,
        fecha_hora__lte=fecha_fin,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
    ).select_related('cliente', 'servicio', 'sucursal')
    
    for cita in citas:
        event = Event()
        event.add('summary', f'{cita.servicio.nombre} - {cita.cliente.nombre}')
        event.add('dtstart', cita.fecha_hora)
        event.add('dtend', cita.fecha_hora + timedelta(minutes=cita.servicio.duracion_minutos))
        event.add('location', f'{cita.sucursal.nombre}, {cita.sucursal.direccion}')
        
        event.add('uid', f'cita-{cita.id}@barberflow.com')
        event.add('status', 'CONFIRMED')
        
        cal.add_component(event)
    
    response = HttpResponse(cal.to_ical(), content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="agenda_{barbero.nombre}_{fecha_inicio.date()}.ics"'
    
    return response
@login_required
@role_required(User.Roles.ADMIN_BARBERIA)
def gestionar_dias_excepcionales(request):
    """HU40: Gestionar días festivos/excepcionales"""
    nosotros = get_nosotros_from_user(request.user)
    if not nosotros:
        return redirect("panel_admin_barberia")
    
    sucursales = Sucursal.objects.filter(barberia__nosotros=nosotros)
    
    if request.method == 'POST':
        from core.models import DiaExcepcional
        
        DiaExcepcional.objects.create(
            sucursal_id=request.POST['sucursal'],
            fecha=request.POST['fecha'],
            tipo=request.POST['tipo'],
            hora_apertura=request.POST.get('hora_apertura') or None,
            hora_cierre=request.POST.get('hora_cierre') or None,
            motivo=request.POST.get('motivo', '')
        )
        messages.success(request, "Día excepcional registrado")
        return redirect('gestionar_dias_excepcionales')
    
    excepciones = DiaExcepcional.objects.filter(
        sucursal__barberia__nosotros=nosotros,
        fecha__gte=timezone.now().date()
    ).order_by('fecha')
    
    return render(request, 'dashboard/dias_excepcionales.html', {
        'sucursales': sucursales,
        'excepciones': excepciones
    })
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.mail import send_mail
from scheduling.models import Cita
from scheduling.forms import ReagendarCitaForm, CancelarCitaForm


def reagendar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)

    if request.method == 'POST':
        form = ReagendarCitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()

            # Notificación vía email
            send_mail(
                'Tu cita fue reagendada',
                f'Hola {cita.cliente.nombre},\n\n'
                f'Tu cita ha sido reagendada para: {cita.fecha_hora}.\n'
                f'Barbería: {cita.sucursal.nombre}\n\n'
                f'— BarberFlow',
                'barberflow@system.com',
                [cita.cliente.email],
                fail_silently=True
            )

            messages.success(request, "Cita reagendada correctamente.")
            return redirect('listar_citas_admin')
    else:
        form = ReagendarCitaForm(instance=cita)

    return render(request, 'citas/reagendar_cita.html', {
        'form': form,
        'cita': cita
    })


def cancelar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)

    if request.method == 'POST':
        form = CancelarCitaForm(request.POST, instance=cita)
        if form.is_valid():
            cita.estado = 'CANCELADA'
            form.save()

            # Notificación al cliente
            send_mail(
                'Tu cita ha sido cancelada',
                f'Hola {cita.cliente.nombre},\n\n'
                f'Tu cita del {cita.fecha_hora} ha sido cancelada.\n'
                f'Motivo: {cita.motivo_cancelacion}\n\n'
                f'— BarberFlow',
                'barberflow@system.com',
                [cita.cliente.email],
                fail_silently=True
            )

            messages.success(request, "Cita cancelada correctamente.")
            return redirect('listar_citas_admin')
    else:
        form = CancelarCitaForm(instance=cita)

    return render(request, 'citas/cancelar_cita.html', {
        'form': form,
        'cita': cita
    })
def completar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)

    if cita.barber.user != request.user:
        messages.error(request, "No tienes permiso para completar esta cita.")
        return redirect('barber_dashboard')

    if request.method == 'POST':
        form = CompletarCitaForm(request.POST, instance=cita)
        if form.is_valid():
            cita.status = "COMPLETED"
            form.save()

            puntos = max(5, cita.service.price // 1000)
            cita.client.points += puntos
            cita.client.save()

            messages.success(request, f"Cita completada. +{puntos} puntos otorgados.")
            return redirect('barber_dashboard')

    else:
        form = CompletarCitaForm(instance=cita)

    return render(request, 'dashboard/citas/completar_cita.html', {
        'cita': cita,
        'form': form
    })
def completar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)

    if cita.barber.user != request.user:
        messages.error(request, "No tienes permiso para completar esta cita.")
        return redirect('barber_dashboard')

    if request.method == 'POST':
        form = CompletarCitaForm(request.POST, instance=cita)
        if form.is_valid():
            cita.status = "COMPLETED"
            form.save()

            puntos = max(5, cita.service.price // 1000)
            cita.client.points += puntos
            cita.client.save()

            messages.success(request, f"Cita completada. +{puntos} puntos otorgados.")
            return redirect('barber_dashboard')

    else:
        form = CompletarCitaForm(instance=cita)

    return render(request, 'dashboard/citas/completar_cita.html', {
        'cita': cita,
        'form': form
    })
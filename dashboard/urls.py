from django.urls import path
from dashboard import views
from dashboard import views_servicios
from django.urls import include


urlpatterns = [
    # Paneles
    path("licencias/", views.panel_licencias, name="panel_licencias"),
    path("admin/", views.panel_admin_barberia, name="panel_admin_barberia"),       
    path("barbero/", views.panel_barbero, name="panel_barbero"),
    path("cliente/", views.panel_cliente, name="panel_cliente"),
    path('exportar/citas/', views.exportar_citas_csv, name='exportar_citas'),
    path('exportar/ingresos/', views.exportar_ingresos_csv, name='exportar_ingresos'),
    path('metricas/barberos/', views.metricas_barberos, name='metricas_barberos'),
    path('cita/<int:cita_id>/completar/', views.marcar_cita_completada, name='marcar_cita_completada'),
    path('cita/<int:cita_id>/no-show/', views.marcar_no_show, name='marcar_no_show'),
    path('estadisticas/ingresos/', views.estadisticas_ingresos, name='estadisticas_ingresos'),
    path("admin/citas/", views.listar_citas_admin, name="listar_citas_admin"),
    path('cita/<int:cita_id>/reagendar/', views.reagendar_cita, name='reagendar_cita'),
    path('cita/<int:cita_id>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    path('cita/<int:cita_id>/completar/', views.completar_cita, name='completar_cita'),
    

    
    
    # Barbero acciones
    
    # Sucursales
    path("admin/sucursales/crear/", views.sucursal_crear, name="sucursal_crear"),
    path("admin/sucursales/<int:sucursal_id>/editar/", views.sucursal_editar, name="sucursal_editar"),
    path("admin/sucursales/<int:sucursal_id>/eliminar/", views.sucursal_eliminar, name="sucursal_eliminar"),
    
    # Barberos
    path("admin/barberos/crear/", views.barbero_crear, name="barbero_crear"),
    path("admin/barberos/<int:barbero_id>/toggle/", views.barbero_toggle_activo, name="barbero_toggle_activo"),
    path("admin/invitaciones/nueva/", views.crear_invitacion_barbero, name="crear_invitacion_barbero"),
    path("barbero/crear/", views.barbero_crear, name="barbero_crear"),

    
    # Servicios
    path("admin/servicios/", views_servicios.servicio_list, name="servicio_list"),
    path("admin/servicios/crear/", views_servicios.servicio_crear, name="servicio_crear"),
    path("admin/servicios/<int:servicio_id>/editar/", views_servicios.servicio_editar, name="servicio_editar"),
    path("admin/servicios/<int:servicio_id>/eliminar/", views_servicios.servicio_eliminar, name="servicio_eliminar"),
    path("admin/servicios/<int:servicio_id>/toggle/", views_servicios.servicio_toggle_activo, name="servicio_toggle_activo"),
]
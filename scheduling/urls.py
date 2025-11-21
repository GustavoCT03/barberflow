from django.urls import path
from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.seleccionar_barberia, name='seleccionar_barberia'),
    path('sucursal/<int:barberia_id>/', views.seleccionar_sucursal, name='seleccionar_sucursal'),
    path('servicio/<int:sucursal_id>/', views.seleccionar_servicio, name='seleccionar_servicio'),
    path('barbero/<int:sucursal_id>/<int:servicio_id>/', views.seleccionar_barbero_fecha, name='seleccionar_barbero_fecha'),
    path('confirmar/<int:sucursal_id>/<int:servicio_id>/<int:barbero_id>/', views.confirmar_reserva, name='confirmar_reserva'),
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('cita/<int:cita_id>/cancelar/', views.cancelar_cita, name='cancelar_cita'),  # ← NUEVA
    path('cita/<int:cita_id>/valorar/', views.valorar_cita, name='valorar_cita'),
    path('barbero/<int:barbero_id>/valoraciones/', views.ver_valoraciones_barbero, name='valoraciones_barbero'),
    path('waitlist/<int:barbero_id>/<int:servicio_id>/unirse/', views.unirse_waitlist, name='unirse_waitlist'),
]
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
]
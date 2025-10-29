"""
URL configuration for BarberFlow project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from accounts.views import login_view, logout_view, registro_cliente, route_by_role, registro_barbero_por_token
from dashboard.views import (
    panel_licencias, panel_admin_barberia, panel_barbero, panel_cliente,
    sucursal_crear, sucursal_editar, sucursal_eliminar, crear_invitacion_barbero
)

urlpatterns = [
    path('admin/', admin.site.urls),

    #auth#
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('registro/cliente/', registro_cliente, name='registro_cliente'),
    path('registro/barbero/<uuid:token>/', registro_barbero_por_token, name='registro_barbero'),

    # para la wea de rol#
    path('', route_by_role, name='route_by_role'),

    # Los paneles #
    path('panel/licencias/', panel_licencias, name='panel_licencias'),
    path('panel/admin/', panel_admin_barberia, name='panel_admin_barberia'),
    path('panel/barbero/', panel_barbero, name='panel_barbero'),
    path('panel/cliente/', panel_cliente, name='panel_cliente'),

    # Las Sucursales #
    path('panel/admin/sucursales/crear/', sucursal_crear, name='sucursal_crear'),
    path('panel/admin/sucursales/<int:sucursal_id>/editar/', sucursal_editar, name='sucursal_editar'),
    path('panel/admin/sucursales/<int:sucursal_id>/eliminar/', sucursal_eliminar, name='sucursal_eliminar'),

    # Las invitaciones para los venecos xddddddd#
    path('panel/admin/invitaciones/nueva/', crear_invitacion_barbero, name='crear_invitacion_barbero'),

]

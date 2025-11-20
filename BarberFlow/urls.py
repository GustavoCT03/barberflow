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
from django.urls import path, include
from accounts.views import (
    login_view, 
    logout_view, 
    registro_cliente, 
    route_by_role,
    registro_barbero_por_token
)

from dashboard.views import (
    panel_licencias, panel_admin_barberia, panel_barbero, panel_cliente,
    sucursal_crear, sucursal_editar, sucursal_eliminar, crear_invitacion_barbero
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('panel/', include('dashboard.urls')), 
    path('citas/', include('scheduling.urls')),
]
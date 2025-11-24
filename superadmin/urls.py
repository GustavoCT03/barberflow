from django.urls import path
from . import views
 
from licensing.views import planes_list
from superadmin import views


urlpatterns = [
    path("", views.panel_principal, name="superadmin_panel"),

    path("planes/", views.planes_list, name="superadmin_planes"),
    path("planes/nuevo/", views.plan_crear, name="superadmin_plan_crear"),
    path("planes/<int:id>/editar/", views.plan_editar, name="superadmin_plan_editar"),

    path("licencias/", views.licencias_list, name="superadmin_licencias"),
    path("barberias/", views.barberias_list, name="superadmin_barberias"),
]

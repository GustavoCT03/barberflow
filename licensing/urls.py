from django.urls import path
from . import views

urlpatterns = [
    path("", views.panel_licencias, name="panel_licencias"),
    path("planes/", views.planes_list, name="planes_list"),
    path("planes/crear/", views.plan_crear, name="plan_crear"),
    path("planes/<int:plan_id>/editar/", views.plan_editar, name="plan_editar"),
    path("planes/<int:plan_id>/eliminar/", views.plan_eliminar, name="plan_eliminar"),

    path("licencias/", views.licencias_list, name="licencias_list"),
    path("barberias/", views.barberias_list, name="barberias_list"),
]
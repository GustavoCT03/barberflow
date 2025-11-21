from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/cliente/', views.registro_cliente, name='registro_cliente'),
    path('registro/barbero/<uuid:token>/', views.registro_barbero_por_token, name='registro_barbero'),
    path('route/', views.route_by_role, name='route_by_role'),
    path('invitacion/<uuid:token>/', views.aceptar_invitacion_barbero, name='aceptar_invitacion'),
]
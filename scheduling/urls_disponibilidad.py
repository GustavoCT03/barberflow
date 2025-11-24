from django.urls import path
from . import views_disponibilidad

app_name = 'scheduling_disponibilidad'

urlpatterns = [
    path('disponibilidad/', views_disponibilidad.disponibilidad_list, name='disponibilidad_list'),
    path('disponibilidad/nueva/', views_disponibilidad.disponibilidad_create, name='disponibilidad_create'),
    path('disponibilidad/<int:pk>/editar/', views_disponibilidad.disponibilidad_update, name='disponibilidad_update'),
    path('disponibilidad/<int:pk>/eliminar/', views_disponibilidad.disponibilidad_delete, name='disponibilidad_delete'),
]
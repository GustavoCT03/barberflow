from django.contrib import admin
from .models import Cita, Valoracion

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'barbero', 'servicio', 'fecha_hora', 'estado']
    list_filter = ['estado', 'fecha_hora']
    search_fields = ['cliente__email', 'barbero__nombre']

@admin.register(Valoracion)
class ValoracionAdmin(admin.ModelAdmin):
    list_display = ('id', 'cita', 'barbero', 'puntuacion', 'fecha_cita', 'creada_en')
    list_filter = ('puntuacion', 'barbero')
    search_fields = ('cita__id', 'barbero__nombre', 'cliente__nombre')
    readonly_fields = ('creada_en',)

    def fecha_cita(self, obj):
        return obj.cita.fecha_hora
    fecha_cita.short_description = 'Fecha Cita'

# Register your models here.

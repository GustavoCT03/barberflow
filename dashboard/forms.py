from django import forms
from core.models import Sucursal, Servicio
from scheduling.models import Cita

class SucursalCreateForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ["nombre", "direccion", "telefono", "activo"]

class SucursalUpdateForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ["nombre", "direccion", "telefono", "activo"]
class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "descripcion", "duracion_minutos", "precio", "activo"]

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio < 0:
            raise forms.ValidationError("El precio debe ser positivo.")
        return precio

    def clean_duracion_minutos(self):
        duracion = self.cleaned_data["duracion_minutos"]
        if duracion <= 0:
            raise forms.ValidationError("La duración debe ser mayor a 0 minutos.")
        return duracion

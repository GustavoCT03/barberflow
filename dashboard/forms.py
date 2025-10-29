from django import forms
from core.models import Sucursal

class SucursalCreateForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ["nombre", "direccion", "telefono", "activo"]

class SucursalUpdateForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ["nombre", "direccion", "telefono", "activo"]

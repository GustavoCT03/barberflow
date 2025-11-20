from django import forms
from core.models import Servicio

class ServicioForm(forms.ModelForm):
    """
    Formulario para crear y editar servicios de la barbería.
    """
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'duracion_minutos', 'precio', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Corte de cabello'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del servicio (opcional)'
            }),
            'duracion_minutos': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '30',
                'min': '5',
                'step': '5'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'nombre': 'Nombre del servicio',
            'descripcion': 'Descripción',
            'duracion_minutos': 'Duración (minutos)',
            'precio': 'Precio ($)',
            'activo': 'Activo',
        }

    def clean_duracion_minutos(self):
        duracion = self.cleaned_data.get('duracion_minutos')
        if duracion and duracion < 5:
            raise forms.ValidationError("La duración mínima es 5 minutos.")
        return duracion

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio and precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio
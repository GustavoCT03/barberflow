from django import forms
from .models import Valoracion

class ValoracionForm(forms.ModelForm):
    class Meta:
        model = Valoracion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.RadioSelect(choices=[(i, '⭐' * i) for i in range(1, 6)]),
            'comentario': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': '¿Cómo fue tu experiencia?',
                'class': 'form-control'
            })
        }
        labels = {
            'puntuacion': 'Calificación',
            'comentario': 'Comentario (opcional)'
        }
class WaitlistForm(forms.Form):
    fecha_dia = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
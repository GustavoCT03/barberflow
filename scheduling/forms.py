from django import forms
from .models import Valoracion
from core.models import HorarioDisponibilidad
from .models import Cita

class ReagendarCitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['fecha_hora']
        widgets = {
            'fecha_hora': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
class CancelarCitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['motivo_cancelacion']
        widgets = {
            'motivo_cancelacion': forms.Textarea(attrs={'rows': 3}),
        }

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
class HorarioDisponibilidadForm(forms.ModelForm):
    class Meta:
        model = HorarioDisponibilidad
        fields = ['dia_semana', 'hora_inicio', 'hora_fin', 'activo']

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise forms.ValidationError("La hora de fin debe ser posterior a la de inicio.")
        return cleaned_data
class CompletarCitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['nota_interna']
        widgets = {
            'nota_interna': forms.Textarea(attrs={'rows': 3})
        }

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    remember_me = forms.BooleanField(required=False, label="Recordarme")

class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField(required=True)
    nombre = forms.CharField(max_length=150, required=True)
    telefono = forms.CharField(max_length=20, required=False)
    acepta_email = forms.BooleanField(required=False, initial=True, label="Acepto recibir emails")
    remember_me = forms.BooleanField(required=False, label="Recordarme")
    
    class Meta:
        model = User
        fields = ['email', 'nombre', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.nombre = self.cleaned_data['nombre']
        user.rol = 'cliente'
        if commit:
            user.save()
        return user
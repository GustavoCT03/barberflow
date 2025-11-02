from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField()
    remember_me = forms.BooleanField(required=False, initial=True, label="Mantener sesión iniciada")

    class Meta:
        model = User
        fields = ("email", "nombre", "password1", "password2")
class LoginForm(forms.Form):
    uemail = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
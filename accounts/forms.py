from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField()
    remember_me = forms.BooleanField(required=False, initial=True, label="Mantener sesión iniciada")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    remeber_me = forms.BooleanField(required=False, initial=True, label="Mantener sesión iniciada")
    
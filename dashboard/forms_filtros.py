from django import forms
from core.models import Barbero

class FiltroCitasAdminForm(forms.Form):
    fecha = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    barbero = forms.ModelChoiceField(
        queryset=Barbero.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        nosotros = kwargs.pop("nosotros", None)
        super().__init__(*args, **kwargs)

        if nosotros:
            self.fields["barbero"].queryset = Barbero.objects.filter(
                nosotros=nosotros,
                activo=True
            ).order_by("nombre")

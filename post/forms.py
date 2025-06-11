# post/forms.py
from django import forms
from .models import Cliente, Resena
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User # Para acceder a los campos del modelo User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Obligatorio. Se utilizará para notificaciones y reseteo de contraseña.")
    first_name = forms.CharField(max_length=100, required=False, help_text="Opcional.")
    last_name = forms.CharField(max_length=100, required=False, help_text="Opcional.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        # Asegurar que el email se guarde en el modelo User también,
        # ya que UserCreationForm por defecto podría no manejarlo si no está en sus fields directos.
        # Sin embargo, al añadirlo a Meta.fields, el super().save() debería manejarlo.
        # Esta asignación explícita es una doble seguridad o para si se quiere lógica extra.
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'email', 'telefono',
            'direccion', 'ciudad', 'codigo_postal', 'pais',
            'fecha_nacimiento', 'acepta_marketing' # Añadido acepta_marketing
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }
        # Podrías añadir labels o help_texts personalizados aquí si los del modelo no son suficientes.

class ResenaForm(forms.ModelForm):
    class Meta:
        model = Resena
        fields = ['titulo', 'comentario', 'calificacion']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 4}),
            'calificacion': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
        }

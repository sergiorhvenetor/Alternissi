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

class CheckoutForm(forms.Form):
    # Campos de Envío
    shipping_nombre = forms.CharField(max_length=100, label="Nombre")
    shipping_apellido = forms.CharField(max_length=100, label="Apellido")
    shipping_email = forms.EmailField(label="Email de Contacto")
    shipping_direccion1 = forms.CharField(max_length=255, label="Dirección Línea 1")
    shipping_direccion2 = forms.CharField(max_length=255, label="Dirección Línea 2", required=False)
    shipping_ciudad = forms.CharField(max_length=100, label="Ciudad")
    shipping_codigo_postal = forms.CharField(max_length=20, label="Código Postal")
    shipping_pais = forms.CharField(max_length=100, label="País")
    shipping_telefono = forms.CharField(max_length=20, label="Teléfono")

    # Checkbox para dirección de facturación
    billing_same_as_shipping = forms.BooleanField(required=False, initial=True, label="Usar la misma dirección de envío para la facturación")

    # Campos de Facturación (opcionales, dependerán del checkbox)
    billing_nombre = forms.CharField(max_length=100, label="Nombre (Facturación)", required=False)
    billing_apellido = forms.CharField(max_length=100, label="Apellido (Facturación)", required=False)
    billing_direccion1 = forms.CharField(max_length=255, label="Dirección Línea 1 (Facturación)", required=False)
    billing_direccion2 = forms.CharField(max_length=255, label="Dirección Línea 2 (Facturación)", required=False)
    billing_ciudad = forms.CharField(max_length=100, label="Ciudad (Facturación)", required=False)
    billing_codigo_postal = forms.CharField(max_length=20, label="Código Postal (Facturación)", required=False)
    billing_pais = forms.CharField(max_length=100, label="País (Facturación)", required=False)

    # Método de Pago
    metodo_pago = forms.ChoiceField(
        choices=(), # Se poblará en __init__ o se pasará desde la vista
        label="Método de Pago",
        widget=forms.RadioSelect
    )

    # Notas del pedido (opcional)
    notas_pedido = forms.CharField(widget=forms.Textarea(attrs={'rows':3}), required=False, label="Notas adicionales para tu pedido")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importar Pedido aquí para evitar importación circular si Pedido importa algo de forms.py
        from .models import Pedido
        self.fields['metodo_pago'].choices = Pedido.MetodoPago.choices


    def clean(self):
        cleaned_data = super().clean()
        billing_same_as_shipping = cleaned_data.get('billing_same_as_shipping')

        if not billing_same_as_shipping:
            required_billing_fields = [
                'billing_nombre', 'billing_apellido', 'billing_direccion1',
                'billing_ciudad', 'billing_codigo_postal', 'billing_pais'
            ]
            for field_name in required_billing_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, forms.ValidationError("Este campo es obligatorio si la dirección de facturación es diferente."))
        return cleaned_data

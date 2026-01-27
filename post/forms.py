from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import Producto, Categoria, Marca, Cupon, Cliente, Resena

User = get_user_model()

class AdminAuthenticationForm(AuthenticationForm):
    """
    Formulario de autenticación personalizado para administradores que requiere un código secreto.
    """
    admin_code = forms.CharField(
        label="Código de Administrador",
        required=True,
        widget=forms.PasswordInput,
    )

    def clean(self):
        cleaned_data = super().clean()
        admin_code = cleaned_data.get("admin_code")
        correct_code = getattr(settings, 'ADMIN_LOGIN_CODE', None)

        if not correct_code:
            raise forms.ValidationError("El sistema no está configurado para el inicio de sesión de administrador.")

        if admin_code != correct_code:
            self.add_error('admin_code', "El código de administrador no es válido.")

        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    """
    Formulario de creación de usuario personalizado que incluye campos adicionales.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name')

class ProductoForm(forms.ModelForm):
    """
    Formulario para la creación y edición de productos desde el panel de administración.
    """
    class Meta:
        model = Producto
        fields = [
            'nombre', 'slug', 'descripcion', 'caracteristicas', 'precio',
            'precio_descuento', 'categoria', 'marca', 'talla', 'genero',
            'color', 'material', 'stock', 'disponible', 'destacado', 'nuevo',
            'etiquetas'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'etiquetas': forms.CheckboxSelectMultiple,
        }

class CuponForm(forms.ModelForm):
    """
    Formulario para la creación y edición de cupones de descuento.
    """
    # Manejo explícito para campos de fecha y ManyToMany
    fecha_inicio = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    fecha_fin = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    productos = forms.ModelMultipleChoiceField(
        queryset=Producto.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Cupon
        fields = [
            'codigo', 'descripcion', 'tipo_descuento', 'descuento',
            'fecha_inicio', 'fecha_fin', 'max_usos', 'activo',
            'minimo_compra', 'categorias', 'productos', 'solo_nuevos_clientes'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

class ClienteForm(forms.ModelForm):
    """
    Formulario para que los clientes editen su perfil.
    """
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'email', 'telefono', 'direccion', 'ciudad',
            'codigo_postal', 'pais', 'fecha_nacimiento', 'acepta_marketing'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'direccion': forms.Textarea(attrs={'rows': 4}),
        }

class ResenaForm(forms.ModelForm):
    """
    Formulario para que los clientes dejen una reseña en un producto.
    """
    class Meta:
        model = Resena
        fields = ('titulo', 'comentario', 'calificacion')
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 5}),
            'calificacion': forms.RadioSelect(choices=[(i, f'{i} estrellas') for i in range(1, 6)]),
        }

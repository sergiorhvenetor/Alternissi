from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Cliente, Pedido, Producto, Categoria
import uuid

User = get_user_model()

class SignalTests(TestCase):
    def test_cliente_profile_created_on_user_creation(self):
        """
        Test that a Cliente profile is created automatically when a new User is created.
        """
        user = User.objects.create_user(
            username='newuser',
            password='password123',
            email='newuser@example.com',
            first_name='New',
            last_name='User'
        )
        self.assertTrue(hasattr(user, 'cliente'))
        self.assertEqual(user.cliente.nombre, 'New')
        self.assertEqual(user.cliente.apellido, 'User')
        self.assertEqual(user.cliente.email, 'newuser@example.com')

    def test_cliente_profile_updated_on_user_update(self):
        """
        Test that the Cliente profile is updated when the associated User is updated.
        """
        user = User.objects.create_user(
            username='updateuser',
            password='password123',
            email='updateuser@example.com',
            first_name='Original',
            last_name='Name'
        )

        user.first_name = 'Updated'
        user.last_name = 'Name'
        user.email = 'updated@example.com'
        user.save()

        # Refresh the user's cliente instance from the database
        user.cliente.refresh_from_db()

        self.assertEqual(user.cliente.nombre, 'Updated')
        self.assertEqual(user.cliente.apellido, 'Name')
        self.assertEqual(user.cliente.email, 'updated@example.com')

    def test_user_updated_on_cliente_update(self):
        """
        Test that the User model is updated when the associated Cliente profile is updated.
        """
        user = User.objects.create_user(
            username='syncuser',
            password='password123',
            email='syncuser@example.com',
            first_name='Original',
            last_name='User'
        )

        cliente = user.cliente
        cliente.nombre = 'Updated'
        cliente.apellido = 'User'
        cliente.email = 'updated_sync@example.com'
        cliente.save()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'updated_sync@example.com')

    def test_duplicate_email_signal_handling(self):
        """Test that signal handles existing Cliente without user by linking them."""
        email = "orphaned@example.com"
        cliente = Cliente.objects.create(
            nombre="Orphaned",
            apellido="Cliente",
            email=email
        )

        # This should NOT raise IntegrityError anymore
        user = User.objects.create_user(
            username="newuser_signal",
            email=email,
            password="password123",
            first_name="New",
            last_name="User"
        )

        cliente.refresh_from_db()
        self.assertEqual(cliente.usuario, user)
        self.assertEqual(cliente.nombre, "Orphaned")

    def test_duplicate_user_email_signal_safety(self):
        """Test that signal doesn't crash if email already belongs to another user."""
        email = "user1@example.com"
        User.objects.create_user(
            username="user1",
            email=email,
            password="password123"
        )

        # Second user with same email (Standard User allows this)
        user2 = User.objects.create_user(
            username="user2",
            email=email,
            password="password123"
        )

        self.assertFalse(Cliente.objects.filter(usuario=user2).exists())


class PedidoModelTests(TestCase):
    def test_generar_codigo_pedido_format(self):
        """
        Test that the `generar_codigo_pedido` method returns a code in the expected format.
        """
        pedido = Pedido()
        codigo = pedido.generar_codigo_pedido()

        self.assertRegex(codigo, r'^PED-\d{6}-[A-F0-9]{6}$')


from .forms import CustomUserCreationForm

class RegistrationFormTests(TestCase):
    def test_form_validation_duplicate_email(self):
        """Test that form prevents registration with an email already used by another user."""
        email = "taken@example.com"
        User.objects.create_user(
            username="existing",
            email=email,
            password="password123"
        )

        form_data = {
            'username': 'newuser_form',
            'email': email,
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'Pass123!',
            'password2': 'Pass123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'][0], "Ya existe un usuario con este correo electrónico.")

    def test_form_validation_existing_cliente_no_user(self):
        """Test that form ALLOWS registration if Cliente exists but has no user."""
        email = "guest@example.com"
        Cliente.objects.create(
            nombre="Guest",
            apellido="User",
            email=email
        )

        form_data = {
            'username': 'newuser_form_guest',
            'email': email,
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'Pass123!',
            'password2': 'Pass123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.categoria = Categoria.objects.create(nombre='Test Category')
        self.producto = Producto.objects.create(
            nombre='Test Product',
            descripcion='A test product',
            precio=10.00,
            categoria=self.categoria,
            stock=10,
        )

    def test_buscar_productos_view(self):
        """
        Test the search view for products.
        """
        response = self.client.get(reverse('tienda:buscar'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'post/resultados_busqueda.html')
        self.assertContains(response, 'Test Product')
        self.assertEqual(response.context['query'], 'Test')

    def test_home_page_view(self):
        """
        Test that the home page loads correctly.
        """
        response = self.client.get(reverse('tienda:inicio'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'post/inicio.html')

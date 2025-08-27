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


class PedidoModelTests(TestCase):
    def test_generar_codigo_pedido_format(self):
        """
        Test that the `generar_codigo_pedido` method returns a code in the expected format.
        """
        pedido = Pedido()
        codigo = pedido.generar_codigo_pedido()

        self.assertRegex(codigo, r'^PED-\d{6}-[A-F0-9]{6}$')


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

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Producto, Categoria, Resena, Cliente

User = get_user_model()

class ReviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reviewer',
            password='password123',
            email='reviewer@example.com',
            first_name='Review',
            last_name='User'
        )
        self.categoria = Categoria.objects.create(nombre='Test Category')
        self.producto = Producto.objects.create(
            nombre='Test Product',
            descripcion='A test product',
            precio=10.00,
            categoria=self.categoria,
            stock=10,
        )
        self.client.login(username='reviewer', password='password123')

    def test_create_review_published_immediately(self):
        """
        Test that a review can be created and it is published immediately (aprobado=True).
        """
        url = reverse('tienda:crear_resena', kwargs={'producto_id': self.producto.id})
        data = {
            'titulo': 'Great product',
            'comentario': 'I really liked this product.',
            'calificacion': 5
        }
        response = self.client.post(url, data)

        # Should redirect to product detail
        self.assertEqual(response.status_code, 302)

        # Verify review exists and is approved
        review = Resena.objects.get(producto=self.producto, cliente__usuario=self.user)
        self.assertEqual(review.titulo, 'Great product')
        self.assertTrue(review.aprobado)

        # Verify it appears on product detail page
        detail_url = reverse('tienda:detalle_producto', kwargs={'pk': self.producto.id, 'slug': self.producto.slug})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Great product')
        self.assertContains(response, 'I really liked this product.')

    def test_review_form_in_detail_page_context(self):
        """
        Test that the product detail page context contains the review form.
        """
        detail_url = reverse('tienda:detalle_producto', kwargs={'pk': self.producto.id, 'slug': self.producto.slug})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('resena_form', response.context)

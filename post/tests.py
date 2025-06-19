from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
import uuid

from .models import (
    Cliente, Producto, Categoria, Marca, Carrito, ItemCarrito,
    Pedido, Cupon, ConfiguracionTienda
)

User = get_user_model()

class RewardCouponGenerationTests(TestCase):
    def setUp(self):
        # Crear usuario y cliente
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        self.cliente = Cliente.objects.create(usuario=self.user, nombre='Test', apellido='User', email='test@example.com')

        # Crear Categoria y Marca
        self.categoria = Categoria.objects.create(nombre='Electrónicos', slug='electronicos')
        self.marca = Marca.objects.create(nombre='TechCorp', slug='techcorp')

        # Crear Productos
        self.producto_sin_recompensa = Producto.objects.create(
            nombre='Teclado Básico',
            slug='teclado-basico',
            descripcion='Un teclado estándar.',
            precio=Decimal('25.00'),
            categoria=self.categoria,
            marca=self.marca,
            stock=100,
            disponible=True,
            porcentaje_recompensa=Decimal('0.00')
        )

        self.producto_con_recompensa_10 = Producto.objects.create(
            nombre='Monitor Avanzado',
            slug='monitor-avanzado',
            descripcion='Monitor de alta resolución.',
            precio=Decimal('100.00'),
            categoria=self.categoria,
            marca=self.marca,
            stock=50,
            disponible=True,
            porcentaje_recompensa=Decimal('0.10') # 10%
        )

        self.producto_con_recompensa_05 = Producto.objects.create(
            nombre='Mouse Gamer',
            slug='mouse-gamer',
            descripcion='Mouse ergonómico para gaming.',
            precio=Decimal('50.00'),
            categoria=self.categoria,
            marca=self.marca,
            stock=75,
            disponible=True,
            porcentaje_recompensa=Decimal('0.05') # 5%
        )

        self.producto_precision_test = Producto.objects.create(
            nombre='Webcam HD',
            slug='webcam-hd',
            descripcion='Webcam para conferencias.',
            precio=Decimal('33.33'),
            categoria=self.categoria,
            marca=self.marca,
            stock=30,
            disponible=True,
            porcentaje_recompensa=Decimal('0.10') # 10% -> 3.333
        )

        # Crear ConfiguracionTienda por si algún modelo lo necesita indirectamente al guardar
        ConfiguracionTienda.objects.get_or_create(
            nombre_tienda="Tienda Test",
            defaults={'activo': True}
        )

        # Datos comunes para convertir_a_pedido
        self.direccion_envio = {
            'nombre': 'Test', 'apellido': 'User', 'email': 'test@example.com',
            'direccion1': '123 Calle Falsa', 'direccion2': '', 'ciudad': 'Springfield',
            'codigo_postal': '12345', 'pais': 'US', 'telefono': '555-1234'
        }
        self.direccion_facturacion = self.direccion_envio.copy()
        self.metodo_pago = Pedido.MetodoPago.TARJETA

    def _crear_carrito_con_items(self, items_data):
        """
        Helper para crear un carrito y añadirle items.
        items_data es una lista de tuplas: (producto, cantidad)
        """
        carrito = Carrito.objects.create(cliente=self.cliente)
        for producto, cantidad in items_data:
            ItemCarrito.objects.create(
                carrito=carrito,
                producto=producto,
                cantidad=cantidad,
                precio=producto.precio_actual # Asegurar que el precio es el actual
            )
        return carrito

    def test_no_reward_coupon_generated(self):
        """
        Test que no se genera cupón si los productos no tienen porcentaje de recompensa.
        """
        carrito = self._crear_carrito_con_items([
            (self.producto_sin_recompensa, 2)
        ])

        initial_cupon_count = Cupon.objects.count()

        pedido = carrito.convertir_a_pedido(
            cliente=self.cliente,
            direccion_envio=self.direccion_envio,
            direccion_facturacion=self.direccion_facturacion,
            metodo_pago=self.metodo_pago
        )
        self.assertIsNotNone(pedido)

        final_cupon_count = Cupon.objects.count()
        self.assertEqual(final_cupon_count, initial_cupon_count)

        # Adicionalmente, verificar que no hay cupones con el prefijo RECOMP-
        self.assertFalse(Cupon.objects.filter(codigo__startswith=f"RECOMP-{pedido.codigo[:10]}").exists())

    def test_reward_coupon_generated_single_item(self):
        """
        Test que se genera un cupón con las propiedades correctas para un solo item con recompensa.
        """
        carrito = self._crear_carrito_con_items([
            (self.producto_con_recompensa_10, 1) # Precio $100, recompensa 10%
        ])

        initial_cupon_count = Cupon.objects.count()

        pedido = carrito.convertir_a_pedido(
            cliente=self.cliente,
            direccion_envio=self.direccion_envio,
            direccion_facturacion=self.direccion_facturacion,
            metodo_pago=self.metodo_pago
        )
        self.assertIsNotNone(pedido)

        self.assertEqual(Cupon.objects.count(), initial_cupon_count + 1)

        cupon_generado = Cupon.objects.filter(codigo__startswith=f"RECOMP-{pedido.codigo[:10]}").first()
        self.assertIsNotNone(cupon_generado)

        self.assertEqual(cupon_generado.tipo_descuento, Cupon.TipoDescuento.FIJO)
        self.assertEqual(cupon_generado.descuento, Decimal('10.00')) # 100.00 * 0.10
        self.assertEqual(cupon_generado.max_usos, 1)
        self.assertTrue(cupon_generado.activo)
        self.assertIsNotNone(cupon_generado.fecha_inicio)
        self.assertIsNotNone(cupon_generado.fecha_fin)
        self.assertTrue(cupon_generado.fecha_fin > cupon_generado.fecha_inicio)
        # Verificar validez de 30 días
        expected_expiry = cupon_generado.fecha_inicio + timezone.timedelta(days=30)
        # Permitir una pequeña diferencia por la ejecución del código
        self.assertAlmostEqual(cupon_generado.fecha_fin, expected_expiry, delta=timezone.timedelta(seconds=10))


    def test_reward_coupon_generated_multiple_items(self):
        """
        Test que se genera un cupón con el valor correcto para múltiples items con diferentes recompensas.
        """
        carrito = self._crear_carrito_con_items([
            (self.producto_con_recompensa_10, 2), # $100 * 0.10 * 2 = $20.00
            (self.producto_con_recompensa_05, 1), # $50 * 0.05 * 1 = $2.50
            (self.producto_sin_recompensa, 3)     # $25 * 0.00 * 3 = $0.00
        ])

        initial_cupon_count = Cupon.objects.count()

        pedido = carrito.convertir_a_pedido(
            cliente=self.cliente,
            direccion_envio=self.direccion_envio,
            direccion_facturacion=self.direccion_facturacion,
            metodo_pago=self.metodo_pago
        )
        self.assertIsNotNone(pedido)

        self.assertEqual(Cupon.objects.count(), initial_cupon_count + 1)

        cupon_generado = Cupon.objects.filter(codigo__startswith=f"RECOMP-{pedido.codigo[:10]}").first()
        self.assertIsNotNone(cupon_generado)

        self.assertEqual(cupon_generado.descuento, Decimal('22.50')) # 20.00 + 2.50

    def test_reward_coupon_value_decimal_precision(self):
        """
        Test que el valor del descuento del cupón se redondea correctamente a 2 decimales.
        """
        carrito = self._crear_carrito_con_items([
            (self.producto_precision_test, 1) # Precio $33.33, recompensa 10% -> $3.333
        ])

        initial_cupon_count = Cupon.objects.count()

        pedido = carrito.convertir_a_pedido(
            cliente=self.cliente,
            direccion_envio=self.direccion_envio,
            direccion_facturacion=self.direccion_facturacion,
            metodo_pago=self.metodo_pago
        )
        self.assertIsNotNone(pedido)

        self.assertEqual(Cupon.objects.count(), initial_cupon_count + 1)

        cupon_generado = Cupon.objects.filter(codigo__startswith=f"RECOMP-{pedido.codigo[:10]}").first()
        self.assertIsNotNone(cupon_generado)

        # El valor 3.333 debe ser cuantizado a 3.33
        self.assertEqual(cupon_generado.descuento, Decimal('3.33'))

    def test_reward_coupon_product_with_null_recompensa(self):
        """
        Test que un producto con porcentaje_recompensa=None (si permitido y default=0 no aplica)
        se trata como 0 recompensa. En nuestro caso, default=0, null=True.
        Si el porcentaje es None, debe comportarse como 0.
        """
        producto_null_recompensa = Producto.objects.create(
            nombre='Producto Recompensa Null',
            slug='producto-recompensa-null',
            descripcion='Este producto tiene recompensa null.',
            precio=Decimal('100.00'),
            categoria=self.categoria,
            stock=10,
            porcentaje_recompensa=None # Explicitamente None
        )

        carrito = self._crear_carrito_con_items([
            (producto_null_recompensa, 1),
            (self.producto_con_recompensa_05, 1) # $50 * 0.05 * 1 = $2.50
        ])

        initial_cupon_count = Cupon.objects.count()

        pedido = carrito.convertir_a_pedido(
            cliente=self.cliente,
            direccion_envio=self.direccion_envio,
            direccion_facturacion=self.direccion_facturacion,
            metodo_pago=self.metodo_pago
        )
        self.assertIsNotNone(pedido)

        self.assertEqual(Cupon.objects.count(), initial_cupon_count + 1)

        cupon_generado = Cupon.objects.filter(codigo__startswith=f"RECOMP-{pedido.codigo[:10]}").first()
        self.assertIsNotNone(cupon_generado)
        self.assertEqual(cupon_generado.descuento, Decimal('2.50')) # Solo el producto con recompensa debe contar

    def test_no_reward_if_percentage_is_zero(self):
        """
        Test que un producto con porcentaje_recompensa=0 explícitamente no genera recompensa.
        Esto es similar a test_no_reward_coupon_generated pero enfocado en un item mixto.
        """
        carrito = self._crear_carrito_con_items([
            (self.producto_sin_recompensa, 1), # 0%
            (self.producto_con_recompensa_10, 0)  # 0 cantidad, no debería afectar
        ])

        initial_cupon_count = Cupon.objects.count()

        pedido = carrito.convertir_a_pedido(
            cliente=self.cliente,
            direccion_envio=self.direccion_envio,
            direccion_facturacion=self.direccion_facturacion,
            metodo_pago=self.metodo_pago
        )
        self.assertIsNotNone(pedido)
        self.assertEqual(Cupon.objects.count(), initial_cupon_count) # No se crea cupón

        # Verificar que no hay cupones con el prefijo RECOMP-
        self.assertFalse(Cupon.objects.filter(codigo__startswith=f"RECOMP-{pedido.codigo[:10]}").exists())

    def tearDown(self):
        # TestCase se encarga de limpiar la base de datos entre tests.
        # No es estrictamente necesario limpiar manualmente aquí, pero puede hacerse si hay
        # algún recurso externo o estado que no sea manejado por las transacciones de TestCase.
        pass

# Ejemplo de test adicional que podría ser útil:
# class AnotherModelTests(TestCase):
#     def test_something_else(self):
#         self.assertTrue(True)

# Para ejecutar estos tests: python manage.py test post.tests
# O si quieres ser más específico: python manage.py test post.tests.RewardCouponGenerationTests
# O un test específico: python manage.py test post.tests.RewardCouponGenerationTests.test_no_reward_coupon_generated

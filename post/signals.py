# post/signals.py
import uuid
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Carrito, ItemCarrito, Cliente, Pedido, Cupon, ConfiguracionTienda

@receiver(user_logged_in)
def transfer_session_cart_to_user_cart(sender, request, user, **kwargs):
    """
    Transfiere o fusiona el carrito de sesión (anónimo) al carrito del usuario
    cuando este se loguea.
    """
    session_key = request.session.session_key
    if not session_key:
        return # No hay sesión, nada que transferir

    try:
        cliente = Cliente.objects.get(usuario=user)
    except Cliente.DoesNotExist:
        # Esto no debería ocurrir si el cliente se crea en el registro
        # o en el CartMixin, pero por si acaso.
        # Podríamos crear el cliente aquí o simplemente retornar.
        # Por ahora, retornamos para evitar efectos secundarios inesperados.
        # print(f"Advertencia: Cliente no encontrado para el usuario {user.username} durante la transferencia del carrito.")
        return

    try:
        session_cart = Carrito.objects.prefetch_related('items__producto').get(session_key=session_key, cliente__isnull=True)
    except Carrito.DoesNotExist:
        return # No hay carrito de sesión para transferir

    # Obtener o crear el carrito del cliente
    # Usamos prefetch_related también aquí por consistencia si vamos a acceder a items
    user_cart, created_user_cart = Carrito.objects.prefetch_related('items__producto').get_or_create(cliente=cliente)

    if session_cart == user_cart: # Esto podría pasar si de alguna manera el carrito de sesión ya estaba asignado.
        if session_cart.session_key: # Limpiar session_key si es el mismo carrito.
            session_cart.session_key = None
            session_cart.save()
        return

    with transaction.atomic():
        # Fusionar items del carrito de sesión al carrito del usuario
        for session_item in session_cart.items.all():
            # Comprobar si el producto ya existe en el carrito del usuario
            user_item, created = user_cart.items.get_or_create(
                producto=session_item.producto,
                defaults={
                    'cantidad': session_item.cantidad,
                    'precio': session_item.producto.precio_actual # Usar precio actual del producto
                }
            )
            if not created:
                # El item ya existía en el carrito del usuario, sumar cantidades
                # Respetar el stock disponible
                nueva_cantidad = user_item.cantidad + session_item.cantidad
                if nueva_cantidad > session_item.producto.stock:
                    user_item.cantidad = session_item.producto.stock
                    # Podríamos enviar un mensaje aquí, pero las señales no tienen acceso fácil a 'messages.error'
                    # Esto se podría manejar en la vista del carrito si la cantidad excede el stock.
                else:
                    user_item.cantidad = nueva_cantidad
                user_item.precio = session_item.producto.precio_actual # Asegurar precio actualizado
                user_item.save()
            # Si fue 'created', ya tiene la cantidad y precio del session_item via defaults.

        # Una vez migrados los items, eliminar el carrito de sesión
        session_cart_id = session_cart.id
        session_cart.delete()

        # Actualizar el carrito del usuario (ej. timestamp)
        user_cart.save()

    # Opcional: limpiar la session_key del request si ya no es necesaria para el carrito.
    # if request.session.get('cart_id') == session_cart_id:
    # del request.session['cart_id'] # Esto si almacenáramos cart_id en sesión, lo que no parece ser el caso.

    # El context processor debería ahora recoger el user_cart correctamente.
    # print(f"Carrito de sesión {session_cart_id} fusionado con carrito de usuario {user_cart.id} para {user.username}")


@receiver(post_save, sender=Pedido)
def generar_cupon_recompensa(sender, instance, created, **kwargs):
    """
    Genera un cupón de recompensa cuando un pedido se marca como 'completado'.
    """
    # Solo actuar si el pedido está completado y si es una actualización (no creación inicial en estado completado)
    # o si se crea directamente como completado (menos común).
    # El 'update_fields' puede ayudar a saber qué cambió, pero aquí verificamos el estado.
    if instance.estado == Pedido.Estado.COMPLETADO:
        # Verificar si ya existe un cupón de recompensa para este pedido
        # Usamos el prefijo del código del pedido para identificarlo.
        reward_coupon_prefix = f"RECOMP-{instance.codigo[:15]}" # Ajustar longitud si es necesario
        if not Cupon.objects.filter(codigo__startswith=reward_coupon_prefix).exists():

            # Lógica para calcular el valor de la recompensa
            # Ejemplo: 5% del subtotal del pedido, con un mínimo de 1 y máximo de 20 unidades de moneda.
            # O un valor fijo si ConfiguracionTienda lo define.
            config = ConfiguracionTienda.obtener_configuracion()
            valor_recompensa = Decimal('5.00') # Valor por defecto

            if config and hasattr(config, 'porcentaje_recompensa_pedido') and config.porcentaje_recompensa_pedido > 0:
                calculated_value = (instance.subtotal * config.porcentaje_recompensa_pedido) / 100
                # Aplicar límites si están definidos en config
                min_recompensa = getattr(config, 'min_valor_recompensa_pedido', Decimal('1.00'))
                max_recompensa = getattr(config, 'max_valor_recompensa_pedido', Decimal('20.00'))
                valor_recompensa = max(min_recompensa, min(calculated_value, max_recompensa))
            elif config and hasattr(config, 'valor_fijo_recompensa_pedido') and config.valor_fijo_recompensa_pedido > 0:
                valor_recompensa = config.valor_fijo_recompensa_pedido

            valor_recompensa = valor_recompensa.quantize(Decimal('0.01')) # Redondear a 2 decimales

            if valor_recompensa <= 0: # No generar cupón si el valor es cero o negativo
                return

            # Generar código único para el cupón
            codigo_cupon = f"{reward_coupon_prefix}-{uuid.uuid4().hex[:6].upper()}"

            # Fechas de validez (ej. 30 días desde hoy)
            fecha_inicio = timezone.now()
            fecha_fin = fecha_inicio + timedelta(days=30)

            Cupon.objects.create(
                codigo=codigo_cupon,
                descripcion=f"Cupón de recompensa por tu pedido #{instance.codigo}. ¡Gracias por tu compra!",
                tipo_descuento=Cupon.TipoDescuento.FIJO,
                descuento=valor_recompensa,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                max_usos=1,
                usos_actuales=0,
                activo=True,
                minimo_compra=Decimal('0.00'), # O un mínimo razonable, ej. valor_recompensa * 2
                # Podríamos asociarlo al cliente del pedido para que solo él pueda usarlo
                # Para ello, necesitaríamos un campo 'cliente_exclusivo' en el modelo Cupon.
                # Por ahora, es un cupón genérico de un solo uso.
            )
            # print(f"Cupón de recompensa {codigo_cupon} generado para el pedido {instance.codigo}")

# Considerar añadir campos a ConfiguracionTienda para:
# - porcentaje_recompensa_pedido (Decimal)
# - min_valor_recompensa_pedido (Decimal)
# - max_valor_recompensa_pedido (Decimal)
# - valor_fijo_recompensa_pedido (Decimal)
# - dias_validez_cupon_recompensa (Integer)
# Si estos campos no existen, la lógica de recompensa usará valores fijos o no se activará.
# Por ahora, la señal usa un valor fijo de 5.00 si no hay configuración.
# Es necesario añadir esos campos al modelo ConfiguracionTienda si se quiere esa flexibilidad.

@receiver(post_save, sender=Cliente)
def update_user_from_cliente(sender, instance, created, **kwargs):
    """
    Actualiza los datos del usuario asociado cuando el perfil del cliente se actualiza.
    """
    if instance.usuario:
        user = instance.usuario
        # Comprobar si los datos han cambiado para evitar bucles infinitos de señales.
        if (user.email != instance.email or
            user.first_name != instance.nombre or
            user.last_name != instance.apellido):

            user.email = instance.email
            user.first_name = instance.nombre
            user.last_name = instance.apellido
            user.save()

from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_cliente_profile(sender, instance, created, **kwargs):
    """
    Crea o actualiza el perfil del cliente cada vez que un usuario se guarda.
    """
    if created:
        # Si se crea un nuevo usuario, también creamos un perfil de Cliente asociado.
        # Esto es especialmente útil para usuarios creados desde el admin.
        Cliente.objects.get_or_create(
            usuario=instance,
            defaults={
                'email': instance.email,
                'nombre': instance.first_name,
                'apellido': instance.last_name,
            }
        )
    else:
        # Si un usuario existente se actualiza, actualizamos el perfil del Cliente.
        try:
            cliente = instance.cliente
            # Comprobar si los datos han cambiado para evitar escrituras innecesarias.
            if (cliente.email != instance.email or
                cliente.nombre != instance.first_name or
                cliente.apellido != instance.last_name):

                cliente.email = instance.email
                cliente.nombre = instance.first_name
                cliente.apellido = instance.last_name
                cliente.save()
        except Cliente.DoesNotExist:
            # Si por alguna razón el perfil no existe, lo creamos.
            Cliente.objects.create(
                usuario=instance,
                email=instance.email,
                nombre=instance.first_name,
                apellido=instance.last_name,
            )

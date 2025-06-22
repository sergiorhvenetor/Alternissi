# post/context_processors.py
from .models import Carrito, Cliente

def cart_processor(request):
    current_cart = None
    # Optimización: prefetch items y su producto, y el cupón del carrito.
    # Esto será útil en cualquier página que muestre resumen del carrito (ej. header).
    cart_qs = Carrito.objects.prefetch_related('items__producto', 'cupon')

    if request.user.is_authenticated:
        try:
            # Intenta obtener el cliente. No lo crea si no existe.
            # El CartMixin y otras vistas (como CuentaDashboardView) se encargan de crear el Cliente si es necesario.
            cliente = Cliente.objects.get(usuario=request.user)
            # Intenta obtener el carrito del cliente. Si no existe, lo crea.
            current_cart, created = cart_qs.get_or_create(cliente=cliente)

            # Si se acaba de crear un carrito para un cliente autenticado,
            # y existía un carrito de sesión previo, podríamos migrarlo.
            # Esta lógica es más compleja y se deja para el CartMixin o una señal.
            # Por ahora, el procesador de contexto no migra carritos.

        except Cliente.DoesNotExist:
            # Si el cliente no existe (ej. usuario recién creado que no ha visitado una vista que cree Cliente),
            # aún podría tener un carrito de sesión si navegó anónimamente antes.
            session_key = request.session.session_key
            if session_key:
                try:
                    current_cart = cart_qs.get(session_key=session_key, cliente__isnull=True)
                except Carrito.DoesNotExist:
                    pass # No hay carrito de sesión para este usuario no-cliente.
    else:
        # Usuario no autenticado, solo buscar carrito de sesión.
        session_key = request.session.session_key
        if session_key:
            try:
                current_cart = cart_qs.get(session_key=session_key, cliente__isnull=True)
            except Carrito.DoesNotExist:
                # No hay sesión o no hay carrito para esta sesión.
                # No creamos un carrito aquí; CartMixin se encargará si es necesario en una vista.
                pass

    return {'cart': current_cart, 'global_cart_items': current_cart.total_items if current_cart else 0}

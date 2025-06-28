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

    cart_total_val = 0
    cart_descuento_val = 0
    global_cart_subtotal = 0

    if current_cart:
        # El cliente para el cálculo del total se infiere de current_cart.cliente (si existe)
        # o es None para carritos de sesión. get_total() y descuento_aplicado() manejan esto.
        cliente_para_calculo = current_cart.cliente # Puede ser None

        global_cart_subtotal = current_cart.subtotal
        cart_total_val = current_cart.get_total(cliente_actual=cliente_para_calculo)
        cart_descuento_val = current_cart.descuento_aplicado # Ahora usa self.cliente implícitamente


    return {
        'cart': current_cart,
        'global_cart_items': current_cart.total_items if current_cart else 0,
        'global_cart_subtotal': global_cart_subtotal, # Para mostrar antes de descuentos
        'global_cart_total': cart_total_val, # Para mostrar el total final
        'global_cart_descuento': cart_descuento_val # Para mostrar el monto del descuento
    }

from .models import ConfiguracionTienda

def tienda_config_processor(request):
    """
    Añade la configuración activa de la tienda al contexto de la plantilla.
    """
    config = ConfiguracionTienda.obtener_configuracion()
    # Define un símbolo de moneda por defecto si la configuración no existe o no tiene uno.
    moneda_simbolo_global = '$'
    if config and hasattr(config, 'simbolo_moneda') and config.simbolo_moneda:
        moneda_simbolo_global = config.simbolo_moneda

    return {
        'tienda_config': config,
        'moneda_simbolo_global': moneda_simbolo_global
    }

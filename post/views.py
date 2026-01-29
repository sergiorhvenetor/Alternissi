from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    View, TemplateView, ListView, DetailView, CreateView, UpdateView,
)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseBadRequest
from .forms import (
    CustomUserCreationForm, ProductoForm, CuponForm, CheckoutForm,
    AdminAuthenticationForm, UnifiedAuthenticationForm
)
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import F, Q, Sum, Value, Avg, Count, Exists, OuterRef
from django.db.models.functions import Coalesce
from django.db import transaction
from .forms import ClienteForm, ResenaForm
from django.contrib.auth.forms import AuthenticationForm

# Importa todos los modelos necesarios
from .models import (
    Producto, Categoria, Marca, Carrito, ItemCarrito,
    Pedido, Cliente, ListaDeseos, Resena, Cupon, ConfiguracionTienda
)

# --- Mixins Personalizados ---

class CartMixin:
    """
    Un Mixin que proporciona una función para obtener el carrito del usuario.
    Esto evita repetir la misma lógica en múltiples vistas.
    """
    def get_cart(self):
        cart_queryset = Carrito.objects.prefetch_related(
            'items__producto__imagenes', # Para mostrar imagen del producto en el carrito
            'cupon' # Para mostrar detalles del cupón si está aplicado
        )
        if self.request.user.is_authenticated:
            cliente, _ = Cliente.objects.get_or_create(
                usuario=self.request.user, 
                defaults={
                    'email': self.request.user.email,
                    'nombre': self.request.user.first_name or self.request.user.username,
                    'apellido': self.request.user.last_name or ''
                }
            )
            # Utiliza el queryset optimizado para get_or_create
            cart, created = cart_queryset.get_or_create(cliente=cliente)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            # Utiliza el queryset optimizado para get_or_create
            cart, created = cart_queryset.get_or_create(session_key=session_key)
        return cart

# --- Vistas Principales de la Tienda ---

class InicioTiendaView(TemplateView):
    """Página de inicio de la tienda."""
    template_name = 'post/inicio.html' # Corrected path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Base queryset con anotaciones de rating para evitar N+1
        base_productos = Producto.objects.filter(disponible=True).annotate(
            annotated_avg_rating=Avg('resenas__calificacion', filter=Q(resenas__aprobado=True)),
            annotated_count_reviews=Count('resenas', filter=Q(resenas__aprobado=True))
        )

        productos_destacados_query = base_productos.filter(precio_descuento__isnull=False, precio_descuento__lt=F('precio')).annotate(
            total_vendido=Coalesce(Sum('ventas__cantidad'), Value(0))
        ).order_by('-total_vendido', '-destacado', '-creado')

        context['productos_destacados'] = productos_destacados_query.prefetch_related('imagenes')[:8]
        context['productos_nuevos'] = base_productos.filter(nuevo=True).prefetch_related('imagenes')[:8]

        # Productos con descuento
        context['productos_con_descuento'] = base_productos.filter(
            precio_descuento__isnull=False,
            precio_descuento__lt=F('precio')
        ).prefetch_related('imagenes').order_by('-creado')[:8]

        context['categorias'] = Categoria.objects.filter(activo=True)
        # 'moneda_simbolo_global' y 'tienda_config' ya están en el contexto global
        return context

class ListaProductosView(ListView):
    """Muestra una lista paginada de productos, con filtros opcionales."""
    model = Producto
    template_name = 'post/lista_productos.html' # Corrected path
    context_object_name = 'productos'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().filter(disponible=True).select_related('categoria', 'marca').prefetch_related('imagenes').annotate(
            annotated_avg_rating=Avg('resenas__calificacion', filter=Q(resenas__aprobado=True)),
            annotated_count_reviews=Count('resenas', filter=Q(resenas__aprobado=True))
        )

        categoria_slug = self.kwargs.get('categoria_slug')
        marca_slug = self.kwargs.get('marca_slug')

        if categoria_slug:
            queryset = queryset.filter(categoria__slug=categoria_slug)
        if marca_slug:
            queryset = queryset.filter(marca__slug=marca_slug)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(activo=True)
        context['marcas'] = Marca.objects.filter(activo=True)
        # Añade la categoría o marca actual al contexto para mostrarla
        if self.kwargs.get('categoria_slug'):
            context['categoria_actual'] = get_object_or_404(Categoria, slug=self.kwargs['categoria_slug'])
        if self.kwargs.get('marca_slug'):
            context['marca_actual'] = get_object_or_404(Marca, slug=self.kwargs['marca_slug'])
        return context

class DetalleProductoView(DetailView):
    """Muestra la página de detalle de un único producto."""
    model = Producto
    template_name = 'post/detalle_producto.html' # Corrected path
    context_object_name = 'producto'

    def get_queryset(self):
        return super().get_queryset().filter(disponible=True).select_related('categoria', 'marca').prefetch_related('imagenes').annotate(
            annotated_avg_rating=Avg('resenas__calificacion', filter=Q(resenas__aprobado=True)),
            annotated_count_reviews=Count('resenas', filter=Q(resenas__aprobado=True))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto = self.get_object()

        # Anotar reseñas con compra_verificada para evitar N+1
        from .models import Pedido
        resenas = producto.resenas.filter(aprobado=True).select_related('cliente').annotate(
            compra_verificada=Exists(
                Pedido.objects.filter(
                    cliente=OuterRef('cliente'),
                    detalles__producto=OuterRef('producto'),
                    estado=Pedido.Estado.COMPLETADO
                )
            )
        )
        context['resenas'] = resenas
        context['resena_form'] = ResenaForm()

        # Productos relacionados con anotaciones de rating
        context['productos_relacionados'] = Producto.objects.filter(
            categoria=producto.categoria,
            disponible=True
        ).exclude(id=producto.id).prefetch_related('imagenes').annotate(
            annotated_avg_rating=Avg('resenas__calificacion', filter=Q(resenas__aprobado=True)),
            annotated_count_reviews=Count('resenas', filter=Q(resenas__aprobado=True))
        )[:4]
        return context

class BuscarProductosView(ListView):
    """Vista para el motor de búsqueda de productos."""
    model = Producto
    template_name = 'post/resultados_busqueda.html'    # Corregido
    context_object_name = 'productos'
    # paginate_by = 12 # Considerar añadir paginación para búsquedas con muchos resultados

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Producto.objects.filter(
                Q(nombre__icontains=query) | Q(descripcion__icontains=query) | Q(sku__icontains=query)
            ).filter(disponible=True).select_related('categoria', 'marca').prefetch_related('imagenes').annotate(
                annotated_avg_rating=Avg('resenas__calificacion', filter=Q(resenas__aprobado=True)),
                annotated_count_reviews=Count('resenas', filter=Q(resenas__aprobado=True))
            )
        return Producto.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        # 'moneda_simbolo_global' y 'tienda_config' ya están en el contexto global
        return context

# --- Vistas del Carrito de Compras ---

class VerCarritoView(CartMixin, TemplateView):
    """Muestra el contenido del carrito de compras."""
    template_name = 'post/carrito.html' # Corregido

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_cart()
        context['carrito'] = cart
        return context

class AgregarAlCarritoView(CartMixin, View):
    """Añade un producto al carrito o incrementa su cantidad."""
    def post(self, request, *args, **kwargs):
        producto = get_object_or_404(Producto, id=self.kwargs.get('producto_id'), disponible=True)
        cart = self.get_cart()
        cantidad = int(request.POST.get('cantidad', 1))

        if producto.stock < cantidad:
            messages.error(request, f"No hay suficiente stock para '{producto.nombre}'.")
            return redirect('tienda:detalle_producto', pk=producto.id, slug=producto.slug)

        item, created = ItemCarrito.objects.get_or_create(
            carrito=cart, producto=producto,
            defaults={'precio': producto.precio_actual, 'cantidad': cantidad}
        )

        if not created:
            item.cantidad += cantidad
            if producto.stock < item.cantidad:
                item.cantidad = producto.stock
                messages.warning(request, f"Stock máximo alcanzado para '{producto.nombre}'.")
            item.save()
            messages.success(request, f"Cantidad de '{producto.nombre}' actualizada.")
        else:
            messages.success(request, f"'{producto.nombre}' añadido al carrito.")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            cart.refresh_from_db() # Asegurar que el carrito esté actualizado
            return JsonResponse({
                'success': True,
                'message': f"'{producto.nombre}' añadido al carrito.",
                'cart_total_items_display': cart.total_items
            })
        else:
            return redirect('tienda:ver_carrito')

class ActualizarItemCarritoView(CartMixin, View): # Added CartMixin
    """Actualiza la cantidad de un item en el carrito (AJAX)."""
    def post(self, request, *args, **kwargs):
        try:
            item_id = self.kwargs.get('item_id')
            # Obtener el carrito actual usando el mixin
            cart = self.get_cart()

            # Verificar que el item pertenezca al carrito del usuario
            item = get_object_or_404(ItemCarrito, id=item_id, carrito=cart)

            cantidad = int(request.POST.get('cantidad', 1))

            if 0 < cantidad <= item.producto.stock:
                item.cantidad = cantidad
                item.save()
                cart.refresh_from_db() # Refrescar cache de prefetch_related
                # El cliente para get_total y descuento_aplicado se toma de cart.cliente si existe
                cart_total_calculado = cart.get_total()
                descuento_aplicado_calculado = cart.descuento_aplicado
                response_data = {
                    'success': True,
                    'removed': False,
                    'item_subtotal': item.subtotal,
                    'cart_subtotal_display': cart.subtotal,
                    'cart_total_display': cart_total_calculado,
                    'cart_total_items_display': cart.total_items,
                    'cart_discount_amount_display': descuento_aplicado_calculado,
                    'cart_cupon_codigo': cart.cupon.codigo if cart.cupon else None,
                    'message': 'Cantidad actualizada.'
                }
                return JsonResponse(response_data)
            elif cantidad == 0: # Permitir eliminar poniendo cantidad a 0
                 nombre_producto = item.producto.nombre
                 item.delete()
                 cart.refresh_from_db() # Refrescar cache de prefetch_related
                 cart_total_calculado = cart.get_total()
                 descuento_aplicado_calculado = cart.descuento_aplicado
                 response_data = {
                    'success': True,
                    'removed': True,
                    'cart_subtotal_display': cart.subtotal,
                    'cart_total_display': cart_total_calculado,
                    'cart_total_items_display': cart.total_items,
                    'cart_discount_amount_display': descuento_aplicado_calculado,
                    'cart_cupon_codigo': cart.cupon.codigo if cart.cupon else None,
                    'message': f"'{nombre_producto}' eliminado del carrito."
                 }
                 return JsonResponse(response_data)
            else:
                return JsonResponse({'success': False, 'message': 'Cantidad no válida o stock insuficiente.'}, status=400)
        except ItemCarrito.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Item no encontrado en tu carrito.'}, status=404)
        except Exception as e:
            # Log el error real en el servidor
            print(f"Error en ActualizarItemCarritoView: {e}")
            return JsonResponse({'success': False, 'message': 'Error interno del servidor.'}, status=500)

class EliminarItemCarritoView(CartMixin, View): # Asegurar que hereda de CartMixin
    """Elimina un item del carrito."""
    def post(self, request, *args, **kwargs): # Cambiado a POST
        try:
            item_id = self.kwargs.get('item_id')
            cart = self.get_cart()

            item = get_object_or_404(ItemCarrito, id=item_id, carrito=cart)

            nombre_producto = item.producto.nombre
            item.delete()
            # cart.save() # Para actualizar 'actualizado' y si 'total' depende de una property que no se recalcula auto.
            messages.info(request, f"'{nombre_producto}' eliminado del carrito.")
        except ItemCarrito.DoesNotExist:
            messages.error(request, "Item no encontrado o no pertenece a tu carrito.")
        except Exception as e:
            print(f"Error en EliminarItemCarritoView: {e}")
            messages.error(request, "Ocurrió un error al eliminar el item.")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Ocurrió un error al eliminar el item.'}, status=500)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Es crucial que el carrito se actualice DESPUÉS de la eliminación del item.
            # get_cart() llamado aquí de nuevo o refresh_from_db() en el 'cart' existente
            # debería darnos el estado actualizado. Las propiedades del modelo Carrito
            # (subtotal, total, total_items) deben calcularse dinámicamente.
            cart.refresh_from_db() # Opcionalmente, se podría llamar a cart.save() si actualiza timestamps o campos cacheados.
                                   # Sin embargo, las propiedades suelen ser @property y se calculan al acceder.

            # El cliente para get_total y descuento_aplicado se toma de cart.cliente si existe
            cart_total_calculado = cart.get_total()
            descuento_aplicado_calculado = cart.descuento_aplicado
            response_data = {
                'success': True,
                'removed': True, # Indicar que el item fue eliminado.
                'message': f"'{nombre_producto}' eliminado del carrito.",
                'cart_total_items_display': cart.total_items,
                'cart_subtotal_display': cart.subtotal,
                'cart_total_display': cart_total_calculado,
                'cart_discount_amount_display': descuento_aplicado_calculado,
                'cart_cupon_codigo': cart.cupon.codigo if cart.cupon else None,
            }
            return JsonResponse(response_data)
        else:
            return redirect('tienda:ver_carrito') # Redirigir siempre al carrito

class AplicarCuponView(CartMixin, View):
    """Aplica un código de cupón al carrito."""
    def post(self, request, *args, **kwargs):
        cart = self.get_cart()
        codigo = request.POST.get('codigo', '').strip()
        try:
            cupon = Cupon.objects.get(codigo__iexact=codigo)
            if cupon.es_valido(cliente=cart.cliente, subtotal=cart.subtotal):
                cart.cupon = cupon
                cart.save()
                messages.success(request, f"Cupón '{cupon.codigo}' aplicado.")
            else:
                messages.error(request, "El cupón no es válido o no cumple los requisitos.")
        except Cupon.DoesNotExist:
            messages.error(request, "El código del cupón no existe.")
        return redirect('tienda:ver_carrito')

class EliminarCuponCarritoView(CartMixin, View):
    """Elimina el cupón aplicado al carrito."""
    def post(self, request, *args, **kwargs):
        cart = self.get_cart()
        if cart.cupon:
            cart.cupon = None
            cart.save()
            messages.info(request, "Cupón eliminado del carrito.")
        return redirect('tienda:ver_carrito')

# --- Vistas del Proceso de Pago (Checkout) ---

class CheckoutView(LoginRequiredMixin, CartMixin, TemplateView):
    """Muestra la página de checkout."""
    template_name = 'post/checkout.html' # Corregido

    def dispatch(self, request, *args, **kwargs):
        cart = self.get_cart()
        if not cart.items.all().exists(): # Comprobar si hay items
            messages.warning(request, "Tu carrito está vacío.")
            return redirect('tienda:lista_productos') # Usar el namespace correcto
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_cart()
        context['carrito'] = cart

        # Pre-poblar el formulario con datos del cliente si existen
        initial_data = {}
        try:
            cliente = Cliente.objects.get(usuario=self.request.user)
            initial_data = {
                'nombre': cliente.nombre,
                'apellido': cliente.apellido,
                'email': cliente.email,
                'telefono': cliente.telefono,
                'direccion': cliente.direccion,
                'ciudad': cliente.ciudad,
                'codigo_postal': cliente.codigo_postal,
                'pais': cliente.pais,
            }
        except Cliente.DoesNotExist:
            initial_data = {
                'email': self.request.user.email,
                'nombre': self.request.user.first_name,
                'apellido': self.request.user.last_name,
            }

        context['form'] = CheckoutForm(initial=initial_data)
        context['pedido_metodos_pago_choices'] = Pedido.MetodoPago.choices
        return context

class ProcesarPedidoView(LoginRequiredMixin, CartMixin, View):
    """Procesa el carrito y lo convierte en un pedido."""
    @transaction.atomic # Asegurar que todas las operaciones sean atómicas
    def post(self, request, *args, **kwargs):
        cart = self.get_cart()
        if not cart.items.all().exists():
            messages.error(request, "Tu carrito está vacío. No puedes procesar un pedido.")
            return redirect('tienda:ver_carrito')

        form = CheckoutForm(request.POST)
        if not form.is_valid():
            # Volver al checkout mostrando errores
            messages.error(request, "Por favor corrige los errores en el formulario.")
            return render(request, 'post/checkout.html', {
                'form': form,
                'carrito': cart,
                'pedido_metodos_pago_choices': Pedido.MetodoPago.choices
            })

        data = form.cleaned_data

        # Usar get_or_create para el cliente
        cliente, created = Cliente.objects.get_or_create(
            usuario=request.user,
            defaults={
                'email': data['email'],
                'nombre': data['nombre'],
                'apellido': data['apellido'],
                'telefono': data['telefono'],
                'direccion': data['direccion'],
                'ciudad': data['ciudad'],
                'codigo_postal': data['codigo_postal'],
                'pais': data['pais'],
            }
        )

        # Actualizar datos del cliente si se solicitó guardar
        if data.get('guardar_informacion'):
            cliente.nombre = data['nombre']
            cliente.apellido = data['apellido']
            cliente.email = data['email']
            cliente.telefono = data['telefono']
            cliente.direccion = data['direccion']
            cliente.ciudad = data['ciudad']
            cliente.codigo_postal = data['codigo_postal']
            cliente.pais = data['pais']
            cliente.save()

        # Recolectar datos de dirección de envío
        direccion_envio_data = {
            'nombre': data['nombre'],
            'apellido': data['apellido'],
            'email': data['email'],
            'direccion': data['direccion'],
            'ciudad': data['ciudad'],
            'codigo_postal': data['codigo_postal'],
            'pais': data['pais'],
            'telefono': data['telefono'],
        }

        # Recolectar datos de dirección de facturación
        billing_same_as_shipping = request.POST.get('billing_same_as_shipping') == 'on'
        if billing_same_as_shipping:
            direccion_facturacion_data = direccion_envio_data.copy()
        else:
            # Aquí se podrían añadir campos específicos de facturación al form si fuera necesario
            # Por ahora usamos los mismos
            direccion_facturacion_data = direccion_envio_data.copy()

        metodo_pago = data['metodo_pago']
        
        try:
            pedido = cart.convertir_a_pedido(
                cliente=cliente,
                direccion_envio=direccion_envio_data,
                direccion_facturacion=direccion_facturacion_data,
                metodo_pago=metodo_pago
            )

            if pedido.estado == Pedido.Estado.PENDIENTE:
                 pedido.estado = Pedido.Estado.PROCESANDO
                 pedido.save()

            messages.success(request, f"¡Gracias! Tu pedido #{pedido.codigo} ha sido creado y está siendo procesado.")
            return redirect('tienda:pedido_completado', pedido_id=pedido.id)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('tienda:ver_carrito')
        except Exception as e:
            print(f"Error al procesar pedido: {e}")
            messages.error(request, "Ocurrió un error inesperado al procesar tu pedido. Por favor, inténtalo de nuevo o contacta a soporte.")
            return redirect('tienda:checkout')

class PedidoCompletadoView(LoginRequiredMixin, DetailView):
    """Muestra la página de confirmación de pedido."""
    model = Pedido
    template_name = 'post/pedido_completado.html'   # Corregido
    context_object_name = 'pedido'
    pk_url_kwarg = 'pedido_id'

    def get_queryset(self):
        # Original: return super().get_queryset().filter(cliente__usuario=self.request.user)
        return super().get_queryset().filter(
            cliente__usuario=self.request.user
        ).select_related(
            'cliente', 'cupon'
        ).prefetch_related(
            'detalles__producto__imagenes' # Para las imágenes de los productos en el resumen
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = self.get_object()

        if pedido and pedido.codigo:
            cupon_recompensa_prefijo = f"RECOMP-{pedido.codigo[:15]}"
            cupon_recompensa = Cupon.objects.filter(
                codigo__startswith=cupon_recompensa_prefijo,
                tipo_descuento=Cupon.TipoDescuento.FIJO,
                max_usos=1
            ).order_by('-creado').first()

            if cupon_recompensa:
                context['cupon_recompensa_generado'] = cupon_recompensa
        return context

class PagoCanceladoView(TemplateView):
    """Página si el pago es cancelado."""
    template_name = 'post/pago_cancelado.html' # Corrected path

# --- Vistas de la Cuenta del Cliente ---

class CuentaDashboardView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = 'post/cuenta/dashboard.html'    # Corregido
    context_object_name = 'cliente'

    def get_object(self):
        # get_or_create para el cliente si no existe, aunque la lógica de CartMixin ya puede haberlo creado.
        # Es más seguro asegurar que el cliente exista aquí si esta vista puede ser el primer punto de contacto para crear un Cliente.
        cliente, created = Cliente.objects.get_or_create(
            usuario=self.request.user,
            defaults={
                'email': self.request.user.email,
                'nombre': self.request.user.first_name or self.request.user.username,
                'apellido': self.request.user.last_name or '',
            }
        )
        return cliente

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ultimos_pedidos'] = self.object.pedidos.select_related('cupon').order_by('-creado')[:5]
        return context

class ListaPedidosClienteView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = 'post/cuenta/lista_pedidos.html'    # Corregido
    context_object_name = 'pedidos'
    paginate_by = 10 # Añadir paginación

    def get_queryset(self):
        return Pedido.objects.filter(
            cliente__usuario=self.request.user
        ).select_related('cupon').order_by('-creado') # Optimizar y ordenar

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class DetallePedidoClienteView(LoginRequiredMixin, DetailView):
    model = Pedido
    template_name = 'post/cuenta/detalle_pedido.html'    # Corregido
    context_object_name = 'pedido'
    pk_url_kwarg = 'pedido_id' # Ya estaba definido

    def get_queryset(self):
        return super().get_queryset().filter(
            cliente__usuario=self.request.user
        ).select_related(
            'cliente', 'cupon' # Cliente ya está implícito por el filtro, pero no daña.
        ).prefetch_related(
            'detalles__producto__imagenes'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class EditarPerfilClienteView(LoginRequiredMixin, UpdateView):
    model = Cliente
    template_name = 'post/cuenta/editar_perfil.html'    # Corregido
    success_url = reverse_lazy('tienda:cuenta_dashboard') # Ya estaba
    form_class = ClienteForm # Usar ClienteForm

    def get_object(self):
        # Asegurar que el cliente exista o se cree, similar a CuentaDashboardView
        cliente, created = Cliente.objects.get_or_create(
            usuario=self.request.user,
            defaults={
                'email': self.request.user.email, # Email del modelo Cliente
                'nombre': self.request.user.first_name or '',
                'apellido': self.request.user.last_name or '',
            }
        )
        return cliente
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        messages.success(self.request, "Tu perfil ha sido actualizado.")
        return super().form_valid(form)

class AgregarAListaDeseosView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs): # Puede ser GET o POST
        producto_id = self.kwargs.get('producto_id')
        producto = get_object_or_404(Producto, id=producto_id)

        cliente, _ = Cliente.objects.get_or_create(
            usuario=request.user,
            defaults={'email': request.user.email, 'nombre': request.user.first_name or request.user.username}
        )
        lista_deseos, _ = ListaDeseos.objects.get_or_create(cliente=cliente)

        if producto not in lista_deseos.productos.all():
            lista_deseos.agregar_producto(producto) # Usa el método del modelo
            messages.success(request, f"'{producto.nombre}' ha sido añadido a tu lista de deseos.")
        else:
            messages.info(request, f"'{producto.nombre}' ya está en tu lista de deseos.")

        referer_url = request.META.get('HTTP_REFERER')
        if referer_url:
            return redirect(referer_url)
        return redirect('tienda:detalle_producto', pk=producto.id, slug=producto.slug)

class EliminarDeListaDeseosView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs): # Usar POST para eliminar
        producto_id = self.kwargs.get('producto_id')
        producto = get_object_or_404(Producto, id=producto_id)

        try:
            cliente = Cliente.objects.get(usuario=request.user) # Asume que el cliente ya existe si tiene lista de deseos
            lista_deseos = get_object_or_404(ListaDeseos, cliente=cliente)

            if producto in lista_deseos.productos.all():
                lista_deseos.remover_producto(producto) # Usa el método del modelo
                messages.success(request, f"'{producto.nombre}' ha sido eliminado de tu lista de deseos.")
            else:
                messages.info(request, f"'{producto.nombre}' no estaba en tu lista de deseos.")
        except Cliente.DoesNotExist:
            messages.error(request, "No se encontró tu perfil de cliente.")
        except ListaDeseos.DoesNotExist:
             messages.info(request, "Tu lista de deseos está vacía.")

        return redirect('tienda:ver_lista_deseos')

class MoverDeseoACarritoView(LoginRequiredMixin, CartMixin, View):
    def post(self, request, *args, **kwargs):
        producto_id = self.kwargs.get('producto_id')
        producto = get_object_or_404(Producto, id=producto_id)

        try:
            cliente, _ = Cliente.objects.get_or_create(
                usuario=request.user,
                defaults={'email': request.user.email, 'nombre': request.user.first_name or request.user.username}
            )
            lista_deseos, _ = ListaDeseos.objects.get_or_create(cliente=cliente)
            carrito = self.get_cart()

            if producto in lista_deseos.productos.all():
                lista_deseos.mover_a_carrito(producto, carrito)
                messages.success(request, f"'{producto.nombre}' ha sido movido de tu lista de deseos al carrito.")
            else:
                messages.warning(request, f"'{producto.nombre}' no se encontró en tu lista de deseos. Quizás ya fue movido o eliminado.")

        except Producto.DoesNotExist:
            messages.error(request, "El producto que intentas mover ya no existe.")
            return redirect('tienda:ver_lista_deseos')
        except Exception as e:
            messages.error(request, f"Ocurrió un error al mover el producto: {str(e)}")
            print(f"Error en MoverDeseoACarritoView: {e}")
            return redirect('tienda:ver_lista_deseos')

        return redirect('tienda:ver_carrito')

# --- Vistas de Lista de Deseos y Reseñas ---

class VerListaDeseosView(LoginRequiredMixin, DetailView):
    model = ListaDeseos
    template_name = 'post/lista_deseos.html'    # Corregido
    context_object_name = 'lista_deseos'
    
    def get_object(self):
        # El cliente se obtiene o crea en el dashboard o al editar perfil.
        # Aquí asumimos que ya existe si el usuario está logueado y accede a su lista de deseos.
        # Si no, get_or_create es seguro.
        cliente, _ = Cliente.objects.get_or_create(
            usuario=self.request.user,
            defaults={
                'email': self.request.user.email,
                'nombre': self.request.user.first_name or self.request.user.username,
                'apellido': self.request.user.last_name or ''
            }
        )
        lista, created = ListaDeseos.objects.get_or_create(cliente=cliente)
        return lista

    def get_queryset(self):
        from django.db.models import Prefetch
        # Optimizar productos de la lista de deseos con anotaciones de rating
        productos_queryset = Producto.objects.filter(disponible=True).select_related('categoria').prefetch_related('imagenes').annotate(
            annotated_avg_rating=Avg('resenas__calificacion', filter=Q(resenas__aprobado=True)),
            annotated_count_reviews=Count('resenas', filter=Q(resenas__aprobado=True))
        )

        return super().get_queryset().filter(
            cliente__usuario=self.request.user
        ).prefetch_related(
            Prefetch('productos', queryset=productos_queryset)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class CrearResenaView(LoginRequiredMixin, CreateView):
    model = Resena
    form_class = ResenaForm # Usar ResenaForm
    template_name = 'post/crear_resena.html'    # Corregido

    def dispatch(self, request, *args, **kwargs):
        # Optimización: prefetch_related para la imagen del producto
        self.producto = get_object_or_404(
            Producto.objects.prefetch_related('imagenes'),
            id=self.kwargs['producto_id']
        )
        self.cliente, cliente_created = Cliente.objects.get_or_create(
            usuario=request.user,
            defaults={
                'email': request.user.email,
                'nombre': request.user.first_name or request.user.username,
                'apellido': request.user.last_name or '',
            }
        )
        
        if Resena.objects.filter(producto=self.producto, cliente=self.cliente).exists():
            messages.error(request, "Ya has dejado una reseña para este producto.")
            return redirect('tienda:detalle_producto', pk=self.producto.id, slug=self.producto.slug)

        return super().dispatch(request, *args, **kwargs)
        
    def form_valid(self, form):
        form.instance.producto = self.producto
        form.instance.cliente = self.cliente # Cliente obtenido/creado en dispatch
        # form.instance.aprobado = True # Ahora es True por defecto en el modelo
        messages.success(self.request, "Gracias por tu reseña. Ha sido publicada exitosamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('tienda:detalle_producto', kwargs={'pk': self.producto.id, 'slug': self.producto.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['producto'] = self.producto
        return context

# Nueva vista de registro:
def registro_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # Usar el nuevo form
        if form.is_valid():
            user = form.save() # El método save del CustomUserCreationForm ya guarda email, first_name, last_name

            # El objeto Cliente asociado se crea automáticamente mediante una señal post_save en el modelo User.

            auth_login(request, user) # Loguear al usuario automáticamente
            messages.success(request, f"¡Bienvenido, {user.username}! Tu cuenta ha sido creada exitosamente.")
            return redirect('tienda:cuenta_dashboard') # O 'tienda:inicio'
    else:
        form = CustomUserCreationForm()

    return render(request, 'post/auth/registro.html', {'form': form})

# --- Vistas de Páginas Estáticas/Informativas ---

class PaginaEstaticaView(TemplateView):
    """Vista base para páginas con contenido de ConfiguracionTienda."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionTienda.obtener_configuracion()
        return context

class PaginaContactoView(PaginaEstaticaView):
    template_name = 'post/contacto.html'   # Corregido

class PoliticaPrivacidadView(PaginaEstaticaView):
    template_name = 'post/pagina_info.html'    # Corregido
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Política de Privacidad'
        context['contenido'] = context['config'].politica_privacidad if context['config'] else ""
        return context

class TerminosCondicionesView(PaginaEstaticaView):
    template_name = 'post/pagina_info.html'    # Corregido
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Términos y Condiciones'
        context['contenido'] = context['config'].terminos_condiciones if context['config'] else ""
        return context

class SobreNosotrosView(PaginaEstaticaView):
    template_name = 'post/pagina_info.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Sobre Nosotros'
        # Attempt to get content from a field like 'sobre_nosotros_info' or 'sobre_nosotros'
        # Provide a default if the field doesn't exist or config is None
        if context['config']:
            context['contenido'] = getattr(context['config'], 'sobre_nosotros', "Información sobre nosotros no disponible.")
        else:
            context['contenido'] = "Información sobre nosotros no disponible."
        return context

# --- Vistas de Administración (Protegidas) ---
@user_passes_test(lambda u: u.is_staff)
@login_required
def agregar_producto_admin_view(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f"Producto '{producto.nombre}' agregado exitosamente.")
            # Redirigir al detalle del producto o a la lista de productos del admin
            return redirect(reverse('tienda:detalle_producto', kwargs={'pk': producto.pk, 'slug': producto.slug}))
    else:
        form = ProductoForm()

    return render(request, 'post/admin/agregar_producto.html', {'form': form})

@user_passes_test(lambda u: u.is_staff)
@login_required
def agregar_promocion_admin_view(request):
    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            cupon = form.save()
            messages.success(request, f"Promoción '{cupon.codigo}' agregada exitosamente.")
            # Redirigir al índice del panel de administración
            return redirect(reverse('admin:index')) # Redirección corregida
    else:
        form = CuponForm()

    return render(request, 'post/admin/agregar_promocion.html', {'form': form})

def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin:index')

    if request.method == 'POST':
        form = AdminAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_staff:
                auth_login(request, user)
                return redirect('admin:index')
            else:
                messages.error(request, 'Este usuario no tiene permisos de administrador.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AdminAuthenticationForm()

    return render(request, 'post/auth/admin_login.html', {'form': form})


class CustomLoginView(LoginView):
    form_class = UnifiedAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        admin_code = form.cleaned_data.get('admin_code')
        correct_code = getattr(settings, 'ADMIN_LOGIN_CODE', None)

        if admin_code:
            if admin_code == correct_code:
                if user.is_staff:
                    auth_login(self.request, user)
                    messages.success(self.request, f"Bienvenido administrador, {user.username}.")
                    return redirect('admin:index')
                else:
                    form.add_error('admin_code', 'Este usuario no tiene permisos de administrador.')
                    return self.form_invalid(form)
            else:
                form.add_error('admin_code', 'El código de administrador no es válido.')
                return self.form_invalid(form)

        # Inicio de sesión normal para clientes (y admins sin código si se desea permitir)
        auth_login(self.request, user)
        messages.success(self.request, f"¡Bienvenido de nuevo, {user.username}!")
        return redirect(self.get_success_url())
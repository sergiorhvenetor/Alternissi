from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    View, TemplateView, ListView, DetailView, CreateView, UpdateView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction

# Importa todos los modelos necesarios
from .models import (
    Producto, Categoria, Marca, Carrito, ItemCarrito, 
    Pedido, Cliente, ListaDeseos, Resena, Cupon, ConfiguracionTienda
)
# Asumimos que tendrás un archivo forms.py con estos formularios
# from .forms import ResenaForm, ClienteForm, DireccionForm

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
                defaults={'email': self.request.user.email, 'nombre': self.request.user.first_name or self.request.user.username}
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
        # Original:
        # context['productos_destacados'] = Producto.objects.filter(disponible=True, destacado=True)[:8]
        # context['productos_nuevos'] = Producto.objects.filter(disponible=True, nuevo=True)[:8]

        # Modificado:
        context['productos_destacados'] = Producto.objects.filter(disponible=True, destacado=True).prefetch_related('imagenes')[:8]
        context['productos_nuevos'] = Producto.objects.filter(disponible=True, nuevo=True).prefetch_related('imagenes')[:8]

        context['categorias'] = Categoria.objects.filter(activo=True)
        # Añadir configuración de la tienda para el símbolo de moneda
        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
        return context

class ListaProductosView(ListView):
    """Muestra una lista paginada de productos, con filtros opcionales."""
    model = Producto
    template_name = 'post/lista_productos.html' # Corrected path
    context_object_name = 'productos'
    paginate_by = 12

    def get_queryset(self):
        # Original: queryset = super().get_queryset().filter(disponible=True)
        queryset = super().get_queryset().filter(disponible=True).select_related('categoria', 'marca').prefetch_related('imagenes')

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
    # slug_field = 'slug' # Already present in models.py get_absolute_url
    # slug_url_kwarg = 'slug' # Already present in models.py get_absolute_url

    def get_queryset(self):
        # Original: return super().get_queryset().filter(disponible=True)
        return super().get_queryset().filter(disponible=True).select_related('categoria', 'marca').prefetch_related('imagenes', 'resenas__cliente')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # El objeto producto ya está en el contexto por DetailView

        producto = self.get_object() # Obtener el objeto una vez
        # imagenes are preloaded by prefetch_related('imagenes')
        # resenas are preloaded by prefetch_related('resenas__cliente')
        # context['imagenes'] = producto.imagenes.all() # Not strictly needed if template uses producto.imagenes.all
        context['resenas'] = producto.resenas.filter(aprobado=True) # Filter preloaded resenas

        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
        # context['resena_form'] = ResenaForm() # Se mantiene comentado como en el original
        return context

class BuscarProductosView(ListView):
    """Vista para el motor de búsqueda de productos."""
    model = Producto
    template_name = 'tienda/resultados_busqueda.html'
    context_object_name = 'productos'
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Producto.objects.filter(
                Q(nombre__icontains=query) | Q(descripcion__icontains=query) | Q(sku__iexact=query)
            ).filter(disponible=True)
        return Producto.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

# --- Vistas del Carrito de Compras ---

class VerCarritoView(CartMixin, TemplateView):
    """Muestra el contenido del carrito de compras."""
    template_name = 'post/carrito.html' # Corregido

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_cart() # Obtiene el carrito del mixin optimizado
        context['carrito'] = cart

        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
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
        return redirect('tienda:ver_carrito')

class ActualizarItemCarritoView(View):
    """Actualiza la cantidad de un item en el carrito (AJAX)."""
    def post(self, request, *args, **kwargs):
        try:
            item = get_object_or_404(ItemCarrito, id=self.kwargs.get('item_id'))
            cantidad = int(request.POST.get('cantidad', 1))

            if 0 < cantidad <= item.producto.stock:
                item.cantidad = cantidad
                item.save()
                return JsonResponse({'success': True, 'item_subtotal': item.subtotal, 'cart_total': item.carrito.total})
            else:
                return JsonResponse({'success': False, 'message': 'Cantidad no válida o stock insuficiente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

class EliminarItemCarritoView(View):
    """Elimina un item del carrito."""
    def get(self, request, *args, **kwargs): # Se puede usar POST también
        item = get_object_or_404(ItemCarrito, id=self.kwargs.get('item_id'))
        nombre_producto = item.producto.nombre
        item.delete()
        messages.info(request, f"'{nombre_producto}' eliminado del carrito.")
        return redirect('tienda:ver_carrito')

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
        context['carrito'] = self.get_cart()

        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'

        # Pasar las choices del método de pago al template
        context['pedido_metodos_pago_choices'] = Pedido.MetodoPago.choices

        # context['direccion_form'] = DireccionForm(...) # Comentado como en el original
        return context

class ProcesarPedidoView(LoginRequiredMixin, CartMixin, View):
    """Procesa el carrito y lo convierte en un pedido."""
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        cart = self.get_cart()
        cliente = get_object_or_404(Cliente, usuario=request.user)

        # Reemplaza esto con la validación de tus formularios de dirección
        direccion_envio = {'calle': 'Calle Falsa 123', 'ciudad': 'Springfield'}
        direccion_facturacion = direccion_envio
        metodo_pago = request.POST.get('metodo_pago', Pedido.MetodoPago.TARJETA)
        
        try:
            pedido = cart.convertir_a_pedido(
                cliente=cliente, direccion_envio=direccion_envio, 
                direccion_facturacion=direccion_facturacion, metodo_pago=metodo_pago
            )
            # Lógica de pago iría aquí
            # pedido.marcar_como_pagado('id_transaccion')
            messages.success(request, f"¡Gracias! Tu pedido #{pedido.codigo} ha sido creado.")
            return redirect('tienda:pedido_completado', pedido_id=pedido.id)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('tienda:ver_carrito')

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
        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
        return context

class PagoCanceladoView(TemplateView):
    """Página si el pago es cancelado."""
    template_name = 'tienda/pago_cancelado.html'

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
        # self.object es el cliente obtenido por get_object()
        # Original: context['ultimos_pedidos'] = self.object.pedidos.all()[:5]
        # Optimizado:
        context['ultimos_pedidos'] = self.object.pedidos.select_related('cupon').order_by('-creado')[:5]

        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
        return context

class ListaPedidosClienteView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = 'post/cuenta/lista_pedidos.html'    # Corregido
    context_object_name = 'pedidos'
    paginate_by = 10 # Añadir paginación

    def get_queryset(self):
        # Original: return Pedido.objects.filter(cliente__usuario=self.request.user)
        return Pedido.objects.filter(
            cliente__usuario=self.request.user
        ).select_related('cupon').order_by('-creado') # Optimizar y ordenar

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
        return context

class DetallePedidoClienteView(LoginRequiredMixin, DetailView):
    model = Pedido
    template_name = 'post/cuenta/detalle_pedido.html'    # Corregido
    context_object_name = 'pedido'
    pk_url_kwarg = 'pedido_id' # Ya estaba definido

    def get_queryset(self):
        # Original: return super().get_queryset().filter(cliente__usuario=self.request.user)
        return super().get_queryset().filter(
            cliente__usuario=self.request.user
        ).select_related(
            'cliente', 'cupon' # Cliente ya está implícito por el filtro, pero no daña.
        ).prefetch_related(
            'detalles__producto__imagenes'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$'
        return context

class EditarPerfilClienteView(LoginRequiredMixin, UpdateView):
    model = Cliente
    template_name = 'post/cuenta/editar_perfil.html'    # Corregido
    success_url = reverse_lazy('tienda:cuenta_dashboard') # Ya estaba

    # Actualizar fields para incluir los campos del template.
    # Idealmente, esto sería un form_class = ClienteForm
    fields = ['nombre', 'apellido', 'email', 'telefono', 'direccion', 'ciudad', 'codigo_postal', 'pais', 'fecha_nacimiento']

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
        config = ConfiguracionTienda.obtener_configuracion()
        context['moneda_simbolo'] = config.simbolo_moneda if config else '$' # Por consistencia
        return context

    def form_valid(self, form):
        messages.success(self.request, "Tu perfil ha sido actualizado.")
        return super().form_valid(form)

# --- Vistas de Lista de Deseos y Reseñas ---

class VerListaDeseosView(LoginRequiredMixin, DetailView):
    model = ListaDeseos
    template_name = 'tienda/lista_deseos.html'
    context_object_name = 'lista_deseos'
    
    def get_object(self):
        cliente = get_object_or_404(Cliente, usuario=self.request.user)
        lista, _ = ListaDeseos.objects.get_or_create(cliente=cliente)
        return lista

class CrearResenaView(LoginRequiredMixin, CreateView):
    model = Resena
    # form_class = ResenaForm
    fields = ['titulo', 'comentario', 'calificacion'] # Ejemplo
    template_name = 'tienda/crear_resena.html'

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, id=self.kwargs['producto_id'])
        self.cliente = get_object_or_404(Cliente, usuario=request.user)
        
        # Validaciones antes de mostrar el formulario
        if not Pedido.objects.filter(cliente=self.cliente, detalles__producto=self.producto, estado=Pedido.Estado.COMPLETADO).exists():
            messages.error(request, "Solo puedes reseñar productos que has comprado.")
            return redirect('tienda:detalle_producto', pk=self.producto.id, slug=self.producto.slug)
        if Resena.objects.filter(producto=self.producto, cliente=self.cliente).exists():
            messages.error(request, "Ya has dejado una reseña para este producto.")
            return redirect('tienda:detalle_producto', pk=self.producto.id, slug=self.producto.slug)

        return super().dispatch(request, *args, **kwargs)
        
    def form_valid(self, form):
        form.instance.producto = self.producto
        form.instance.cliente = self.cliente
        messages.success(self.request, "Gracias por tu reseña. Será publicada tras su aprobación.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('tienda:detalle_producto', kwargs={'pk': self.producto.id, 'slug': self.producto.slug})

# --- Vistas de Páginas Estáticas/Informativas ---

class PaginaEstaticaView(TemplateView):
    """Vista base para páginas con contenido de ConfiguracionTienda."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionTienda.obtener_configuracion()
        return context

class PaginaContactoView(PaginaEstaticaView):
    template_name = 'tienda/contacto.html'

class PoliticaPrivacidadView(PaginaEstaticaView):
    template_name = 'tienda/pagina_info.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Política de Privacidad'
        context['contenido'] = context['config'].politica_privacidad if context['config'] else ""
        return context

class TerminosCondicionesView(PaginaEstaticaView):
    template_name = 'tienda/pagina_info.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Términos y Condiciones'
        context['contenido'] = context['config'].terminos_condiciones if context['config'] else ""
        return context
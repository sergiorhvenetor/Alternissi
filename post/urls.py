from django.urls import path
# Importamos las clases de las vistas
from . import views

app_name = 'post'

urlpatterns = [
    # --- URLs principales de la tienda ---
    path('', views.InicioTiendaView.as_view(), name='inicio'),
    path('productos/', views.ListaProductosView.as_view(), name='lista_productos'),
    path('categoria/<slug:categoria_slug>/', views.ListaProductosView.as_view(), name='productos_por_categoria'),
    path('marca/<slug:marca_slug>/', views.ListaProductosView.as_view(), name='productos_por_marca'),
    path('producto/<int:pk>/<slug:slug>/', views.DetalleProductoView.as_view(), name='detalle_producto'),
    path('buscar/', views.BuscarProductosView.as_view(), name='buscar'),

    # --- URLs del Carrito de Compras (Carrito) ---
    path('carrito/', views.VerCarritoView.as_view(), name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.AgregarAlCarritoView.as_view(), name='agregar_al_carrito'),
    path('carrito/actualizar/<int:item_id>/', views.ActualizarItemCarritoView.as_view(), name='actualizar_item_carrito'),
    path('carrito/eliminar/<int:item_id>/', views.EliminarItemCarritoView.as_view(), name='eliminar_item_carrito'),
    path('carrito/aplicar-cupon/', views.AplicarCuponView.as_view(), name='aplicar_cupon'),

    # --- URLs del Proceso de Pago (Checkout) ---
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('checkout/procesar-pedido/', views.ProcesarPedidoView.as_view(), name='procesar_pedido'),
    path('checkout/pedido-completado/<int:pedido_id>/', views.PedidoCompletadoView.as_view(), name='pedido_completado'),
    path('checkout/cancelado/', views.PagoCanceladoView.as_view(), name='pago_cancelado'),
    
    # --- URLs de la Cuenta del Cliente ---
    path('cuenta/', views.CuentaDashboardView.as_view(), name='cuenta_dashboard'),
    path('cuenta/pedidos/', views.ListaPedidosClienteView.as_view(), name='lista_pedidos_cliente'),
    path('cuenta/pedidos/<int:pedido_id>/', views.DetallePedidoClienteView.as_view(), name='detalle_pedido_cliente'),
    path('cuenta/perfil/', views.EditarPerfilClienteView.as_view(), name='editar_perfil_cliente'),
    
    # --- URLs de la Lista de Deseos (ListaDeseos) ---
    path('lista-deseos/', views.VerListaDeseosView.as_view(), name='ver_lista_deseos'),
    
    # NOTA: Las siguientes vistas para agregar/eliminar de la lista de deseos no están en el
    # views.py que me pasaste, pero serían el siguiente paso lógico. Deberías crearlas
    # de forma similar a 'AgregarAlCarritoView'.
    # path('lista-deseos/agregar/<int:producto_id>/', views.AgregarAListaDeseosView.as_view(), name='agregar_a_lista_deseos'),
    # path('lista-deseos/eliminar/<int:producto_id>/', views.EliminarDeListaDeseosView.as_view(), name='eliminar_de_lista_deseos'),
    
    # --- URLs para Reseñas de Productos ---
    path('producto/<int:producto_id>/crear-resena/', views.CrearResenaView.as_view(), name='crear_resena'),
    
    # --- URLs para páginas estáticas/informativas ---
    path('contacto/', views.PaginaContactoView.as_view(), name='contacto'),
    path('politica-privacidad/', views.PoliticaPrivacidadView.as_view(), name='politica_privacidad'),
    path('terminos-condiciones/', views.TerminosCondicionesView.as_view(), name='terminos_condiciones'),
]
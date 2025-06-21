from django.urls import path
# Importamos las clases de las vistas
from . import views
from django.contrib.auth import views as auth_views # Added for auth views
from django.urls import reverse_lazy # Added for password reset URLs

app_name = 'tienda' # Changed from 'post'

urlpatterns = [
    # Auth URLs
    path('login/', auth_views.LoginView.as_view(template_name='post/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='tienda:inicio'), name='logout'),
    path('registro/', views.registro_view, name='registro'), # Vista de registro
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='post/auth/password_reset_form.html',
             email_template_name='post/auth/password_reset_email.html',
             subject_template_name='post/auth/password_reset_subject.txt',
             success_url=reverse_lazy('tienda:password_reset_done')
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='post/auth/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='post/auth/password_reset_confirm.html',
             success_url=reverse_lazy('tienda:password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='post/auth/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    path('cuenta/cambiar-password/',
         auth_views.PasswordChangeView.as_view(
             template_name='post/auth/password_change_form.html',
             success_url=reverse_lazy('tienda:password_change_done')
         ),
         name='password_change'),
    path('cuenta/cambiar-password/done/',
         auth_views.PasswordChangeDoneView.as_view(
             template_name='post/auth/password_change_done.html'
         ),
         name='password_change_done'),


    

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
    path('deseos/agregar/<int:producto_id>/', views.AgregarAListaDeseosView.as_view(), name='agregar_a_lista_deseos'),
    path('deseos/eliminar/<int:producto_id>/', views.EliminarDeListaDeseosView.as_view(), name='eliminar_de_lista_deseos'),
    path('deseos/mover-a-carrito/<int:producto_id>/', views.MoverDeseoACarritoView.as_view(), name='mover_deseo_a_carrito'),
    
    # --- URLs para Reseñas de Productos ---
    path('producto/<int:producto_id>/crear-resena/', views.CrearResenaView.as_view(), name='crear_resena'),
    
    # --- URLs para páginas estáticas/informativas ---
    path('contacto/', views.PaginaContactoView.as_view(), name='contacto'),
    path('politica-privacidad/', views.PoliticaPrivacidadView.as_view(), name='politica_privacidad'),
    path('terminos-condiciones/', views.TerminosCondicionesView.as_view(), name='terminos_condiciones'),

    # --- URLs de Administración ---
    path('admin/productos/nuevo/', views.agregar_producto_admin_view, name='admin_agregar_producto'),
    path('admin/promociones/nuevo/', views.agregar_promocion_admin_view, name='admin_agregar_promocion'),
]
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import *

class TimeStampedModelAdmin(admin.ModelAdmin):
    readonly_fields = ('creado', 'actualizado')
    list_filter = ('creado', 'actualizado')

@admin.register(Categoria)
class CategoriaAdmin(TimeStampedModelAdmin):
    list_display = ('nombre', 'activo', 'orden', 'imagen_previa', 'productos_count')
    list_editable = ('activo', 'orden')
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    actions = ['activar_categorias', 'desactivar_categorias']
    readonly_fields = ('imagen_previa',)
    fieldsets = (
        (None, {'fields': ('nombre', 'slug', 'descripcion', 'activo', 'orden')}),
        ('Imagen', {'fields': ('imagen', 'imagen_previa'), 'classes': ('collapse',)}),
    )

    def imagen_previa(self, obj):
        return format_html('<img src="{}" style="max-height: 50px;" />', obj.imagen.url) if obj.imagen else "-"
    imagen_previa.short_description = 'Vista previa'

    def productos_count(self, obj):
        return obj.productos.count()
    productos_count.short_description = 'Productos'

    def activar_categorias(self, request, queryset):
        queryset.update(activo=True)
    activar_categorias.short_description = "Activar categorías seleccionadas"

    def desactivar_categorias(self, request, queryset):
        queryset.update(activo=False)
    desactivar_categorias.short_description = "Desactivar categorías seleccionadas"

@admin.register(Marca)
class MarcaAdmin(TimeStampedModelAdmin):
    list_display = ('nombre', 'activo', 'logo_previa', 'productos_count', 'sitio_web')
    list_editable = ('activo',)
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    readonly_fields = ('logo_previa',)
    fieldsets = (
        (None, {'fields': ('nombre', 'slug', 'descripcion', 'activo', 'sitio_web')}),
        ('Logo', {'fields': ('logo', 'logo_previa'), 'classes': ('collapse',)}),
    )

    def logo_previa(self, obj):
        return format_html('<img src="{}" style="max-height: 50px;" />', obj.logo.url) if obj.logo else "-"
    logo_previa.short_description = 'Logo'

    def productos_count(self, obj):
        return obj.productos.count()
    productos_count.short_description = 'Productos'

class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1
    readonly_fields = ('imagen_previa',)
    fields = ('imagen', 'imagen_previa', 'orden', 'principal', 'alt_text')

    def imagen_previa(self, obj):
        return format_html('<img src="{}" style="max-height: 50px;" />', obj.imagen.url) if obj.imagen else "-"
    imagen_previa.short_description = 'Vista previa'

class EtiquetaProductoFilter(admin.SimpleListFilter):
    title = _('etiquetas')
    parameter_name = 'etiquetas'

    def lookups(self, request, model_admin):
        return [(e.id, e.nombre) for e in EtiquetaProducto.objects.all()]

    def queryset(self, request, queryset):
        return queryset.filter(etiquetas__id=self.value()) if self.value() else queryset

@admin.register(Producto)
class ProductoAdmin(TimeStampedModelAdmin):
    list_display = ('nombre', 'precio_actual', 'categoria', 'marca', 'stock', 'disponible', 'destacado', 'nuevo', 'tiene_descuento', 'imagen_principal')
    list_editable = ('stock', 'disponible', 'destacado', 'nuevo')
    list_filter = ('disponible', 'destacado', 'nuevo', 'categoria', 'marca', 'talla', 'genero', EtiquetaProductoFilter, 'creado')
    search_fields = ('nombre', 'sku', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    readonly_fields = ('sku', 'imagen_principal', 'porcentaje_descuento')
    filter_horizontal = ('etiquetas',)
    inlines = [ImagenProductoInline]
    actions = ['hacer_destacados', 'quitar_destacados', 'marcar_como_nuevos', 'actualizar_precios']
    fieldsets = (
        (None, {'fields': ('nombre', 'slug', 'sku', 'descripcion', 'caracteristicas')}),
        ('Precios', {'fields': ('precio', 'precio_descuento', 'porcentaje_descuento'), 'classes': ('collapse',)}),
        ('Inventario', {'fields': ('stock', 'disponible'), 'classes': ('collapse',)}),
        ('Categorización', {'fields': ('categoria', 'marca', 'etiquetas'), 'classes': ('collapse',)}),
        ('Detalles', {'fields': ('talla', 'genero', 'color', 'material'), 'classes': ('collapse',)}),
        ('Promociones', {'fields': ('destacado', 'nuevo'), 'classes': ('collapse',)}),
    )

    def imagen_principal(self, obj):
        img = obj.imagenes.filter(principal=True).first()
        return format_html('<img src="{}" style="max-height: 50px;" />', img.imagen.url) if img else "-"
    imagen_principal.short_description = 'Imagen'

    def precio_actual(self, obj):
        if obj.tiene_descuento:
            return format_html('<span style="color: red; text-decoration: line-through;">{}</span> {}', obj.precio, obj.precio_descuento)
        return obj.precio
    precio_actual.short_description = 'Precio'

    def tiene_descuento(self, obj):
        return obj.tiene_descuento
    tiene_descuento.boolean = True
    tiene_descuento.short_description = 'Oferta'

    def hacer_destacados(self, request, queryset):
        queryset.update(destacado=True)
    hacer_destacados.short_description = "Marcar como destacados"

    def quitar_destacados(self, request, queryset):
        queryset.update(destacado=False)
    quitar_destacados.short_description = "Quitar de destacados"

    def marcar_como_nuevos(self, request, queryset):
        queryset.update(nuevo=True)
    marcar_como_nuevos.short_description = "Marcar como nuevos"

    def actualizar_precios(self, request, queryset):
        for producto in queryset:
            if producto.precio_descuento and producto.precio_descuento >= producto.precio:
                producto.precio_descuento = None
                producto.save()
    actualizar_precios.short_description = "Corregir precios con descuento"

@admin.register(EtiquetaProducto)
class EtiquetaProductoAdmin(TimeStampedModelAdmin):
    list_display = ('nombre', 'color_muestra', 'productos_count')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}

    def color_muestra(self, obj):
        return format_html('<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #000;"></div>', obj.color)
    color_muestra.short_description = 'Color'

    def productos_count(self, obj):
        return obj.producto_set.count()
    productos_count.short_description = 'Productos'

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ('subtotal',)
    fields = ('producto', 'precio', 'cantidad', 'subtotal')

@admin.register(Pedido)
class PedidoAdmin(TimeStampedModelAdmin):
    list_display = ('codigo', 'cliente', 'estado', 'metodo_pago', 'total', 'fecha_creado')
    list_filter = ('estado', 'metodo_pago', 'creado')
    search_fields = ('codigo', 'cliente__nombre', 'cliente__apellido', 'cliente__email')
    readonly_fields = ('codigo', 'fecha_creado')
    inlines = [DetallePedidoInline]
    actions = ['marcar_como_enviados', 'marcar_como_completados']
    fieldsets = (
        (None, {'fields': ('codigo', 'cliente', 'estado', 'metodo_pago')}),
        ('Direcciones', {'fields': ('direccion_envio', 'direccion_facturacion'), 'classes': ('collapse',)}),
        ('Pagos', {'fields': ('subtotal', 'descuento', 'impuesto', 'envio', 'total', 'transaccion_id'), 'classes': ('collapse',)}),
        ('Otros', {'fields': ('notas', 'cupon'), 'classes': ('collapse',)}),
    )

    def fecha_creado(self, obj):
        return obj.creado
    fecha_creado.short_description = 'Fecha'

    def marcar_como_enviados(self, request, queryset):
        queryset.update(estado='enviado')
    marcar_como_enviados.short_description = "Marcar como enviados"

    def marcar_como_completados(self, request, queryset):
        queryset.update(estado='completado')
    marcar_como_completados.short_description = "Marcar como completados"

@admin.register(Resena)
class ResenaAdmin(TimeStampedModelAdmin):
    list_display = ('producto', 'cliente', 'calificacion', 'aprobado', 'fecha_creado')
    list_filter = ('aprobado', 'calificacion', 'creado')
    search_fields = ('producto__nombre', 'cliente__nombre', 'cliente__apellido')
    list_editable = ('aprobado',)
    actions = ['aprobar_resenas', 'desaprobar_resenas']
    readonly_fields = ('fecha_creado', 'fecha_respuesta')

    def fecha_creado(self, obj):
        return obj.creado
    fecha_creado.short_description = 'Fecha'

    def fecha_respuesta(self, obj):
        return obj.respuesta_fecha
    fecha_respuesta.short_description = 'Fecha respuesta'

    def aprobar_resenas(self, request, queryset):
        queryset.update(aprobado=True)
    aprobar_resenas.short_description = "Aprobar reseñas seleccionadas"

    def desaprobar_resenas(self, request, queryset):
        queryset.update(aprobado=False)
    desaprobar_resenas.short_description = "Desaprobar reseñas seleccionadas"

@admin.register(Cupon)
class CuponAdmin(TimeStampedModelAdmin):
    list_display = ('codigo', 'tipo_descuento', 'descuento', 'fecha_inicio', 'fecha_fin', 'activo', 'usos_actuales')
    list_filter = ('activo', 'tipo_descuento', 'fecha_inicio', 'fecha_fin')
    search_fields = ('codigo', 'descripcion')
    actions = ['activar_cupones', 'desactivar_cupones']
    filter_horizontal = ('categorias', 'productos')
    fieldsets = (
        (None, {'fields': ('codigo', 'descripcion', 'tipo_descuento', 'descuento', 'activo')}),
        ('Fechas', {'fields': ('fecha_inicio', 'fecha_fin')}),
        ('Límites', {'fields': ('max_usos', 'usos_actuales', 'minimo_compra', 'solo_nuevos_clientes')}),
        ('Aplicación', {'fields': ('categorias', 'productos')}),
    )

    def activar_cupones(self, request, queryset):
        queryset.update(activo=True)
    activar_cupones.short_description = "Activar cupones seleccionados"

    def desactivar_cupones(self, request, queryset):
        queryset.update(activo=False)
    desactivar_cupones.short_description = "Desactivar cupones seleccionados"

class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    readonly_fields = ('subtotal',)
    fields = ('producto', 'precio', 'cantidad', 'subtotal')

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_info', 'total_items', 'subtotal', 'fecha_creado')
    list_filter = ('creado',)
    search_fields = ('cliente__nombre', 'cliente__apellido', 'cliente__email')
    readonly_fields = ('fecha_creado', 'fecha_actualizado')
    inlines = [ItemCarritoInline]

    def cliente_info(self, obj):
        return obj.cliente.nombre_completo if obj.cliente else f"Sesión: {obj.session_key}"
    cliente_info.short_description = 'Cliente'

    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Items'

    def fecha_creado(self, obj):
        return obj.creado
    fecha_creado.short_description = 'Creado'

    def fecha_actualizado(self, obj):
        return obj.actualizado
    fecha_actualizado.short_description = 'Actualizado'

@admin.register(Cliente)
class ClienteAdmin(TimeStampedModelAdmin):
    list_display = ('nombre_completo', 'email', 'telefono', 'ciudad', 'pedidos_count', 'fecha_registro')
    search_fields = ('nombre', 'apellido', 'email', 'telefono', 'ciudad')
    list_filter = ('ciudad', 'acepta_marketing', 'creado')
    fieldsets = (
        (None, {'fields': ('usuario', 'nombre', 'apellido', 'email', 'telefono')}),
        ('Dirección', {'fields': ('direccion', 'ciudad', 'codigo_postal', 'pais')}),
        ('Otros', {'fields': ('fecha_nacimiento', 'acepta_marketing')}),
    )

    def nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"
    nombre_completo.short_description = 'Nombre'

    def pedidos_count(self, obj):
        return obj.pedidos.count()
    pedidos_count.short_description = 'Pedidos'

    def fecha_registro(self, obj):
        return obj.creado
    fecha_registro.short_description = 'Registro'

@admin.register(ListaDeseos)
class ListaDeseosAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'productos_count', 'fecha_creado')
    search_fields = ('cliente__nombre', 'cliente__apellido')
    filter_horizontal = ('productos',)
    readonly_fields = ('fecha_creado', 'fecha_actualizado')

    def productos_count(self, obj):
        return obj.productos.count()
    productos_count.short_description = 'Productos'

    def fecha_creado(self, obj):
        return obj.creado
    fecha_creado.short_description = 'Creado'

    def fecha_actualizado(self, obj):
        return obj.actualizado
    fecha_actualizado.short_description = 'Actualizado'

@admin.register(ConfiguracionTienda)
class ConfiguracionTiendaAdmin(admin.ModelAdmin):
    list_display = ('nombre_tienda', 'moneda', 'impuesto', 'modo_mantenimiento')
    fieldsets = (
        ('Información Básica', {'fields': ('nombre_tienda', 'logo', 'logo_alt_text', 'activo')}),
        ('Moneda y Precios', {'fields': ('moneda', 'simbolo_moneda', 'impuesto')}),
        ('Envío', {'fields': ('costo_envio', 'minimo_compra_envio_gratis')}),
        ('Contacto', {'fields': ('telefono_contacto', 'email_contacto', 'direccion', 'horario_atencion')}),
        ('Redes Sociales', {'fields': ('redes_sociales',)}),
        ('Legal', {'fields': ('politica_privacidad', 'terminos_condiciones')}),
        ('Mantenimiento', {'fields': ('modo_mantenimiento', 'mensaje_mantenimiento')}),
    )

    def has_add_permission(self, request):
        return not ConfiguracionTienda.objects.exists()
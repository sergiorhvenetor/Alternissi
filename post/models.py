from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, F
import uuid

User = get_user_model()

class TimeStampedModel(models.Model):
    """Modelo abstracto para manejar campos de fecha de creación y actualización."""
    creado = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Categoria(TimeStampedModel):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['orden', 'nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tienda:productos_por_categoria', args=[self.slug])

    def clean(self):
        # Validación adicional si es necesaria
        if len(self.nombre) < 2:
            raise ValidationError("El nombre de la categoría es demasiado corto.")


class Marca(TimeStampedModel):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    descripcion = models.TextField(blank=True)
    logo = models.ImageField(upload_to='marcas/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    sitio_web = models.URLField(blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'marcas'
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre, allow_unicode=True)
        super().save(*args, **kwargs)


class Producto(TimeStampedModel):
    class Talla(models.TextChoices):
        XS = 'XS', 'Extra Small'
        S = 'S', 'Small'
        M = 'M', 'Medium'
        L = 'L', 'Large'
        XL = 'XL', 'Extra Large'
        XXL = 'XXL', 'Extra Extra Large'
        U = 'U', 'Única'

    class Genero(models.TextChoices):
        HOMBRE = 'H', 'Hombre'
        MUJER = 'M', 'Mujer'
        UNISEX = 'U', 'Unisex'
        NINO = 'N', 'Niño'

    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    sku = models.CharField(max_length=50, unique=True, editable=False, default=uuid.uuid4)
    descripcion = models.TextField()
    caracteristicas = models.JSONField(default=dict, blank=True)  # Django 5.0+ feature
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    precio_descuento = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Si se especifica, será el precio mostrado como oferta."
    )
    categoria = models.ForeignKey(
        Categoria, 
        related_name='productos', 
        on_delete=models.PROTECT
    )
    marca = models.ForeignKey(
        Marca, 
        related_name='productos', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    talla = models.CharField(
        max_length=4, 
        choices=Talla.choices, 
        default=Talla.U
    )
    genero = models.CharField(
        max_length=1, 
        choices=Genero.choices, 
        default=Genero.UNISEX
    )
    color = models.CharField(max_length=50)
    material = models.CharField(max_length=100)
    stock = models.PositiveIntegerField()
    disponible = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    nuevo = models.BooleanField(default=False)
    etiquetas = models.ManyToManyField('EtiquetaProducto', blank=True)

    class Meta:
        ordering = ['-creado']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['precio']),
            models.Index(fields=['disponible']),
            models.Index(fields=['destacado']),
            models.Index(fields=['nuevo']),
            models.Index(fields=['categoria', 'disponible']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(precio__gte=0),
                name='precio_positivo'
            ),
            models.CheckConstraint(
                check=Q(precio_descuento__isnull=True) | Q(precio_descuento__lt=F('precio')),
                name='descuento_valido'
            ),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tienda:detalle_producto', args=[self.id, self.slug])

    @property
    def tiene_descuento(self):
        return self.precio_descuento is not None and self.precio_descuento < self.precio

    @property
    def precio_actual(self):
        return self.precio_descuento if self.tiene_descuento else self.precio

    @property
    def porcentaje_descuento(self):
        if self.tiene_descuento:
            return int(100 - (self.precio_descuento * 100 / self.precio))
        return 0

    def reducir_stock(self, cantidad):
        """Reduce el stock y guarda el producto."""
        if cantidad > self.stock:
            raise ValueError("No hay suficiente stock disponible")
        self.stock -= cantidad
        self.save()


class EtiquetaProducto(TimeStampedModel):
    nombre = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, allow_unicode=True)
    color = models.CharField(max_length=7, default='#000000')  # Código HEX

    class Meta:
        ordering = ['nombre']
        verbose_name = 'etiqueta de producto'
        verbose_name_plural = 'etiquetas de producto'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre, allow_unicode=True)
        super().save(*args, **kwargs)


class ImagenProducto(TimeStampedModel):
    producto = models.ForeignKey(
        Producto, 
        related_name='imagenes', 
        on_delete=models.CASCADE
    )
    imagen = models.ImageField(
        upload_to='productos/', 
        help_text="Imagen del producto (recomendado 800x800px)"
    )
    orden = models.PositiveIntegerField(default=0)
    principal = models.BooleanField(default=False)
    alt_text = models.CharField(
        max_length=125, 
        blank=True,
        help_text="Texto alternativo para accesibilidad (SEO)"
    )

    class Meta:
        ordering = ['orden']
        verbose_name = 'imagen de producto'
        verbose_name_plural = 'imágenes de producto'
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'principal'],
                condition=Q(principal=True),
                name='unica_imagen_principal'
            )
        ]

    def __str__(self):
        return f"Imagen de {self.producto.nombre}"

    def save(self, *args, **kwargs):
        if self.principal:
            # Desmarcar cualquier otra imagen principal
            ImagenProducto.objects.filter(
                producto=self.producto,
                principal=True
            ).exclude(id=self.id).update(principal=False)
        
        if not self.alt_text:
            self.alt_text = f"Imagen de {self.producto.nombre}"
            
        super().save(*args, **kwargs)


class Cliente(TimeStampedModel):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cliente'
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    acepta_marketing = models.BooleanField(default=False)
    ROL_CLIENTE = 'cliente'
    ROL_ADMINISTRADOR = 'administrador'
    ROLES_USUARIO = [
        (ROL_CLIENTE, 'Cliente'),
        (ROL_ADMINISTRADOR, 'Administrador'),
    ]
    rol = models.CharField(
        max_length=20,
        choices=ROLES_USUARIO,
        default=ROL_CLIENTE,
        help_text='Rol del usuario en el sistema'
    )

    class Meta:
        ordering = ['apellido', 'nombre']
        indexes = [
            models.Index(fields=['apellido', 'nombre']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"


class Pedido(TimeStampedModel):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        PROCESANDO = 'procesando', 'Procesando'
        ENVIADO = 'enviado', 'Enviado'
        COMPLETADO = 'completado', 'Completado'
        CANCELADO = 'cancelado', 'Cancelado'
        REEMBOLSADO = 'reembolsado', 'Reembolsado'

    class MetodoPago(models.TextChoices):
        TARJETA = 'tarjeta', 'Tarjeta de Crédito/Débito'
        PAYPAL = 'paypal', 'PayPal'
        TRANSFERENCIA = 'transferencia', 'Transferencia Bancaria'
        CONTRAENTREGA = 'contraentrega', 'Contraentrega'

    cliente = models.ForeignKey(
        Cliente, 
        related_name='pedidos', 
        on_delete=models.PROTECT
    )
    codigo = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="Código único del pedido"
    )
    estado = models.CharField(
        max_length=20, 
        choices=Estado.choices, 
        default=Estado.PENDIENTE
    )
    metodo_pago = models.CharField(
        max_length=20, 
        choices=MetodoPago.choices
    )
    direccion_envio = models.JSONField()  # Almacena la dirección como JSON
    direccion_facturacion = models.JSONField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    envio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    notas = models.TextField(blank=True)
    transaccion_id = models.CharField(max_length=100, blank=True)
    cupon = models.ForeignKey(
        'Cupon', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        ordering = ['-creado']
        verbose_name_plural = 'pedidos'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['estado']),
            models.Index(fields=['cliente']),
            models.Index(fields=['creado']),
        ]

    def __str__(self):
        return f"Pedido #{self.codigo}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo_pedido()
        super().save(*args, **kwargs)

    def generar_codigo_pedido(self):
        """Genera un código único para el pedido."""
        fecha = timezone.now().strftime('%Y%m%d')
        ultimo_pedido = Pedido.objects.order_by('-id').first()
        numero = (ultimo_pedido.id + 1) if ultimo_pedido else 1
        return f"PED-{fecha}-{numero:04d}"

    @property
    def items(self):
        return self.detalles.all()

    def calcular_total(self):
        """Calcula el total del pedido basado en sus items."""
        agregado = self.detalles.aggregate(
            subtotal=Sum(F('precio') * F('cantidad'))
        )
        self.subtotal = agregado['subtotal'] or 0
        self.total = self.subtotal - self.descuento + self.impuesto + self.envio
        self.save()

    def marcar_como_pagado(self, transaccion_id):
        """Marca el pedido como pagado."""
        self.estado = self.Estado.PROCESANDO
        self.transaccion_id = transaccion_id
        self.save()


class DetallePedido(TimeStampedModel):
    pedido = models.ForeignKey(
        Pedido, 
        related_name='detalles', 
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT,
        related_name='ventas'
    )
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        ordering = ['pedido']
        verbose_name = 'detalle de pedido'
        verbose_name_plural = 'detalles de pedido'

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en {self.pedido}"

    def save(self, *args, **kwargs):
        self.subtotal = self.precio * self.cantidad
        super().save(*args, **kwargs)


class Resena(TimeStampedModel):
    producto = models.ForeignKey(
        Producto, 
        related_name='resenas', 
        on_delete=models.CASCADE
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE,
        related_name='resenas'
    )
    titulo = models.CharField(max_length=200)
    comentario = models.TextField()
    calificacion = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    aprobado = models.BooleanField(default=False)
    respuesta = models.TextField(blank=True)
    respuesta_fecha = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'reseña'
        verbose_name_plural = 'reseñas'
        unique_together = ('producto', 'cliente')
        constraints = [
            models.CheckConstraint(
                check=Q(calificacion__gte=1) & Q(calificacion__lte=5),
                name='calificacion_rango_valido'
            )
        ]

    def __str__(self):
        return f"Reseña de {self.cliente} para {self.producto}"

    def responder(self, respuesta):
        """Registra una respuesta a la reseña."""
        self.respuesta = respuesta
        self.respuesta_fecha = timezone.now()
        self.save()


class Cupon(TimeStampedModel):
    class TipoDescuento(models.TextChoices):
        PORCENTAJE = 'porcentaje', 'Porcentaje'
        FIJO = 'fijo', 'Monto Fijo'

    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    tipo_descuento = models.CharField(
        max_length=10, 
        choices=TipoDescuento.choices,
        default=TipoDescuento.PORCENTAJE
    )
    descuento = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    max_usos = models.PositiveIntegerField(default=0)  # 0 = ilimitado
    usos_actuales = models.PositiveIntegerField(default=0, editable=False)
    activo = models.BooleanField(default=True)
    minimo_compra = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    categorias = models.ManyToManyField(Categoria, blank=True)
    productos = models.ManyToManyField(Producto, blank=True)
    solo_nuevos_clientes = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name_plural = 'cupones'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
        ]

    def __str__(self):
        return self.codigo

    def es_valido(self, cliente=None, subtotal=0):
        """Verifica si el cupón es válido para su uso."""
        ahora = timezone.now()
        
        condiciones = [
            self.activo,
            self.fecha_inicio <= ahora <= self.fecha_fin,
            self.max_usos == 0 or self.usos_actuales < self.max_usos,
            subtotal >= (self.minimo_compra or 0)
        ]
        
        if self.solo_nuevos_clientes and cliente:
            condiciones.append(
                not cliente.pedidos.filter(estado=Pedido.Estado.COMPLETADO).exists()
            )
            
        return all(condiciones)

    def aplicar_descuento(self, monto):
        """Aplica el descuento al monto especificado."""
        if self.tipo_descuento == self.TipoDescuento.PORCENTAJE:
            return monto * (self.descuento / 100)
        return min(self.descuento, monto)

    def incrementar_uso(self):
        """Incrementa el contador de usos del cupón."""
        self.usos_actuales = models.F('usos_actuales') + 1
        self.save(update_fields=['usos_actuales'])


class Carrito(models.Model):
    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carrito'
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    cupon = models.ForeignKey(
        Cupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        if self.cliente:
            return f"Carrito de {self.cliente}"
        return f"Carrito (sesión: {self.session_key})"

    @property
    def total_items(self):
        return self.items.aggregate(total=Sum('cantidad'))['total'] or 0

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total(self):
        descuento = 0
        if self.cupon and self.cupon.es_valido(subtotal=self.subtotal):
            descuento = self.cupon.aplicar_descuento(self.subtotal)
        return self.subtotal - descuento

    def vaciar(self):
        """Elimina todos los items del carrito."""
        self.items.all().delete()
        self.cupon = None
        self.save()

    def convertir_a_pedido(self, cliente, direccion_envio, direccion_facturacion, metodo_pago):
        """Convierte el carrito en un pedido."""
        from django.db import transaction

        with transaction.atomic():
            pedido = Pedido.objects.create(
                cliente=cliente,
                direccion_envio=direccion_envio,
                direccion_facturacion=direccion_facturacion,
                metodo_pago=metodo_pago,
                subtotal=self.subtotal,
                descuento=self.subtotal - self.total,
                total=self.total,
                cupon=self.cupon
            )

            for item in self.items.all():
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    precio=item.precio,
                    cantidad=item.cantidad
                )
                item.producto.reducir_stock(item.cantidad)

            if self.cupon:
                self.cupon.incrementar_uso()

            self.vaciar()

        return pedido


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito, 
        related_name='items', 
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('carrito', 'producto')
        verbose_name = 'ítem de carrito'
        verbose_name_plural = 'ítems de carrito'

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    @property
    def subtotal(self):
        return self.precio * self.cantidad

    def save(self, *args, **kwargs):
        # Actualizar el precio al guardar para reflejar cambios en el producto
        self.precio = self.producto.precio_actual
        super().save(*args, **kwargs)


class ListaDeseos(models.Model):
    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='lista_deseos'
    )
    productos = models.ManyToManyField(Producto)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'lista de deseos'
        verbose_name_plural = 'listas de deseos'

    def __str__(self):
        return f"Lista de deseos de {self.cliente}"

    def agregar_producto(self, producto):
        """Agrega un producto a la lista de deseos."""
        self.productos.add(producto)

    def remover_producto(self, producto):
        """Remueve un producto de la lista de deseos."""
        self.productos.remove(producto)

    def mover_a_carrito(self, producto, carrito):
        """Mueve un producto de la lista de deseos al carrito."""
        item, created = carrito.items.get_or_create(
            producto=producto,
            defaults={'precio': producto.precio_actual}
        )
        if not created:
            item.cantidad += 1
            item.save()
        self.remover_producto(producto)


class ConfiguracionTienda(models.Model):
    nombre_tienda = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='configuracion/', blank=True, null=True)
    logo_alt_text = models.CharField(max_length=125, blank=True)
    moneda = models.CharField(max_length=10, default='USD')
    simbolo_moneda = models.CharField(max_length=1, default='$')
    impuesto = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimo_compra_envio_gratis = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    telefono_contacto = models.CharField(max_length=20, blank=True)
    email_contacto = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    horario_atencion = models.CharField(max_length=100, blank=True)
    redes_sociales = models.JSONField(default=dict, blank=True)  # {facebook: url, instagram: url, etc.}
    politica_privacidad = models.TextField(blank=True)
    terminos_condiciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    modo_mantenimiento = models.BooleanField(
        default=False,
        help_text="Cuando está activo, solo los superusuarios pueden acceder al sitio."
    )
    mensaje_mantenimiento = models.TextField(blank=True)

    class Meta:
        verbose_name = 'configuración de tienda'
        verbose_name_plural = 'configuraciones de tienda'
        constraints = [
            models.CheckConstraint(
                check=Q(impuesto__gte=0),
                name='impuesto_positivo'
            ),
            models.CheckConstraint(
                check=Q(costo_envio__gte=0),
                name='costo_envio_positivo'
            ),
        ]

    def __str__(self):
        return self.nombre_tienda

    def save(self, *args, **kwargs):
        # Asegurarse de que solo haya una configuración activa
        if self.activo:
            ConfiguracionTienda.objects.exclude(id=self.id).update(activo=False)
        super().save(*args, **kwargs)

    @classmethod
    def obtener_configuracion(cls):
        """Obtiene la configuración activa de la tienda."""
        return cls.objects.filter(activo=True).first()
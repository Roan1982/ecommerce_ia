from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    imagen_url = models.URLField(blank=True, null=True)
    stock = models.IntegerField(default=10)

    @property
    def en_stock(self):
        """Verifica si el producto está disponible en stock"""
        return self.stock > 0

    @property
    def promedio_calificacion(self):
        """Calcula el promedio de calificaciones del producto"""
        resenas = self.resena_set.all()
        if resenas.exists():
            return round(sum(resena.calificacion for resena in resenas) / resenas.count(), 1)
        return 0

    @property
    def total_resenas(self):
        """Devuelve el número total de reseñas"""
        return self.resena_set.count()

    def puede_reseñar(self, usuario):
        """Verifica si un usuario puede reseñar este producto"""
        # El usuario debe haber comprado el producto
        # Verificar en pedidos completados
        from tienda.models import PedidoProducto, CompraProducto

        pedidos_completados = Pedido.objects.filter(
            usuario=usuario,
            estado__in=['pagado', 'enviado', 'entregado']
        ).values_list('id', flat=True)

        productos_pedidos = PedidoProducto.objects.filter(
            pedido_id__in=pedidos_completados,
            producto=self
        ).exists()

        # Verificar en compras directas
        compras_directas = CompraProducto.objects.filter(
            compra__usuario=usuario,
            producto=self
        ).exists()

        return productos_pedidos or compras_directas

class Carrito(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

    @property
    def total_productos(self):
        return sum(item.cantidad for item in self.carritoproducto_set.all())

    @property
    def total_precio(self):
        return sum(item.subtotal for item in self.carritoproducto_set.all())

class CarritoProducto(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)

    class Meta:
        unique_together = ('carrito', 'producto')

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad} en carrito"

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad

class Compra(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Compra de {self.usuario.username} - ${self.total}"

class CompraProducto(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

class DireccionEnvio(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre_direccion = models.CharField(max_length=100, help_text="Ej: Casa, Trabajo, etc.")
    nombre_completo = models.CharField(max_length=200)
    calle = models.CharField(max_length=200)
    numero = models.CharField(max_length=20)
    piso_departamento = models.CharField(max_length=50, blank=True, null=True)
    ciudad = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    telefono = models.CharField(max_length=20)
    es_predeterminada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre_direccion} - {self.nombre_completo}"

    class Meta:
        verbose_name = "Dirección de Envío"
        verbose_name_plural = "Direcciones de Envío"

class MetodoPago(models.Model):
    TIPO_CHOICES = [
        ('tarjeta', 'Tarjeta de Crédito/Débito'),
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='tarjeta')
    nombre_titular = models.CharField(max_length=200, blank=True, null=True)
    numero_tarjeta = models.CharField(max_length=20, blank=True, null=True)  # Solo últimos 4 dígitos
    fecha_vencimiento = models.DateField(blank=True, null=True)
    es_predeterminada = models.BooleanField(default=False)

    def __str__(self):
        if self.tipo == 'tarjeta':
            return f"Tarjeta ****{self.numero_tarjeta[-4:] if self.numero_tarjeta else '****'}"
        return f"{self.get_tipo_display()}"

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"

class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('pagado', 'Pagado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    # Información de envío
    direccion_envio = models.ForeignKey(DireccionEnvio, on_delete=models.SET_NULL, null=True)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Información de pago
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True)
    total_productos = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_cupon = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2)

    # Información adicional
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username} - ${self.total_pedido}"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_creacion']

class PedidoProducto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    class Meta:
        verbose_name = "Producto del Pedido"
        verbose_name_plural = "Productos del Pedido"

class Resena(models.Model):
    CALIFICACION_CHOICES = [
        (1, '1 estrella'),
        (2, '2 estrellas'),
        (3, '3 estrellas'),
        (4, '4 estrellas'),
        (5, '5 estrellas'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    calificacion = models.IntegerField(choices=CALIFICACION_CHOICES)
    comentario = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reseña"
        verbose_name_plural = "Reseñas"
        unique_together = ('usuario', 'producto')  # Un usuario puede reseñar un producto solo una vez
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Reseña de {self.usuario.username} para {self.producto.nombre} - {self.calificacion}★"

    @property
    def estrellas_display(self):
        """Devuelve una representación visual de las estrellas"""
        return '★' * self.calificacion + '☆' * (5 - self.calificacion)


class Cupon(models.Model):
    """Modelo para cupones de descuento"""
    TIPO_DESCUENTO = [
        ('porcentaje', 'Porcentaje'),
        ('monto_fijo', 'Monto Fijo'),
    ]

    codigo = models.CharField(max_length=20, unique=True, help_text="Código único del cupón")
    descripcion = models.CharField(max_length=200, help_text="Descripción del cupón")
    tipo_descuento = models.CharField(max_length=20, choices=TIPO_DESCUENTO, default='porcentaje')
    valor_descuento = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor del descuento")
    fecha_expiracion = models.DateTimeField(help_text="Fecha de expiración del cupón")
    usos_maximos = models.PositiveIntegerField(default=1, help_text="Número máximo de usos")
    usos_actuales = models.PositiveIntegerField(default=0, help_text="Número actual de usos")
    activo = models.BooleanField(default=True, help_text="Si el cupón está activo")
    minimo_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Monto mínimo de compra requerido")

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

    def es_valido(self):
        """Verifica si el cupón es válido"""
        ahora = timezone.now()
        return (
            self.activo and
            self.fecha_expiracion > ahora and
            self.usos_actuales < self.usos_maximos
        )

    def calcular_descuento(self, subtotal):
        """Calcula el descuento aplicable"""
        if subtotal < self.minimo_compra:
            return 0

        if self.tipo_descuento == 'porcentaje':
            return subtotal * (self.valor_descuento / 100)
        else:  # monto_fijo
            return min(self.valor_descuento, subtotal)

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"

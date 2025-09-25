from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Producto(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('agotado', 'Agotado'),
    ]

    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    imagen_url = models.URLField(blank=True, null=True)

    # Campos de inventario mejorados
    stock = models.IntegerField(default=10, help_text="Cantidad actual en inventario")
    stock_minimo = models.IntegerField(default=5, help_text="Stock mínimo para alertas")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Código SKU del producto")
    peso = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Peso en kg para cálculo de envío")
    dimensiones = models.CharField(max_length=50, blank=True, null=True, help_text="Dimensiones (ej: 10x20x5 cm)")

    # Estado del producto
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    fecha_creacion = models.DateTimeField(default=timezone.now, help_text="Fecha de creación del producto")
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} (SKU: {self.sku or 'N/A'})"

    @property
    def en_stock(self):
        """Verifica si el producto está disponible en stock"""
        return self.stock > 0 and self.estado == 'activo'

    @property
    def stock_bajo(self):
        """Verifica si el stock está por debajo del mínimo"""
        return self.stock <= self.stock_minimo and self.stock > 0

    @property
    def agotado(self):
        """Verifica si el producto está agotado"""
        return self.stock == 0 or self.estado == 'agotado'

    def reducir_stock(self, cantidad, usuario=None, pedido=None):
        """Reduce el stock del producto"""
        if cantidad > self.stock:
            raise ValueError(f"No hay suficiente stock. Disponible: {self.stock}, Solicitado: {cantidad}")
        self.stock -= cantidad
        self.save()
        # Crear registro de movimiento de inventario
        descripcion = f"Venta - Reducción de stock por pedido #{pedido.id}" if pedido else "Venta - Reducción de stock por pedido"
        MovimientoInventario.objects.create(
            producto=self,
            tipo='salida',
            cantidad=-cantidad,  # Negativo para indicar salida
            descripcion=descripcion,
            usuario=usuario
        )

    def aumentar_stock(self, cantidad, usuario=None, pedido=None):
        """Aumenta el stock del producto"""
        self.stock += cantidad
        self.save()
        # Crear registro de movimiento de inventario
        descripcion = f"Devolución - Aumento de stock por pedido #{pedido.id}" if pedido else "Ajuste - Aumento de stock"
        MovimientoInventario.objects.create(
            producto=self,
            tipo='entrada',
            cantidad=cantidad,  # Positivo para indicar entrada
            descripcion=descripcion,
            usuario=usuario
        )

    def aumentar_stock(self, cantidad, descripcion="Ajuste manual"):
        """Aumenta el stock del producto"""
        self.stock += cantidad
        self.save()
        # Crear registro de movimiento de inventario
        MovimientoInventario.objects.create(
            producto=self,
            tipo='entrada',
            cantidad=cantidad,
            descripcion=descripcion
        )

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

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-fecha_creacion']


class MovimientoInventario(models.Model):
    """Modelo para tracking de movimientos de inventario"""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.IntegerField(help_text="Cantidad del movimiento")
    descripcion = models.CharField(max_length=200, help_text="Descripción del movimiento")
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               help_text="Usuario que realizó el movimiento")

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} - {self.cantidad} unidades"

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ['-fecha']

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

class ConfiguracionSistema(models.Model):
    """Modelo para configuraciones del sistema"""
    # Configuración general
    sitio_activo = models.BooleanField(default=True, help_text="Si el sitio web está activo")
    registro_abierto = models.BooleanField(default=True, help_text="Permitir registro de nuevos usuarios")
    moneda = models.CharField(max_length=3, default='COP', help_text="Moneda predeterminada (COP, USD, EUR)")

    # Configuración de comercio
    envio_gratuito_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=50000,
                                               help_text="Monto mínimo para envío gratuito")
    stock_minimo_alerta = models.PositiveIntegerField(default=5, help_text="Stock mínimo para mostrar alerta")
    productos_por_pagina = models.PositiveIntegerField(default=12, help_text="Productos por página en catálogo")
    impuestos_activos = models.BooleanField(default=True, help_text="Calcular y mostrar impuestos")

    # Configuración de email
    email_notificaciones = models.BooleanField(default=True, help_text="Enviar notificaciones por email")
    email_admin = models.EmailField(blank=True, help_text="Email del administrador")
    email_smtp = models.CharField(max_length=100, blank=True, help_text="Servidor SMTP")
    email_puerto = models.PositiveIntegerField(default=587, help_text="Puerto SMTP")
    email_usuario = models.CharField(max_length=100, blank=True, help_text="Usuario SMTP")
    email_password = models.CharField(max_length=200, blank=True, help_text="Contraseña SMTP")

    # Configuración de seguridad
    session_timeout = models.PositiveIntegerField(default=60, help_text="Tiempo de sesión en minutos")
    max_login_attempts = models.PositiveIntegerField(default=5, help_text="Máximo intentos de login")
    two_factor_auth = models.BooleanField(default=False, help_text="Autenticación de dos factores para admin")
    password_complexity = models.BooleanField(default=True, help_text="Requerir contraseñas complejas")

    # Configuración de backup
    backup_automatico = models.BooleanField(default=True, help_text="Realizar backups automáticos")
    backup_frecuencia = models.CharField(max_length=20, default='diario',
                                        choices=[('diario', 'Diario'), ('semanal', 'Semanal'), ('mensual', 'Mensual')])
    backup_retencion = models.PositiveIntegerField(default=30, help_text="Días para retener backups")

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuración del Sistema - Actualizada: {self.fecha_actualizacion}"

    @classmethod
    def get_configuracion(cls):
        """Obtiene la configuración actual del sistema, crea una si no existe"""
        config, created = cls.objects.get_or_create(id=1, defaults={})
        return config

    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuración del Sistema"

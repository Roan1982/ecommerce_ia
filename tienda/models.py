from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
import os

class Producto(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('agotado', 'Agotado'),
    ]

    nombre = models.CharField(max_length=100, default='Producto sin nombre')
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    categoria = models.CharField(max_length=50, default='Sin categoría')
    descripcion = models.TextField(blank=True, null=True)

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
    def imagen_principal(self):
        """Devuelve la URL de la imagen principal del producto"""
        imagen_principal = self.imagenes.filter(es_principal=True).first()
        if imagen_principal:
            return imagen_principal.url_imagen
        # Si no hay imagen principal, devolver la primera imagen disponible
        primera_imagen = self.imagenes.first()
        if primera_imagen:
            return primera_imagen.url_imagen
        return None

    @property
    def tiene_imagen(self):
        """Verifica si el producto tiene alguna imagen"""
        return self.imagenes.exists()

    @property
    def imagenes_disponibles(self):
        """Devuelve todas las imágenes del producto ordenadas por principal primero"""
        return self.imagenes.order_by('-es_principal', 'orden')

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

    @property
    def total_resenas(self):
        """Devuelve el total de reseñas del producto"""
        return self.resena_set.count()

    @property
    def promedio_calificacion(self):
        """Devuelve el promedio de calificaciones del producto"""
        from django.db.models import Avg
        avg_rating = self.resena_set.aggregate(avg=Avg('calificacion'))['avg']
        return round(avg_rating, 1) if avg_rating else 0.0

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-fecha_creacion']


class ProductoImagen(models.Model):
    """Modelo para almacenar múltiples imágenes de productos como blobs"""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes',
                                help_text="Producto al que pertenece la imagen")
    imagen_blob = models.BinaryField(help_text="Imagen almacenada como blob en la base de datos")
    imagen_nombre = models.CharField(max_length=255, help_text="Nombre original del archivo de imagen")
    imagen_tipo_mime = models.CharField(max_length=100, help_text="Tipo MIME de la imagen (ej: image/jpeg)")
    es_principal = models.BooleanField(default=False, help_text="Si esta es la imagen principal del producto")
    orden = models.PositiveIntegerField(default=0, help_text="Orden de visualización de la imagen")
    fecha_subida = models.DateTimeField(default=timezone.now, help_text="Fecha de subida de la imagen")
    descripcion = models.CharField(max_length=200, blank=True, null=True,
                                  help_text="Descripción opcional de la imagen")

    class Meta:
        verbose_name = "Imagen de Producto"
        verbose_name_plural = "Imágenes de Productos"
        ordering = ['orden', 'fecha_subida']
        unique_together = ['producto', 'orden']  # Evitar órdenes duplicados por producto

    def __str__(self):
        return f"Imagen de {self.producto.nombre} - {self.imagen_nombre}"

    @property
    def url_imagen(self):
        """Devuelve la URL para acceder a esta imagen"""
        return f"/producto/{self.producto.id}/imagen/{self.id}/"

    def save(self, *args, **kwargs):
        # Si esta imagen es principal, quitar el flag principal de otras imágenes del mismo producto
        if self.es_principal:
            ProductoImagen.objects.filter(
                producto=self.producto,
                es_principal=True
            ).exclude(pk=self.pk).update(es_principal=False)
        super().save(*args, **kwargs)


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

    @property
    def esta_completa(self):
        """Verifica si la dirección de envío está completa para poder enviar pedidos"""
        campos_requeridos = [
            self.nombre_direccion,
            self.nombre_completo,
            self.calle,
            self.numero,
            self.ciudad,
            self.provincia,
            self.codigo_postal,
            self.telefono,
        ]
        return all(campos_requeridos) and all(str(campo).strip() for campo in campos_requeridos)

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
        ('procesando', 'Procesando'),
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

    def calcular_totales(self):
        """Calcula los totales del pedido incluyendo descuentos de cupones"""
        # Calcular total de productos
        self.total_productos = sum(producto.subtotal for producto in self.pedidoproducto_set.all())

        # Calcular descuento total de cupones aplicados
        self.descuento_cupon = sum(cupon.descuento_aplicado for cupon in self.cupones_aplicadas.all())

        # Calcular total final
        self.total_pedido = self.total_productos - self.descuento_cupon + (self.costo_envio or 0)

        # Asegurar que el total no sea negativo
        self.total_pedido = max(self.total_pedido, 0)

    def aplicar_cupon(self, cupon, subtotal=None):
        """Aplica un cupón al pedido"""
        from django.core.exceptions import ValidationError

        # Verificar que el cupón sea válido para este usuario
        if not cupon.es_valido(self.usuario):
            raise ValidationError("El cupón no es válido para este usuario")

        # Verificar que el cupón no haya sido aplicado ya a este pedido
        if self.cupones_aplicadas.filter(cupon=cupon).exists():
            raise ValidationError("Este cupón ya ha sido aplicado a este pedido")

        # Calcular el subtotal (productos + envío - descuentos anteriores)
        if subtotal is None:
            subtotal_actual = self.total_productos + (self.costo_envio or 0) - self.descuento_cupon
        else:
            subtotal_actual = subtotal

        # Verificar monto mínimo de compra
        if subtotal_actual < cupon.minimo_compra:
            raise ValidationError(f"El monto mínimo de compra para este cupón es ${cupon.minimo_compra}")

        # Calcular descuento
        descuento = cupon.calcular_descuento(subtotal_actual)

        if descuento <= 0:
            raise ValidationError("El cupón no aplica descuento a este pedido")

        # Crear relación pedido-cupón
        PedidoCupon.objects.create(
            pedido=self,
            cupon=cupon,
            descuento_aplicado=descuento
        )

        # Marcar cupón como usado
        cupon.marcar_como_usado(self.usuario)

        # Recalcular totales
        self.calcular_totales()
        self.save()

        return descuento

    def remover_cupon(self, cupon):
        """Remueve un cupón aplicado al pedido"""
        pedido_cupon = self.cupones_aplicadas.filter(cupon=cupon).first()
        if pedido_cupon:
            # Eliminar la relación
            pedido_cupon.delete()

            # Recalcular totales
            self.calcular_totales()
            self.save()

            return True
        return False

    @property
    def cupones_aplicados_count(self):
        """Devuelve el número de cupones aplicados"""
        return self.cupones_aplicadas.count()

    @property
    def puede_ser_enviado(self):
        """Verifica si el pedido puede ser enviado (tiene dirección completa)"""
        return self.direccion_envio and self.direccion_envio.esta_completa

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

    TIPO_CUPON = [
        ('normal', 'Cupón Normal'),
        ('codigo_copiable', 'Código Copiable'),
        ('comprado_puntos', 'Comprado con Puntos'),
        ('canjeado_puntos', 'Canjeado por Puntos'),
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

    # Nuevos campos para el sistema avanzado de cupones
    tipo_cupon = models.CharField(max_length=20, choices=TIPO_CUPON, default='normal',
                                  help_text="Tipo de cupón")
    puntos_requeridos = models.PositiveIntegerField(default=0,
                                                   help_text="Puntos requeridos para comprar este cupón")
    usuario_propietario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                           related_name='cupones_propios',
                                           help_text="Usuario propietario (para cupones personales)")
    usado_por_usuario = models.BooleanField(default=False,
                                           help_text="Si este cupón ya fue usado por su propietario")

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

    def es_valido(self, usuario=None):
        """Verifica si el cupón es válido para un usuario específico"""
        ahora = timezone.now()

        # Validaciones básicas
        if not self.activo or self.fecha_expiracion <= ahora or self.usos_actuales >= self.usos_maximos:
            return False

        # Validaciones específicas por tipo de cupón
        if self.tipo_cupon == 'codigo_copiable':
            # Los cupones copiables solo pueden usarse una vez por usuario
            if usuario and hasattr(self, 'pedidos_usados') and self.pedidos_usados.filter(pedido__usuario=usuario).exists():
                return False
        elif self.tipo_cupon == 'comprado_puntos':
            # Los cupones comprados con puntos no se pueden copiar
            return False
        elif self.tipo_cupon == 'canjeado_puntos':
            # Los cupones canjeados por puntos son personales
            if not usuario or self.usuario_propietario != usuario:
                return False
            if self.usado_por_usuario:
                return False

        return True

    def puede_copiar_codigo(self, usuario=None):
        """Verifica si el código del cupón puede ser copiado"""
        if self.tipo_cupon == 'comprado_puntos':
            return False
        if self.tipo_cupon == 'canjeado_puntos' and self.usuario_propietario != usuario:
            return False
        return True

    def calcular_descuento(self, subtotal):
        """Calcula el descuento aplicable"""
        if subtotal < self.minimo_compra:
            return 0

        if self.tipo_descuento == 'porcentaje':
            return subtotal * (self.valor_descuento / 100)
        else:  # monto_fijo
            return min(self.valor_descuento, subtotal)

    def marcar_como_usado(self, usuario=None):
        """Marca el cupón como usado por un usuario específico"""
        self.usos_actuales += 1

        if self.tipo_cupon == 'canjeado_puntos' and usuario == self.usuario_propietario:
            self.usado_por_usuario = True

        self.save()

    def puede_canjear_por_puntos(self, usuario):
        """Verifica si este cupón puede ser canjeado por puntos de fidelidad"""
        return (
            self.tipo_cupon == 'codigo_copiable' and
            self.usuario_propietario == usuario and
            hasattr(self, 'pedidos_usados') and
            self.pedidos_usados.filter(pedido__usuario=usuario).exists()
        )

    def canjear_por_puntos(self, usuario):
        """Canjea el cupón usado por puntos de fidelidad"""
        if not self.puede_canjear_por_puntos(usuario):
            raise ValueError("Este cupón no puede ser canjeado por puntos")

        # Calcular puntos a otorgar (valor del descuento / 10, por ejemplo)
        puntos_a_otorgar = int(self.calcular_descuento(1000) / 10)  # Base en descuento de $1000

        # Otorgar puntos al usuario
        profile = usuario.profile
        profile.agregar_puntos(puntos_a_otorgar, f"Canje de cupón usado: {self.codigo}")

        # Desactivar el cupón
        self.activo = False
        self.save()

        return puntos_a_otorgar

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"

class PedidoCupon(models.Model):
    """Modelo para relacionar pedidos con cupones aplicados (permite múltiples cupones por pedido)"""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='cupones_aplicados')
    cupon = models.ForeignKey(Cupon, on_delete=models.CASCADE, related_name='pedidos_usados')
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, help_text="Descuento aplicado por este cupón")
    fecha_aplicacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Pedido {self.pedido.id} - Cupón {self.cupon.codigo}"

    class Meta:
        verbose_name = "Cupón del Pedido"
        verbose_name_plural = "Cupones del Pedido"
        unique_together = ('pedido', 'cupon')  # Un cupón no puede aplicarse dos veces al mismo pedido

class ConfiguracionSistema(models.Model):
    """Modelo para configuraciones del sistema"""
    # Configuración general
    sitio_activo = models.BooleanField(default=True, help_text="Si el sitio web está activo")
    registro_abierto = models.BooleanField(default=True, help_text="Permitir registro de nuevos usuarios")
    moneda = models.CharField(max_length=3, default='ARS', help_text="Moneda predeterminada (ARS, COP, USD, EUR)")

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


class Profile(models.Model):
    """Modelo para perfil de usuario extendido"""
    NIVEL_CHOICES = [
        ('bronce', 'Bronce'),
        ('plata', 'Plata'),
        ('oro', 'Oro'),
        ('platino', 'Platino'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telefono = models.CharField(max_length=20, blank=True, null=True, help_text="Número de teléfono")
    fecha_nacimiento = models.DateField(blank=True, null=True, help_text="Fecha de nacimiento")
    genero = models.CharField(max_length=10, choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], blank=True, null=True)
    biografia = models.TextField(blank=True, null=True, help_text="Biografía del usuario")

    # Sistema de puntos de fidelidad
    puntos_totales = models.PositiveIntegerField(default=0, help_text="Puntos totales acumulados")
    puntos_disponibles = models.PositiveIntegerField(default=0, help_text="Puntos disponibles para canjear")
    nivel_membresia = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='bronce', help_text="Nivel de membresía")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

    @property
    def puntos_para_siguiente_nivel(self):
        """Calcula los puntos necesarios para el siguiente nivel"""
        niveles_puntos = {
            'bronce': 0,
            'plata': 500,
            'oro': 1500,
            'platino': 3000,
        }
        siguiente_nivel = self.get_siguiente_nivel()
        return niveles_puntos.get(siguiente_nivel, 0) - self.puntos_totales

    def get_siguiente_nivel(self):
        """Obtiene el siguiente nivel disponible"""
        niveles = ['bronce', 'plata', 'oro', 'platino']
        current_index = niveles.index(self.nivel_membresia)
        if current_index < len(niveles) - 1:
            return niveles[current_index + 1]
        return self.nivel_membresia

    def actualizar_nivel(self):
        """Actualiza el nivel de membresía basado en puntos totales"""
        puntos = self.puntos_totales
        if puntos >= 3000:
            self.nivel_membresia = 'platino'
        elif puntos >= 1500:
            self.nivel_membresia = 'oro'
        elif puntos >= 500:
            self.nivel_membresia = 'plata'
        else:
            self.nivel_membresia = 'bronce'
        self.save()

    def agregar_puntos(self, puntos, descripcion="Compra realizada"):
        """Agrega puntos al usuario y actualiza nivel"""
        self.puntos_totales += puntos
        self.puntos_disponibles += puntos
        self.actualizar_nivel()

        # Crear registro en historial
        HistorialPuntos.objects.create(
            usuario=self.usuario,
            tipo='ganados',
            puntos=puntos,
            descripcion=descripcion
        )

        self.save()

    def canjear_puntos(self, puntos, descripcion="Canje de puntos"):
        """Canjea puntos disponibles"""
        if puntos > self.puntos_disponibles:
            raise ValueError("No tienes suficientes puntos disponibles")

        self.puntos_disponibles -= puntos

        # Crear registro en historial
        HistorialPuntos.objects.create(
            usuario=self.usuario,
            tipo='canjeados',
            puntos=-puntos,  # Negativo para indicar canje
            descripcion=descripcion
        )

        self.save()

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"


class HistorialPuntos(models.Model):
    """Modelo para el historial de puntos de fidelidad"""
    TIPO_CHOICES = [
        ('ganados', 'Puntos Ganados'),
        ('canjeados', 'Puntos Canjeados'),
        ('expirados', 'Puntos Expirados'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_puntos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    puntos = models.IntegerField(help_text="Cantidad de puntos (positivo para ganados, negativo para canjeados)")
    descripcion = models.CharField(max_length=200, help_text="Descripción de la transacción")
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Historial de Puntos"
        verbose_name_plural = "Historial de Puntos"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()} - {self.puntos} puntos"


class Wishlist(models.Model):
    """Modelo para lista de deseos de usuarios"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='wishlist_users')
    fecha_agregado = models.DateTimeField(default=timezone.now)

    # Configuración de contribuciones grupales
    permitir_contribuciones = models.BooleanField(default=False,
                                                help_text="Permitir que otros usuarios contribuyan al pago")
    contribucion_objetivo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=False,
        default=0,
        help_text="Monto objetivo para contribuciones grupales"
    )
    contribucion_privada = models.BooleanField(default=False,
                                             help_text="Las contribuciones son privadas (solo visible para el propietario)")
    descripcion_contribucion = models.TextField(blank=True, null=True,
                                              help_text="Descripción opcional de la contribución grupal")
    fecha_modificacion = models.DateTimeField(auto_now=True,
                                            help_text="Fecha de última modificación de la configuración de contribuciones")

    # Sistema de referidos y compartir
    compartir_activo = models.BooleanField(default=True,
                                         help_text="Permitir compartir esta wishlist en redes sociales")
    codigo_referido = models.CharField(max_length=20, unique=True, blank=True, null=True,
                                     help_text="Código único para tracking de referidos")
    veces_compartido = models.PositiveIntegerField(default=0,
                                                 help_text="Número de veces que se ha compartido")
    veces_visitado_via_referido = models.PositiveIntegerField(default=0,
                                                            help_text="Número de visitas vía enlaces de referido")
    veces_contribuido_via_referido = models.PositiveIntegerField(default=0,
                                                               help_text="Número de contribuciones vía referidos")

    class Meta:
        verbose_name = "Lista de Deseos"
        verbose_name_plural = "Listas de Deseos"
        unique_together = ['usuario', 'producto']  # Un usuario no puede tener el mismo producto dos veces
        ordering = ['-fecha_agregado']

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre}"

    def save(self, *args, **kwargs):
        # Validar el modelo antes de guardar
        from django.core.exceptions import ValidationError
        try:
            self.full_clean()
        except ValidationError:
            # Re-lanzar para que admin/forms vean el error
            raise

        # Generar código de referido único si no existe
        if not self.codigo_referido:
            import secrets
            import string
            # Generar código alfanumérico único
            while True:
                codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not Wishlist.objects.filter(codigo_referido=codigo).exists():
                    self.codigo_referido = codigo
                    break

        super().save(*args, **kwargs)

    def clean(self):
        """Validación del modelo: si permitir contribuciones, la meta debe ser > 0"""
        from django.core.exceptions import ValidationError

        if self.permitir_contribuciones:
            # contribucion_objetivo puede ser Decimal o número; aceptamos > 0
            if not self.contribucion_objetivo or self.contribucion_objetivo <= 0:
                raise ValidationError({'contribucion_objetivo': 'La meta debe ser mayor a 0 cuando las contribuciones están activas.'})

    @property
    def total_contribuido(self):
        """Calcula el total contribuido por todos los usuarios"""
        return self.contribuciones.filter(estado='completado').aggregate(
            total=Sum('monto')
        )['total'] or 0

    @property
    def progreso_contribucion(self):
        """Calcula el progreso de contribución (0-100)"""
        if not self.permitir_contribuciones or not self.contribucion_objetivo:
            return 0
        return min(100, (self.total_contribuido / self.contribucion_objetivo) * 100)

    @property
    def objetivo_alcanzado(self):
        """Verifica si se alcanzó el objetivo de contribución"""
        if not self.permitir_contribuciones or not self.contribucion_objetivo:
            return False
        return self.total_contribuido >= self.contribucion_objetivo

    @property
    def monto_restante(self):
        """Calcula el monto restante para alcanzar el objetivo"""
        if not self.permitir_contribuciones or not self.contribucion_objetivo:
            return 0
        return max(0, self.contribucion_objetivo - self.total_contribuido)

    def puede_contribuir(self, usuario):
        """Verifica si un usuario puede contribuir a este item"""
        if not self.permitir_contribuciones:
            return False
        if usuario == self.usuario:
            return False  # El propietario no puede contribuir a su propio item
        return True

    def agregar_contribucion(self, usuario, monto, mensaje="", referido_por=None):
        """Agrega una contribución a este item de wishlist"""
        if not self.puede_contribuir(usuario):
            raise ValueError("No puedes contribuir a este item")

        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")

        # Crear la contribución
        contribucion = ContribucionWishlist.objects.create(
            wishlist_item=self,
            usuario_contribuyente=usuario,
            monto=monto,
            mensaje=mensaje,
            estado='completado'  # Por simplicidad, asumimos que el pago se completa inmediatamente
        )

        # Si vino por referido, registrar el referido
        if referido_por:
            ReferidoWishlist.objects.create(
                wishlist=self,
                usuario_referido=usuario,
                usuario_referidor=referido_por,
                contribucion=contribucion,
                plataforma_origen='enlace_compartido'
            )
            # Incrementar contador de contribuciones vía referido
            self.veces_contribuido_via_referido += 1
            self.save()

        # Verificar si se alcanzó el objetivo
        if self.objetivo_alcanzado:
            self.convertir_a_pedido()

        return contribucion

    def registrar_visita_referido(self, usuario_referidor=None):
        """Registra una visita vía enlace de referido"""
        self.veces_visitado_via_referido += 1
        self.save()

        # Si hay usuario referidor, registrar en el tracking
        if usuario_referidor:
            ReferidoWishlist.objects.create(
                wishlist=self,
                usuario_referidor=usuario_referidor,
                plataforma_origen='enlace_compartido'
            )

    def registrar_compartir(self, plataforma):
        """Registra que se compartió en una plataforma"""
        self.veces_compartido += 1
        self.save()

        # Registrar en el historial de compartidos
        HistorialCompartir.objects.create(
            wishlist=self,
            usuario=self.usuario,  # El propietario es quien comparte
            plataforma=plataforma
        )

    @property
    def url_compartir(self):
        """Genera la URL para compartir esta wishlist"""
        from django.urls import reverse
        base_url = reverse('wishlist_detalle_contribucion', kwargs={'wishlist_id': self.id})
        return f"{base_url}?ref={self.codigo_referido}"

    def generar_enlaces_compartir(self):
        """Genera enlaces para compartir en diferentes plataformas"""
        import urllib.parse
        base_url = f"http://127.0.0.1:8000{self.url_compartir}"

        titulo = f"¡Ayúdame a conseguir {self.producto.nombre}!"
        descripcion = f"Necesito ayuda para comprar {self.producto.nombre}. ¿Me ayudas con una contribución?"

        if self.descripcion_contribucion:
            descripcion = self.descripcion_contribucion

        texto_compartir = f"{titulo}\n{descripcion}\n\n{base_url}"

        return {
            'whatsapp': f"https://wa.me/?text={urllib.parse.quote(texto_compartir)}",
            'telegram': f"https://t.me/share/url?url={urllib.parse.quote(base_url)}&text={urllib.parse.quote(titulo + ' - ' + descripcion)}",
            'twitter': f"https://twitter.com/intent/tweet?text={urllib.parse.quote(titulo)}&url={urllib.parse.quote(base_url)}",
            'facebook': f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(base_url)}",
            'instagram': f"https://www.instagram.com/",  # Instagram no permite compartir URLs directas
            'tiktok': f"https://www.tiktok.com/",  # TikTok tampoco permite compartir URLs directas
            'copiar': base_url
        }

    def convertir_a_pedido(self):
        """Convierte el item de wishlist en un pedido cuando se alcanza el objetivo"""
        from .models import Pedido, PedidoProducto, DireccionEnvio

        # Crear pedido para el usuario propietario
        pedido = Pedido.objects.create(
            usuario=self.usuario,
            estado='pagado',  # El pedido ya está "pagado" por las contribuciones
            total_productos=self.producto.precio,
            descuento_cupon=0,
            total_pedido=self.producto.precio,
            notas=f"Pedido generado por contribuciones grupales. Contribuyeron: {self.contribuciones.count()} personas."
        )

        # Agregar el producto al pedido
        PedidoProducto.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=self.producto.precio
        )

        # Reducir stock del producto
        self.producto.reducir_stock(1)

        # Marcar contribuciones como procesadas
        self.contribuciones.filter(estado='completado').update(estado='procesado', pedido_generado=pedido)

        # Eliminar el item de wishlist
        self.delete()

        # Enviar notificaciones
        self.enviar_notificaciones_pedido_generado(pedido)

        return pedido

    def enviar_notificaciones_pedido_generado(self, pedido):
        """Envía notificaciones cuando se genera el pedido"""
        from .services.email_service import EmailService

        # Notificar al propietario
        email_service = EmailService()
        contexto_propietario = {
            'usuario': self.usuario,
            'producto': self.producto,
            'pedido': pedido,
            'contribuciones': self.contribuciones.filter(estado='procesado'),
            'total_contribuciones': self.contribuciones.filter(estado='procesado').count()
        }

        try:
            email_service.enviar_email(
                tipo='wishlist_contribucion_completada',
                usuario=self.usuario,
                contexto=contexto_propietario
            )
        except Exception as e:
            print(f"Error enviando email al propietario: {e}")

        # Notificar a los contribuyentes
        for contribucion in self.contribuciones.filter(estado='procesado'):
            contexto_contribuyente = {
                'contribuyente': contribucion.usuario_contribuyente,
                'producto': self.producto,
                'propietario': self.usuario,
                'monto_contribuido': contribucion.monto,
                'pedido': pedido
            }

            try:
                email_service.enviar_email(
                    tipo='wishlist_contribucion_gracias',
                    usuario=contribucion.usuario_contribuyente,
                    contexto=contexto_contribuyente
                )
            except Exception as e:
                print(f"Error enviando email al contribuyente {contribucion.usuario_contribuyente.email}: {e}")


class ContribucionWishlist(models.Model):
    """Modelo para contribuciones a items de wishlist"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('completado', 'Pago Completado'),
        ('procesado', 'Procesado en Pedido'),
        ('cancelado', 'Cancelado'),
        ('reembolsado', 'Reembolsado'),
    ]

    wishlist_item = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='contribuciones')
    usuario_contribuyente = models.ForeignKey(User, on_delete=models.CASCADE,
                                            related_name='contribuciones_realizadas')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    mensaje = models.TextField(blank=True, null=True,
                              help_text="Mensaje opcional del contribuyente")
    fecha_contribucion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    # Relación con pedido generado (opcional)
    pedido_generado = models.ForeignKey('Pedido', on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name='contribuciones')

    # Información de pago (para futuras expansiones)
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Contribución Wishlist"
        verbose_name_plural = "Contribuciones Wishlist"
        ordering = ['-fecha_contribucion']

    def __str__(self):
        return f"{self.usuario_contribuyente.username} contribuyó ${self.monto} a {self.wishlist_item}"

    @property
    def es_anonima(self):
        """Verifica si la contribución debe mostrarse como anónima"""
        return self.wishlist_item.contribucion_privada

    def cancelar_contribucion(self):
        """Cancela la contribución (para reembolsos)"""
        if self.estado == 'completado':
            self.estado = 'cancelado'
            self.save()
            # Aquí iría la lógica de reembolso

    def procesar_reembolso(self):
        """Procesa el reembolso de la contribución"""
        if self.estado == 'cancelado':
            self.estado = 'reembolsado'
            self.save()
            # Aquí iría la lógica real de reembolso


class ComparacionProductos(models.Model):
    """Modelo para comparación de productos"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='comparacion')
    productos = models.ManyToManyField(Producto, related_name='comparaciones', blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comparación de Productos"
        verbose_name_plural = "Comparaciones de Productos"

    def __str__(self):
        return f"Comparación de {self.usuario.username} ({self.productos.count()} productos)"

    @property
    def puede_agregar_mas(self):
        """Verifica si se pueden agregar más productos (máximo 4)"""
        return self.productos.count() < 4

    @property
    def productos_ordenados(self):
        """Devuelve los productos ordenados por nombre"""
        return self.productos.all().order_by('nombre')

    def agregar_producto(self, producto):
        """Agrega un producto a la comparación"""
        if self.productos.count() >= 4:
            raise ValueError("No se pueden comparar más de 4 productos")
        if self.productos.filter(id=producto.id).exists():
            raise ValueError("El producto ya está en la comparación")
        self.productos.add(producto)

    def quitar_producto(self, producto):
        """Quita un producto de la comparación"""
        self.productos.remove(producto)

    def limpiar(self):
        """Limpia todos los productos de la comparación"""
        self.productos.clear()


# ===== SISTEMA DE NEWSLETTER/SUSCRIPCIÓN =====

class NewsletterSubscription(models.Model):
    """Modelo para suscripciones al newsletter"""
    FRECUENCIA_CHOICES = [
        ('diaria', 'Diaria'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    ]

    email = models.EmailField(unique=True, help_text="Email del suscriptor")
    nombre = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre opcional del suscriptor")
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='semanal',
                                  help_text="Frecuencia de envío del newsletter")
    activo = models.BooleanField(default=True, help_text="Si la suscripción está activa")
    fecha_suscripcion = models.DateTimeField(default=timezone.now, help_text="Fecha de suscripción")
    fecha_ultimo_envio = models.DateTimeField(blank=True, null=True, help_text="Fecha del último envío")
    token_confirmacion = models.CharField(max_length=64, unique=True, blank=True, null=True,
                                          help_text="Token para confirmar suscripción")
    confirmado = models.BooleanField(default=False, help_text="Si la suscripción ha sido confirmada")

    # Preferencias de contenido
    recibir_ofertas = models.BooleanField(default=True, help_text="Recibir ofertas y promociones")
    recibir_novedades = models.BooleanField(default=True, help_text="Recibir novedades de productos")
    recibir_recomendaciones = models.BooleanField(default=True, help_text="Recibir recomendaciones personalizadas")

    class Meta:
        verbose_name = "Suscripción Newsletter"
        verbose_name_plural = "Suscripciones Newsletter"
        ordering = ['-fecha_suscripcion']

    def __str__(self):
        return f"{self.email} ({'Confirmado' if self.confirmado else 'Pendiente'})"

    def generar_token_confirmacion(self):
        """Genera un token único para confirmar la suscripción"""
        import secrets
        self.token_confirmacion = secrets.token_hex(32)
        self.save()

    def confirmar_suscripcion(self):
        """Confirma la suscripción usando el token"""
        self.confirmado = True
        self.token_confirmacion = None
        self.save()

    def cancelar_suscripcion(self):
        """Cancela la suscripción"""
        self.activo = False
        self.save()

    @property
    def puede_recibir_newsletter(self):
        """Verifica si puede recibir newsletters"""
        return self.activo and self.confirmado


class NewsletterCampaign(models.Model):
    """Modelo para campañas de newsletter"""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('programado', 'Programado'),
        ('enviando', 'Enviando'),
        ('enviado', 'Enviado'),
        ('cancelado', 'Cancelado'),
    ]

    titulo = models.CharField(max_length=200, help_text="Título de la campaña")
    asunto = models.CharField(max_length=200, help_text="Asunto del email")
    contenido_html = models.TextField(help_text="Contenido HTML del newsletter")
    contenido_texto = models.TextField(blank=True, null=True, help_text="Versión texto plano")

    # Configuración de envío
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_programada = models.DateTimeField(blank=True, null=True, help_text="Fecha de envío programado")
    fecha_envio = models.DateTimeField(blank=True, null=True, help_text="Fecha real de envío")

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')

    # Estadísticas
    total_suscriptores = models.IntegerField(default=0, help_text="Total de suscriptores objetivo")
    enviados = models.IntegerField(default=0, help_text="Emails enviados")
    abiertos = models.IntegerField(default=0, help_text="Emails abiertos")
    clics = models.IntegerField(default=0, help_text="Clics en enlaces")

    # Filtros de segmentación
    frecuencia_target = models.CharField(max_length=20, blank=True, null=True,
                                         help_text="Frecuencia específica (opcional)")
    solo_confirmados = models.BooleanField(default=True, help_text="Solo suscriptores confirmados")

    # Configuración de tracking
    tracking_aperturas = models.BooleanField(default=True, help_text="Habilitar tracking de aperturas")
    tracking_clics = models.BooleanField(default=True, help_text="Habilitar tracking de clics")

    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = "Campaña Newsletter"
        verbose_name_plural = "Campañas Newsletter"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} ({self.get_estado_display()})"

    @property
    def tasa_apertura(self):
        """Calcula la tasa de apertura"""
        if self.enviados == 0:
            return 0
        return round((self.abiertos / self.enviados) * 100, 2)

    @property
    def tasa_clic(self):
        """Calcula la tasa de clic"""
        if self.enviados == 0:
            return 0
        return round((self.clics / self.enviados) * 100, 2)

    def obtener_suscriptores_target(self):
        """Obtiene la lista de suscriptores objetivo para esta campaña"""
        queryset = NewsletterSubscription.objects.filter(activo=True)

        if self.solo_confirmados:
            queryset = queryset.filter(confirmado=True)

        if self.frecuencia_target:
            queryset = queryset.filter(frecuencia=self.frecuencia_target)

        return queryset

    def programar_envio(self, fecha):
        """Programa el envío de la campaña"""
        self.fecha_programada = fecha
        self.estado = 'programado'
        self.save()

    def iniciar_envio(self):
        """Inicia el proceso de envío"""
        self.estado = 'enviando'
        self.fecha_envio = timezone.now()
        self.total_suscriptores = self.obtener_suscriptores_target().count()
        self.save()

    def completar_envio(self):
        """Completa el envío de la campaña"""
        self.estado = 'enviado'
        self.save()

    def send_campaign(self):
        """
        Envía la campaña de newsletter a todos los suscriptores objetivo.
        Maneja el proceso completo de envío, incluyendo tracking y estadísticas.
        """
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from .views import generar_unsubscribe_url  # Importar función auxiliar

        # Verificar que la campaña esté en estado válido para envío
        if self.estado not in ['borrador', 'programado']:
            raise ValueError("La campaña debe estar en estado 'borrador' o 'programado' para poder enviarse")

        # Iniciar el envío
        self.iniciar_envio()

        # Obtener suscriptores objetivo
        suscriptores = self.obtener_suscriptores_target()
        emails_enviados = 0
        emails_fallidos = 0

        for suscriptor in suscriptores:
            try:
                # Generar URLs de tracking
                unsubscribe_url = generar_unsubscribe_url(suscriptor.email)

                # Preparar contexto para el template
                context = {
                    'campana': self,
                    'suscriptor': suscriptor,
                    'unsubscribe_url': unsubscribe_url,
                    'es_prueba': False,
                }

                # Renderizar contenido
                html_content = render_to_string('tienda/emails/newsletter_template.html', context)
                text_content = strip_tags(html_content)

                # Crear log de envío para tracking
                log_envio = NewsletterLog.objects.create(
                    campaign=self,
                    suscriptor=suscriptor,
                    tipo='envio'
                )

                # Agregar pixel de tracking de apertura si está habilitado
                if hasattr(self, 'tracking_aperturas') and self.tracking_aperturas:
                    from django.conf import settings
                    tracking_pixel = f'<img src="{settings.SITE_URL}/newsletter/tracking/open/{log_envio.id}/" width="1" height="1" style="display:none;" alt="" />'
                    html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')

                # Crear y enviar email
                email_msg = EmailMultiAlternatives(
                    subject=self.asunto,
                    body=text_content,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tu-sitio.com'),
                    to=[suscriptor.email]
                )
                email_msg.attach_alternative(html_content, "text/html")

                # Enviar email
                email_msg.send()

                emails_enviados += 1

                # Actualizar contador en campaña
                self.enviados += 1
                self.save()

            except Exception as e:
                print(f"Error enviando newsletter a {suscriptor.email}: {e}")
                emails_fallidos += 1

                # Registrar error en log
                NewsletterLog.objects.create(
                    campaign=self,
                    suscriptor=suscriptor,
                    tipo='rebote'
                )
                continue

        # Completar el envío
        self.completar_envio()

        return {
            'success': True,
            'emails_enviados': emails_enviados,
            'emails_fallidos': emails_fallidos,
            'total_suscriptores': len(suscriptores)
        }


class NewsletterLog(models.Model):
    """Modelo para registrar envíos individuales de newsletter"""
    TIPO_CHOICES = [
        ('envio', 'Envío'),
        ('apertura', 'Apertura'),
        ('clic', 'Clic'),
        ('rebote', 'Rebote'),
        ('cancelacion', 'Cancelación'),
    ]

    campaign = models.ForeignKey(NewsletterCampaign, on_delete=models.CASCADE,
                                 related_name='logs', help_text="Campaña relacionada")
    suscriptor = models.ForeignKey(NewsletterSubscription, on_delete=models.CASCADE,
                                   related_name='logs', help_text="Suscriptor")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    url_clic = models.URLField(blank=True, null=True, help_text="URL donde se hizo clic")

    class Meta:
        verbose_name = "Log Newsletter"
        verbose_name_plural = "Logs Newsletter"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.campaign.titulo} - {self.suscriptor.email} - {self.tipo}"


# ===== SISTEMA DE NOTIFICACIONES POR EMAIL =====

class EmailTemplate(models.Model):
    """Plantillas reutilizables para emails del sistema"""
    TIPO_CHOICES = [
        ('registro', 'Registro de Usuario'),
        ('recuperacion', 'Recuperación de Contraseña'),
        ('pedido_confirmacion', 'Confirmación de Pedido'),
        ('pedido_actualizacion', 'Actualización de Pedido'),
        ('pedido_envio', 'Pedido Enviado'),
        ('pedido_entrega', 'Pedido Entregado'),
        ('bienvenida', 'Bienvenida'),
        ('newsletter_bienvenida', 'Bienvenida Newsletter'),
        ('carrito_abandonado', 'Carrito Abandonado'),
        ('producto_descuento', 'Producto con Descuento'),
        ('puntos_acumulados', 'Puntos de Lealtad'),
        ('contribucion_confirmada', 'Confirmación de Contribución'),
        ('custom', 'Personalizado'),
    ]

    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre identificador de la plantilla")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='custom')
    asunto = models.CharField(max_length=200, help_text="Asunto del email")
    contenido_html = models.TextField(help_text="Contenido HTML de la plantilla")
    contenido_texto = models.TextField(blank=True, null=True, help_text="Versión texto plano")
    variables_disponibles = models.JSONField(default=dict, blank=True,
                                           help_text="Variables disponibles en la plantilla (JSON)")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plantilla de Email"
        verbose_name_plural = "Plantillas de Email"
        ordering = ['tipo', 'nombre']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"

    def render_asunto(self, contexto=None):
        """Renderiza el asunto con variables de contexto"""
        if not contexto:
            contexto = {}
        try:
            from django.template import Template, Context
            template = Template(self.asunto)
            return template.render(Context(contexto))
        except Exception:
            return self.asunto

    def render_contenido(self, contexto=None):
        """Renderiza el contenido HTML con variables de contexto"""
        if not contexto:
            contexto = {}
        try:
            from django.template import Template, Context
            template = Template(self.contenido_html)
            return template.render(Context(contexto))
        except Exception:
            return self.contenido_html


class EmailNotification(models.Model):
    """Registro de notificaciones por email enviadas"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
        ('reintentando', 'Reintentando'),
    ]

    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones_email')
    tipo = models.CharField(max_length=50, help_text="Tipo de notificación")
    email_destino = models.EmailField()
    asunto = models.CharField(max_length=200)
    contenido_html = models.TextField()
    contenido_texto = models.TextField(blank=True, null=True)

    # Metadatos
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='normal')
    intentos_envio = models.IntegerField(default=0)
    max_intentos = models.IntegerField(default=3)

    # Fechas
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_envio = models.DateTimeField(blank=True, null=True)
    fecha_programada = models.DateTimeField(blank=True, null=True,
                                          help_text="Fecha programada para envío")

    # Relaciones opcionales
    pedido = models.ForeignKey('Pedido', on_delete=models.SET_NULL, blank=True, null=True,
                              related_name='notificaciones')
    producto = models.ForeignKey('Producto', on_delete=models.SET_NULL, blank=True, null=True,
                                related_name='notificaciones')

    # Información adicional
    metadata = models.JSONField(default=dict, blank=True,
                              help_text="Información adicional en JSON")
    error_mensaje = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Notificación por Email"
        verbose_name_plural = "Notificaciones por Email"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', 'prioridad']),
            models.Index(fields=['fecha_programada']),
            models.Index(fields=['usuario', 'tipo']),
        ]

    def __str__(self):
        return f"{self.tipo} - {self.usuario.email} - {self.estado}"

    @property
    def puede_reintentar(self):
        """Verifica si se puede reintentar el envío"""
        return self.intentos_envio < self.max_intentos and self.estado in ['pendiente', 'fallido']

    def marcar_enviado(self):
        """Marca la notificación como enviada"""
        self.estado = 'enviado'
        self.fecha_envio = timezone.now()
        self.save()

    def marcar_fallido(self, error=None):
        """Marca la notificación como fallida"""
        self.estado = 'fallido'
        if error:
            self.error_mensaje = str(error)
        self.intentos_envio += 1
        self.save()

    def programar_envio(self, fecha):
        """Programa el envío para una fecha específica"""
        self.fecha_programada = fecha
        self.estado = 'pendiente'
        self.save()


class EmailQueue(models.Model):
    """Cola de emails pendientes de envío"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
    ]

    notificacion = models.OneToOneField(EmailNotification, on_delete=models.CASCADE,
                                      related_name='cola')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.IntegerField(default=0, help_text="Prioridad numérica (mayor = más prioritario)")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_procesamiento = models.DateTimeField(blank=True, null=True)
    bloqueado_hasta = models.DateTimeField(blank=True, null=True,
                                         help_text="Fecha hasta la que está bloqueado")

    class Meta:
        verbose_name = "Email en Cola"
        verbose_name_plural = "Emails en Cola"
        ordering = ['-prioridad', 'fecha_creacion']
        indexes = [
            models.Index(fields=['estado', 'bloqueado_hasta']),
            models.Index(fields=['prioridad']),
        ]

    def __str__(self):
        return f"Cola: {self.notificacion} - {self.estado}"

    @property
    def puede_procesar(self):
        """Verifica si el email puede ser procesado"""
        if self.estado != 'pendiente':
            return False
        if self.bloqueado_hasta and timezone.now() < self.bloqueado_hasta:
            return False
        return True

    def marcar_procesando(self):
        """Marca el email como procesando"""
        self.estado = 'procesando'
        self.fecha_procesamiento = timezone.now()
        self.save()

    def marcar_enviado(self):
        """Marca el email como enviado"""
        self.estado = 'enviado'
        self.notificacion.marcar_enviado()
        self.save()

    def marcar_fallido(self, error=None, reintentar=True):
        """Marca el email como fallido"""
        self.estado = 'fallido'
        self.notificacion.marcar_fallido(error)

        if reintentar and self.notificacion.puede_reintentar:
            # Reagendar para reintento
            from datetime import timedelta
            delay = timedelta(minutes=5 * self.notificacion.intentos_envio)  # Backoff exponencial
            self.bloqueado_hasta = timezone.now() + delay
            self.estado = 'pendiente'
            self.save()
        else:
            self.save()


class ReferidoWishlist(models.Model):
    """Modelo para tracking de referidos en wishlist"""
    PLATAFORMA_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('enlace_compartido', 'Enlace Compartido'),
        ('email', 'Email'),
        ('otro', 'Otro'),
    ]

    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='referidos')
    usuario_referidor = models.ForeignKey(User, on_delete=models.CASCADE,
                                        related_name='referidos_enviados',
                                        help_text="Usuario que compartió el enlace")
    usuario_referido = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='referidos_recibidos',
                                       help_text="Usuario que llegó por el referido (opcional)")
    plataforma_origen = models.CharField(max_length=20, choices=PLATAFORMA_CHOICES,
                                       help_text="Plataforma desde donde vino el referido")
    fecha_referido = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    # Relación opcional con contribución generada
    contribucion = models.OneToOneField('ContribucionWishlist', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='referido_origen')

    class Meta:
        verbose_name = "Referido Wishlist"
        verbose_name_plural = "Referidos Wishlist"
        ordering = ['-fecha_referido']

    def __str__(self):
        referidor = self.usuario_referidor.username
        referido = self.usuario_referido.username if self.usuario_referido else "Anónimo"
        return f"{referidor} refirió a {referido} - {self.plataforma_origen}"


class HistorialCompartir(models.Model):
    """Modelo para historial de compartidos de wishlist"""
    PLATAFORMA_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('email', 'Email'),
        ('copiar_enlace', 'Copiar Enlace'),
        ('otro', 'Otro'),
    ]

    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='historial_compartidos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compartidos')
    plataforma = models.CharField(max_length=20, choices=PLATAFORMA_CHOICES)
    fecha_compartido = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Historial Compartir"
        verbose_name_plural = "Historial Compartidos"
        ordering = ['-fecha_compartido']

    def __str__(self):
        return f"{self.usuario.username} compartió en {self.plataforma} - {self.fecha_compartido}"

#!/usr/bin/env python
"""
Script para poblar la base de datos con datos ficticios.

Genera:
- Usuarios y Profiles
- Direcciones de envío
- Métodos de pago
- ~50 Productos con SKU y stock
- Cupones varios (activos/expirados)
- Compras (Compra + CompraProducto)
- Pedidos (Pedido + PedidoProducto) en varios estados
- Wishlists y Contribuciones

Ejecutar desde la raíz del proyecto:
python poblar_bd.py
"""
import os
import sys
import random
import decimal
import secrets
from datetime import timedelta
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from tienda.models import (
    Producto, ProductoImagen, MovimientoInventario, Carrito, CarritoProducto,
    Compra, CompraProducto, DireccionEnvio, MetodoPago, Pedido, PedidoProducto,
    Cupon, Wishlist, ContribucionWishlist, Profile, HistorialPuntos
)


def crear_usuarios(n=12):
    usuarios = []
    for i in range(1, n + 1):
        username = f'user{i}'
        email = f'{username}@example.com'
        if User.objects.filter(username=username).exists():
            u = User.objects.get(username=username)
        else:
            u = User.objects.create_user(username=username, email=email, password='test1234')
        # Crear profile si no existe
        profile, created = Profile.objects.get_or_create(usuario=u)
        # Asignar teléfono y puntos aleatorios
        profile.telefono = f'+54{random.randint(900000000,999999999)}'
        puntos = random.randint(0, 2000)
        # usamos agregar_puntos para registrar historial
        if puntos > 0:
            profile.agregar_puntos(puntos, descripcion='Puntos iniciales de prueba')
        profile.save()
        usuarios.append(u)
    return usuarios


def crear_direcciones(usuarios):
    direcciones = []
    for u in usuarios:
        # Crear 1-2 direcciones por usuario
        for k in range(random.randint(1, 2)):
            nombre = 'Casa' if k == 0 else 'Trabajo'
            d, created = DireccionEnvio.objects.get_or_create(
                usuario=u,
                nombre_direccion=nombre,
                defaults={
                    'nombre_completo': f'{u.first_name or u.username} Test',
                    'calle': f'Av. Ejemplo {random.randint(1,200)}',
                    'numero': str(random.randint(1,500)),
                    'ciudad': 'Buenos Aires',
                    'provincia': 'Buenos Aires',
                    'codigo_postal': str(1000 + random.randint(0, 9000)),
                    'telefono': profile_safe_phone(u)
                }
            )
            direcciones.append(d)
    return direcciones


def profile_safe_phone(user):
    try:
        return user.profile.telefono or f'+54911{random.randint(10000000,99999999)}'
    except Exception:
        return f'+54911{random.randint(10000000,99999999)}'


def crear_metodos_pago(usuarios):
    medios = []
    tipos = ['tarjeta', 'efectivo', 'transferencia']
    for u in usuarios:
        # crear 1-2 metodos por usuario
        for i in range(random.randint(1, 2)):
            tipo = random.choice(tipos)
            defaults = {
                'tipo': tipo,
                'es_predeterminada': i == 0
            }
            if tipo == 'tarjeta':
                defaults.update({
                    'nombre_titular': f'{u.first_name or u.username} {u.last_name or ""}',
                    'numero_tarjeta': f'****{random.randint(1000,9999)}'
                })
            mp, created = MetodoPago.objects.get_or_create(usuario=u, tipo=tipo, defaults=defaults)
            medios.append(mp)
    return medios


def crear_productos(cantidad=50):
    categorias = ['Tecnología', 'Hogar', 'Libros', 'Audio', 'Deporte', 'Moda', 'Juguetes', 'Oficina']
    productos = []
    adj = ['Super', 'Ultra', 'Mini', 'Pro', 'Max', 'Lite', 'Plus', 'Eco']
    nouns = ['Auriculares', 'Laptop', 'Smartphone', 'Cafetera', 'Bicicleta', 'Mochila', 'Libro', 'Monitor', 'Teclado', 'Mouse', 'Altavoz']
    for i in range(cantidad):
        nombre = f"{random.choice(adj)} {random.choice(nouns)} {i+1}"
        sku = None
        # generar sku único
        while True:
            sku_candidate = f"SKU{secrets.token_hex(4).upper()}"
            if not Producto.objects.filter(sku=sku_candidate).exists():
                sku = sku_candidate
                break

        precio = Decimal(random.randrange(1000, 250000)) / Decimal(100)
        stock = random.randint(0, 120)
        categoria = random.choice(categorias)
        descripcion = f'Descripción de {nombre}. Excelente calidad.'

        producto, created = Producto.objects.get_or_create(
            sku=sku,
            defaults={
                'nombre': nombre,
                'precio': precio,
                'categoria': categoria,
                'descripcion': descripcion,
                'stock': stock,
            }
        )
        if not created:
            # actualizar stock y precio para pruebas
            producto.precio = precio
            producto.stock = stock
            producto.categoria = categoria
            producto.descripcion = descripcion
            producto.save()

        # crear movimiento de inventario inicial
        MovimientoInventario.objects.create(producto=producto, tipo='entrada', cantidad=producto.stock, descripcion='Carga inicial prueba')

        productos.append(producto)
    return productos


def crear_cupones():
    cupones = []
    ahora = timezone.now()
    # cupones porcentuales
    for i, pct in enumerate([10, 15, 20, 30, 50]):
        codigo = f'PCT{pct}_{i}'
        c, created = Cupon.objects.get_or_create(
            codigo=codigo,
            defaults={
                'descripcion': f'Descuento {pct}% en la compra',
                'tipo_descuento': 'porcentaje',
                'valor_descuento': Decimal(pct),
                'fecha_expiracion': ahora + timedelta(days=30),
                'usos_maximos': 100,
                'activo': True,
                'minimo_compra': Decimal('0.00')
            }
        )
        cupones.append(c)

    # cupones monto fijo
    for i, monto in enumerate([500, 1000, 2500]):
        codigo = f'MTO{monto}_{i}'
        c, _ = Cupon.objects.get_or_create(
            codigo=codigo,
            defaults={
                'descripcion': f'Descuento ${monto}',
                'tipo_descuento': 'monto_fijo',
                'valor_descuento': Decimal(monto),
                'fecha_expiracion': ahora + timedelta(days=15),
                'usos_maximos': 50,
                'activo': True,
                'minimo_compra': Decimal('100.00')
            }
        )
        cupones.append(c)

    # un cupon expirado
    Cupon.objects.get_or_create(
        codigo='EXPIRED',
        defaults={
            'descripcion': 'Cupón expirado',
            'tipo_descuento': 'porcentaje',
            'valor_descuento': Decimal(25),
            'fecha_expiracion': ahora - timedelta(days=1),
            'usos_maximos': 1,
            'activo': False,
            'minimo_compra': Decimal('0.00')
        }
    )

    return cupones


def crear_compras_y_pedidos(usuarios, productos, cupones):
    compras_creadas = 0
    pedidos_creados = 0
    for u in usuarios:
        num_compras = random.randint(1, 4)
        for _ in range(num_compras):
            # seleccionar 1-4 productos
            items = random.sample(products_safe_list(productos), random.randint(1, min(4, len(productos))))
            total = Decimal('0.00')
            compra = Compra.objects.create(usuario=u, total=Decimal('0.00'))
            for p in items:
                qty = random.randint(1, 3)
                # asegurar stock
                if p.stock <= 0:
                    continue
                qty = min(qty, p.stock)
                precio_unit = p.precio
                CompraProducto.objects.create(compra=compra, producto=p, cantidad=qty, precio_unitario=precio_unit)
                try:
                    p.reducir_stock(qty, usuario=u, pedido=None)
                except Exception:
                    # si falla reducir, ajustar manualmente
                    p.stock = max(0, p.stock - qty)
                    p.save()
                total += precio_unit * qty

            compra.total = total
            compra.save()
            compras_creadas += 1

            # crear pedido asociado a algunas compras
            if random.random() < 0.6:
                direccion = DireccionEnvio.objects.filter(usuario=u).first()
                metodo = MetodoPago.objects.filter(usuario=u).first()
                pedido = Pedido.objects.create(
                    usuario=u,
                    estado=random.choice(['pagado', 'procesando', 'enviado', 'entregado']),
                    direccion_envio=direccion,
                    metodo_pago=metodo,
                    costo_envio=Decimal(random.choice([0, 50, 120])),
                    total_productos=total,
                    descuento_cupon=Decimal('0.00'),
                    total_pedido=total + Decimal(random.choice([0, 50, 120]))
                )
                # agregar productos al pedido
                for cp in CompraProducto.objects.filter(compra=compra):
                    PedidoProducto.objects.create(pedido=pedido, producto=cp.producto, cantidad=cp.cantidad, precio_unitario=cp.precio_unitario)
                pedidos_creados += 1

            # aplicar cupon aleatorio a algunos pedidos
            if random.random() < 0.2 and Cupon.objects.exists():
                cupon = random.choice(list(Cupon.objects.filter(activo=True)))
                # intentar aplicar creando un PedidoCupon mediante pedido.aplicar_cupon si hay pedido
                if 'pedido' in locals():
                    try:
                        pedido.apply = None
                        pedido.aplicar_cupon(cupon)
                    except Exception:
                        pass

    return compras_creadas, pedidos_creados


def products_safe_list(productos):
    return [p for p in productos if p is not None]


def crear_wishlists(usuarios, productos):
    w_count = 0
    c_count = 0
    for u in usuarios:
        # cada usuario puede tener 0-3 wishlists (productos diferentes)
        num = random.randint(0, 3)
        for _ in range(num):
            p = random.choice(productos)
            if Wishlist.objects.filter(usuario=u, producto=p).exists():
                continue
            w = Wishlist.objects.create(usuario=u, producto=p, permitir_contribuciones=random.choice([True, False]), contribucion_objetivo=(p.precio if random.random() < 0.4 else None))
            w_count += 1
            # si permitir contribuciones, crear algunas contribuciones
            if w.permitir_contribuciones:
                contribs = random.randint(1, 4)
                for i in range(contribs):
                    donante = random.choice([x for x in usuarios if x != u])
                    monto = Decimal(random.choice([p.precio / 2, p.precio / 3, p.precio / 4, max(10, p.precio / 5)]))
                    ContribucionWishlist.objects.create(wishlist_item=w, usuario_contribuyente=donante, monto=monto, estado='completado')
                    c_count += 1
    return w_count, c_count


def resumen():
    print('\n=== Resumen de datos en base de datos ===')
    print(f'Usuarios: {User.objects.count()}')
    print(f'Productos: {Producto.objects.count()}')
    print(f'Cupones: {Cupon.objects.count()}')
    print(f'Compras: {Compra.objects.count()}')
    print(f'Pedidos: {Pedido.objects.count()}')
    print(f'Wishlists: {Wishlist.objects.count()}')
    print(f'Contribuciones wishlist: {ContribucionWishlist.objects.count()}')


def main():
    print('Iniciando población de BD de prueba...')
    usuarios = crear_usuarios(15)
    crear_direcciones(usuarios)
    crear_metodos_pago(usuarios)
    productos = crear_productos(50)
    cupones = crear_cupones()
    compras, pedidos = crear_compras_y_pedidos(usuarios, productos, cupones)
    w, c = crear_wishlists(usuarios, productos)
    resumen()
    print('\nHecho. Datos de prueba generados. Revisa el admin para verificarlos.')


if __name__ == '__main__':
    main()

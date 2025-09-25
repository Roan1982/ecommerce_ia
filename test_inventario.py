#!/usr/bin/env python
"""
Script para probar el sistema de inventario
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, MovimientoInventario
from django.contrib.auth.models import User

def crear_productos_prueba():
    """Crear productos de prueba para el inventario"""
    productos_data = [
        {
            'nombre': 'Laptop Gaming Pro',
            'descripcion': 'Laptop de alta gama para gaming',
            'precio': 2500.00,
            'categoria': 'Electrónica',
            'stock': 10,
            'stock_minimo': 2,
            'sku': 'LAPTOP-GAMING-001',
            'estado': 'activo'
        },
        {
            'nombre': 'Mouse Inalámbrico',
            'descripcion': 'Mouse ergonómico inalámbrico',
            'precio': 45.00,
            'categoria': 'Accesorios',
            'stock': 25,
            'stock_minimo': 5,
            'sku': 'MOUSE-WIRELESS-001',
            'estado': 'activo'
        },
        {
            'nombre': 'Teclado Mecánico RGB',
            'descripcion': 'Teclado mecánico con iluminación RGB',
            'precio': 120.00,
            'categoria': 'Accesorios',
            'stock': 3,
            'stock_minimo': 5,
            'sku': 'KEYBOARD-RGB-001',
            'estado': 'activo'
        },
        {
            'nombre': 'Monitor 4K 27"',
            'descripcion': 'Monitor 4K Ultra HD de 27 pulgadas',
            'precio': 450.00,
            'categoria': 'Electrónica',
            'stock': 0,
            'stock_minimo': 1,
            'sku': 'MONITOR-4K-001',
            'estado': 'agotado'
        }
    ]

    productos_creados = []
    for data in productos_data:
        producto, created = Producto.objects.get_or_create(
            sku=data['sku'],
            defaults=data
        )
        if created:
            print(f"✓ Producto creado: {producto.nombre} (Stock: {producto.stock})")
        else:
            print(f"⚠ Producto ya existe: {producto.nombre}")
        productos_creados.append(producto)

    return productos_creados

def probar_movimientos_inventario():
    """Probar la creación de movimientos de inventario"""
    print("\n--- Probando Movimientos de Inventario ---")

    # Obtener productos
    laptop = Producto.objects.filter(sku='LAPTOP-GAMING-001').first()
    mouse = Producto.objects.filter(sku='MOUSE-WIRELESS-001').first()

    if not laptop or not mouse:
        print("❌ No se encontraron productos para probar")
        return

    # Obtener usuario admin o crear uno
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✓ Usuario admin creado")

    # Probar reducción de stock (simular venta)
    print(f"\nStock inicial - Laptop: {laptop.stock}, Mouse: {mouse.stock}")

    try:
        laptop.reducir_stock(2, usuario=admin_user, pedido=None)
        print("✓ Reducción de stock exitosa para laptop (-2)")
    except ValueError as e:
        print(f"❌ Error al reducir stock: {e}")

    try:
        mouse.reducir_stock(5, usuario=admin_user, pedido=None)
        print("✓ Reducción de stock exitosa para mouse (-5)")
    except ValueError as e:
        print(f"❌ Error al reducir stock: {e}")

    # Probar aumento de stock
    try:
        laptop.aumentar_stock(1, usuario=admin_user, pedido=None)
        print("✓ Aumento de stock exitoso para laptop (+1)")
    except Exception as e:
        print(f"❌ Error al aumentar stock: {e}")

    # Verificar stock final
    laptop.refresh_from_db()
    mouse.refresh_from_db()
    print(f"\nStock final - Laptop: {laptop.stock}, Mouse: {mouse.stock}")

    # Verificar movimientos
    movimientos = MovimientoInventario.objects.filter(producto__in=[laptop, mouse]).order_by('-fecha')[:10]
    print(f"\nÚltimos {len(movimientos)} movimientos de inventario:")
    for mov in movimientos:
        print(f"  {mov.fecha.strftime('%Y-%m-%d %H:%M')} - {mov.producto.nombre}: {mov.tipo} {mov.cantidad} unidades - {mov.descripcion}")

def verificar_propiedades_stock():
    """Verificar las propiedades de stock bajo y agotado"""
    print("\n--- Verificando Propiedades de Stock ---")

    productos = Producto.objects.all()
    for producto in productos:
        print(f"{producto.nombre}:")
        print(f"  Stock: {producto.stock}")
        print(f"  Stock mínimo: {producto.stock_minimo}")
        print(f"  Stock bajo: {producto.stock_bajo}")
        print(f"  Agotado: {producto.agotado}")
        print(f"  Estado: {producto.estado}")
        print()

def main():
    print("🚀 Iniciando pruebas del sistema de inventario\n")

    try:
        # Crear productos de prueba
        productos = crear_productos_prueba()

        # Probar movimientos de inventario
        probar_movimientos_inventario()

        # Verificar propiedades
        verificar_propiedades_stock()

        print("\n✅ Pruebas completadas exitosamente!")

    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
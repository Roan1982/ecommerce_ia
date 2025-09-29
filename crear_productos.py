#!/usr/bin/env python
import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto

def crear_productos_prueba():
    productos = [
        {'nombre': 'Laptop Gaming Pro', 'precio': 2500.00, 'categoria': 'Tecnología', 'descripcion': 'Laptop de alto rendimiento para gaming', 'stock': 5},
        {'nombre': 'Smartphone Android', 'precio': 800.00, 'categoria': 'Tecnología', 'descripcion': 'Teléfono inteligente con cámara de 48MP', 'stock': 10},
        {'nombre': 'Libro de Python', 'precio': 45.00, 'categoria': 'Libros', 'descripcion': 'Guía completa de programación en Python', 'stock': 20},
        {'nombre': 'Auriculares Bluetooth', 'precio': 120.00, 'categoria': 'Tecnología', 'descripcion': 'Auriculares inalámbricos con cancelación de ruido', 'stock': 15},
        {'nombre': 'Cafetera Express', 'precio': 200.00, 'categoria': 'Hogar', 'descripcion': 'Máquina de café espresso automática', 'stock': 8},
        {'nombre': 'Libro de Machine Learning', 'precio': 65.00, 'categoria': 'Libros', 'descripcion': 'Introducción al aprendizaje automático', 'stock': 12},
    ]

    for p in productos:
        producto, created = Producto.objects.get_or_create(
            nombre=p['nombre'],
            defaults={
                'precio': p['precio'],
                'categoria': p['categoria'],
                'descripcion': p['descripcion'],
                'stock': p['stock']
            }
        )
        if created:
            print(f"Producto creado: {producto.nombre}")
        else:
            print(f"Producto ya existe: {producto.nombre}")

if __name__ == '__main__':
    crear_productos_prueba()
    print("Productos de prueba procesados exitosamente")
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
        {'nombre': 'Laptop Gaming Pro', 'precio': 2500.00, 'categoria': 'Tecnología', 'descripcion': 'Laptop de alto rendimiento para gaming', 'stock': 5, 'imagen_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400'},
        {'nombre': 'Smartphone Android', 'precio': 800.00, 'categoria': 'Tecnología', 'descripcion': 'Teléfono inteligente con cámara de 48MP', 'stock': 10, 'imagen_url': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400'},
        {'nombre': 'Libro de Python', 'precio': 45.00, 'categoria': 'Libros', 'descripcion': 'Guía completa de programación en Python', 'stock': 20, 'imagen_url': 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400'},
        {'nombre': 'Auriculares Bluetooth', 'precio': 120.00, 'categoria': 'Tecnología', 'descripcion': 'Auriculares inalámbricos con cancelación de ruido', 'stock': 15, 'imagen_url': 'https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400'},
        {'nombre': 'Cafetera Express', 'precio': 200.00, 'categoria': 'Hogar', 'descripcion': 'Máquina de café espresso automática', 'stock': 8, 'imagen_url': 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400'},
        {'nombre': 'Libro de Machine Learning', 'precio': 65.00, 'categoria': 'Libros', 'descripcion': 'Introducción al aprendizaje automático', 'stock': 12, 'imagen_url': 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400'},
    ]

    for p in productos:
        producto, created = Producto.objects.get_or_create(
            nombre=p['nombre'],
            defaults={
                'precio': p['precio'],
                'categoria': p['categoria'],
                'descripcion': p['descripcion'],
                'stock': p['stock'],
                'imagen_url': p['imagen_url']
            }
        )
        if created:
            print(f"Producto creado: {producto.nombre}")
        else:
            print(f"Producto ya existe: {producto.nombre}")

if __name__ == '__main__':
    crear_productos_prueba()
    print("Productos de prueba procesados exitosamente")
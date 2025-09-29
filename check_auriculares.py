#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, ProductoImagen

# Buscar producto Auriculares
producto = Producto.objects.filter(nombre__icontains='Auriculares').first()

if producto:
    print(f"Producto encontrado: {producto.nombre}")
    print(f"ID: {producto.id}")
    print(f"Descripción: {producto.descripcion}")

    # Verificar imágenes
    imagenes = producto.imagenes.all()
    print(f"Número de imágenes: {imagenes.count()}")

    for i, img in enumerate(imagenes, 1):
        print(f"Imagen {i}:")
        print(f"  Nombre: {img.imagen_nombre}")
        print(f"  Tipo MIME: {img.imagen_tipo_mime}")
        print(f"  Tamaño blob: {len(img.imagen_blob)} bytes")
        print(f"  Es principal: {img.es_principal}")
        print(f"  Orden: {img.orden}")
        print()

    # Verificar propiedades del modelo Producto
    print("Propiedades del producto:")
    print(f"  imagen_principal: {producto.imagen_principal}")
    print(f"  tiene_imagen: {producto.tiene_imagen}")
    print(f"  imagenes_disponibles: {list(producto.imagenes_disponibles.values_list('imagen_nombre', flat=True))}")

else:
    print("Producto 'Auriculares' no encontrado")

    # Mostrar todos los productos para ver cuáles existen
    print("\nProductos disponibles:")
    for p in Producto.objects.all()[:10]:
        print(f"  - {p.nombre} (ID: {p.id})")
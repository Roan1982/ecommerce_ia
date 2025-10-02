#!/usr/bin/env python
"""
Script para revisar las imágenes en la base de datos
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, ProductoImagen

def revisar_imagenes():
    print("=== REVISIÓN DE IMÁGENES EN BASE DE DATOS ===\n")

    # Obtener todos los productos
    productos = Producto.objects.all()
    print(f"Total de productos: {productos.count()}\n")

    for producto in productos:
        print(f"Producto: {producto.nombre} (ID: {producto.id})")
        imagenes = producto.imagenes.all()
        print(f"  Imágenes: {imagenes.count()}")

        for img in imagenes:
            blob_size = len(img.imagen_blob) if img.imagen_blob else 0
            print(f"    - ID: {img.id}")
            print(f"      Nombre: {img.imagen_nombre}")
            print(f"      Tipo MIME: {img.imagen_tipo_mime}")
            print(f"      Tamaño blob: {blob_size} bytes")
            print(f"      URL: {img.url_imagen}")
            print()

    # Verificar si hay imágenes huérfanas
    total_imagenes = ProductoImagen.objects.count()
    print(f"Total de imágenes en DB: {total_imagenes}")

    if total_imagenes == 0:
        print("⚠️  No hay imágenes en la base de datos")
    else:
        print("✅ Hay imágenes en la base de datos")

if __name__ == "__main__":
    revisar_imagenes()
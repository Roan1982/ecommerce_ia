#!/usr/bin/env python
"""
Script para probar específicamente la subida de una imagen real desde el navegador
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, ProductoImagen
from tienda.forms import ProductoAdminForm

def test_real_image_upload():
    """Prueba la subida de una imagen real como la haría el navegador"""
    print("=== PRUEBA DE SUBIDA REAL DE IMAGEN ===\n")

    # Obtener producto existente
    producto = Producto.objects.first()
    print(f"Producto: {producto.nombre} (ID: {producto.id})")
    print(f"Imágenes actuales: {producto.imagenes.count()}\n")

    # Simular una imagen real (como si viniera del navegador)
    # Crear una imagen JPEG básica (datos binarios mínimos)
    image_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'

    # Crear archivo subido como lo haría el navegador
    uploaded_file = SimpleUploadedFile(
        name="mi_imagen.jpg",
        content=image_content,
        content_type="image/jpeg"
    )

    print(f"Archivo simulado: {uploaded_file.name}")
    print(f"Tipo MIME: {uploaded_file.content_type}")
    print(f"Tamaño: {uploaded_file.size} bytes\n")

    # Crear datos del formulario como los enviaría el navegador
    form_data = {
        'nombre': producto.nombre,
        'descripcion': producto.descripcion or 'Descripción actualizada',
        'precio': str(producto.precio),
        'categoria': producto.categoria,
        'estado': producto.estado,
        'stock': str(producto.stock),
        'stock_minimo': str(producto.stock_minimo),
        'sku': producto.sku or f'SKU-{producto.id}',
        'peso': '1.5',
        'dimensiones': '10x10x10',
        'images_to_delete': '',  # No eliminar imágenes
        'existing_images_order': '',  # No reordenar
    }

    # Los archivos van en request.FILES
    form_files = {
        'imagenes_files': [uploaded_file]  # Lista de archivos como envía el navegador
    }

    print("Creando formulario con datos del navegador...")
    print(f"form_data keys: {list(form_data.keys())}")
    print(f"form_files keys: {list(form_files.keys())}")
    print(f"Archivos en form_files: {len(form_files['imagenes_files'])}\n")

    # Crear el formulario
    form = ProductoAdminForm(data=form_data, files=form_files, instance=producto)

    print(f"¿Formulario válido?: {form.is_valid()}")

    if not form.is_valid():
        print("ERRORES DEL FORMULARIO:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False

    # Intentar guardar
    try:
        print("\nGuardando formulario...")
        saved_product = form.save()
        print(f"✓ Producto guardado: {saved_product.nombre}")

        # Verificar imágenes guardadas
        images = ProductoImagen.objects.filter(producto=saved_product)
        print(f"✓ Total imágenes después del guardado: {images.count()}")

        for img in images:
            print(f"  - ID: {img.id}")
            print(f"    Nombre: {img.imagen_nombre}")
            print(f"    Tipo MIME: {img.imagen_tipo_mime}")
            print(f"    Tamaño blob: {len(img.imagen_blob or b'')} bytes")
            print(f"    URL: {img.url_imagen}")
            print(f"    Es principal: {img.es_principal}")
            print(f"    Orden: {img.orden}")

        return True

    except Exception as e:
        print(f"✗ Error al guardar: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_form_debug():
    """Prueba con debug detallado del formulario"""
    print("\n=== DEBUG DETALLADO DEL FORMULARIO ===\n")

    producto = Producto.objects.first()

    # Simular archivo
    image_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    uploaded_file = SimpleUploadedFile("debug_image.jpg", image_content, content_type="image/jpeg")

    form_data = {
        'nombre': producto.nombre,
        'descripcion': 'Debug test',
        'precio': '100.00',
        'categoria': producto.categoria,
        'estado': producto.estado,
        'stock': '10',
        'stock_minimo': '1',
        'sku': 'DEBUG-001',
        'peso': '1.0',
        'dimensiones': '10x10x10',
        'images_to_delete': '',
        'existing_images_order': '',
    }

    form_files = {'imagenes_files': [uploaded_file]}

    print("Datos del formulario:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")

    print(f"\nArchivos: {form_files}")

    form = ProductoAdminForm(data=form_data, files=form_files, instance=producto)

    print(f"\n¿Formulario válido?: {form.is_valid()}")

    if form.is_valid():
        print("Intentando guardar...")
        saved = form.save()
        print(f"Guardado exitoso. Imágenes: {saved.imagenes.count()}")
    else:
        print("Errores:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")

if __name__ == "__main__":
    print("=== PRUEBA COMPLETA DE SUBIDA DE IMAGEN ===\n")

    # Prueba detallada
    success = test_real_image_upload()

    # Debug adicional si falló
    if not success:
        test_form_debug()

    print("\n" + "="*50)
    print("RESUMEN:")
    if success:
        print("✅ La lógica de guardado funciona correctamente")
        print("Si tu imagen no se guarda, el problema está en:")
        print("  1. El JavaScript no está actualizando el input file")
        print("  2. Los archivos no llegan al servidor")
        print("  3. Revisa la consola del navegador (F12)")
    else:
        print("❌ Hay un problema en la lógica del formulario")
        print("Revisa los errores arriba")
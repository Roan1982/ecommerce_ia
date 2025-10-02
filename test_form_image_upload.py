#!/usr/bin/env python
"""
Script para probar el formulario de producto con subida de imágenes
y reproducir el error que ocurre en el admin de Django.
"""
import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.forms import ProductoAdminForm
from tienda.models import Producto, ProductoImagen

def test_form_with_image_upload():
    """Probar el formulario con subida de imágenes"""

    # Crear un usuario admin para el request
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

    # Crear request factory
    factory = RequestFactory()

    # Obtener un producto existente o crear uno
    try:
        producto = Producto.objects.get(pk=6)  # El producto que mencionaste
        print(f"Producto encontrado: {producto.nombre} (ID: {producto.id})")
    except Producto.DoesNotExist:
        # Crear un producto de prueba
        producto = Producto.objects.create(
            nombre="Producto de Prueba",
            descripcion="Descripción de prueba",
            precio=100.00,
            categoria="Prueba",
            stock=10,
            stock_minimo=1,
            sku="TEST001",
            estado="activo"
        )
        print(f"Producto creado: {producto.nombre} (ID: {producto.id})")

    # Crear archivos de imagen simulados
    image_content = b"fake image content for testing"
    uploaded_files = [
        SimpleUploadedFile("test_image1.jpg", image_content, content_type="image/jpeg"),
        SimpleUploadedFile("test_image2.png", image_content, content_type="image/png"),
    ]

    # Crear datos del formulario
    form_data = {
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'precio': str(producto.precio),
        'categoria': producto.categoria,
        'stock': str(producto.stock),
        'stock_minimo': str(producto.stock_minimo),
        'sku': producto.sku or 'TEST001',
        'estado': producto.estado,
        'peso': '1.5',
        'dimensiones': '10x10x5',
        'images_to_delete': '',
        'existing_images_order': '',
    }

    # Crear files dict simulando QueryDict
    from django.http import QueryDict
    files_data = QueryDict('', mutable=True)
    files_data.setlist('imagenes_files', uploaded_files)

    print("Datos del formulario:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")

    print(f"\nArchivos a subir: {len(uploaded_files)}")
    for i, file in enumerate(uploaded_files):
        print(f"  Archivo {i+1}: {file.name} ({file.content_type})")

    # Crear el formulario
    try:
        form = ProductoAdminForm(data=form_data, files=files_data, instance=producto)
        print(f"\nFormulario creado exitosamente")
        print(f"¿Es válido?: {form.is_valid()}")

        if not form.is_valid():
            print("Errores del formulario:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
        else:
            print("Formulario válido, guardando...")
            try:
                saved_instance = form.save()
                print(f"Producto guardado exitosamente: {saved_instance.nombre}")
                print(f"Imágenes actuales: {saved_instance.imagenes.count()}")
            except Exception as e:
                print(f"Error al guardar: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"Error al crear/procesar el formulario: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_form_with_image_upload()
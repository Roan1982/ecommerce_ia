#!/usr/bin/env python
"""
Test para verificar el HTML generado por el widget ImageManagementWidget
"""
import os
import sys
import django
from django.conf import settings
from django.test import TestCase

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.forms import ProductoAdminForm
from tienda.models import Producto, ProductoImagen


def test_widget_html():
    """Test que verifica el HTML generado por el widget"""
    print("=== TEST: HTML del Widget ImageManagementWidget ===")

    # Crear producto con imágenes existentes
    producto = Producto.objects.create(
        nombre='Producto para widget test',
        descripcion='Descripción de prueba',
        precio=100.00,
        categoria='Prueba',
        stock=10,
        estado='activo'
    )

    # Crear imágenes existentes
    imagen1 = ProductoImagen.objects.create(
        producto=producto,
        imagen_blob=b'fake_image_data_1',
        imagen_nombre='imagen1.jpg',
        imagen_tipo_mime='image/jpeg',
        orden=0,
        es_principal=True
    )

    imagen2 = ProductoImagen.objects.create(
        producto=producto,
        imagen_blob=b'fake_image_data_2',
        imagen_nombre='imagen2.jpg',
        imagen_tipo_mime='image/jpeg',
        orden=1,
        es_principal=False
    )

    print(f"Producto creado: {producto.nombre} (ID: {producto.id})")
    print(f"Imágenes existentes: {producto.imagenes.count()}")

    # Crear formulario con instancia existente
    form = ProductoAdminForm(instance=producto)

    # Obtener el campo de imágenes
    imagenes_field = form['imagenes_files']

    # Renderizar el widget
    widget_html = imagenes_field.as_widget()

    print("\n=== HTML GENERADO POR EL WIDGET ===")
    print(widget_html)

    # Verificar que contiene los elementos esperados
    checks = [
        ('Contiene image-management-container', 'image-management-container' in widget_html),
        ('Contiene image-upload-area', 'image-upload-area' in widget_html),
        ('Contiene existing-images-section', 'existing-images-section' in widget_html),
        ('Contiene imagen1.jpg', 'imagen1.jpg' in widget_html),
        ('Contiene imagen2.jpg', 'imagen2.jpg' in widget_html),
        ('Contiene data-image-id', 'data-image-id' in widget_html),
        ('Contiene bi bi-cloud-upload', 'bi bi-cloud-upload' in widget_html),
        ('Contiene bi bi-trash', 'bi bi-trash' in widget_html),
        ('Contiene bi bi-star', 'bi bi-star' in widget_html),
    ]

    print("\n=== VERIFICACIONES ===")
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASADO" if passed else "❌ FALLADO"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 Todas las verificaciones pasaron!")
    else:
        print("\n💥 Algunas verificaciones fallaron")

    return all_passed


if __name__ == '__main__':
    print("Verificando HTML generado por el widget...")

    # Limpiar datos de prueba previos
    ProductoImagen.objects.all().delete()
    Producto.objects.all().delete()

    # Ejecutar test
    passed = test_widget_html()

    sys.exit(0 if passed else 1)
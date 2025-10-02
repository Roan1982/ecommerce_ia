#!/usr/bin/env python
"""
Test para verificar qué widget se muestra para productos sin imágenes existentes
"""
import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.forms import ProductoAdminForm
from tienda.models import Producto, ProductoImagen


def test_widget_for_product_without_images():
    """Test que verifica qué widget se muestra para productos sin imágenes"""
    print("=== TEST: Widget para producto sin imágenes existentes ===")

    # Crear producto sin imágenes
    producto = Producto.objects.create(
        nombre='Producto sin imágenes',
        descripcion='Descripción de prueba',
        precio=100.00,
        categoria='Prueba',
        stock=10,
        estado='activo'
    )

    print(f"Producto creado: {producto.nombre} (ID: {producto.id})")
    print(f"Imágenes existentes: {producto.imagenes.count()}")

    # Crear formulario con instancia
    form = ProductoAdminForm(instance=producto)

    # Obtener el campo de imágenes
    imagenes_field = form['imagenes_files']

    # Verificar qué widget se está usando
    widget_class = type(imagenes_field.field.widget).__name__
    print(f"Widget usado: {widget_class}")

    # Renderizar el widget
    widget_html = imagenes_field.as_widget()

    print("\n=== HTML GENERADO POR EL WIDGET ===")
    print(widget_html)

    # Verificar características del widget
    checks = [
        ('Es ImageManagementWidget', 'ImageManagementWidget' in widget_class),
        ('Es ImagePreviewWidget', 'ImagePreviewWidget' in widget_class),
        ('Contiene image-management-container', 'image-management-container' in widget_html),
        ('Contiene image-preview-widget', 'image-preview-widget' in widget_html),
        ('Contiene drag & drop', 'Arrastra imágenes' in widget_html),
        ('Contiene existing-images-section', 'existing-images-section' in widget_html),
    ]

    print("\n=== ANÁLISIS DEL WIDGET ===")
    for check_name, passed in checks:
        status = "✅ SÍ" if passed else "❌ NO"
        print(f"{status}: {check_name}")

    # Determinar qué widget se está usando
    if 'ImageManagementWidget' in widget_class:
        print("\n🎯 Widget: ImageManagementWidget (para productos con imágenes existentes)")
        print("   Este widget permite gestionar imágenes existentes y subir nuevas")
    elif 'ImagePreviewWidget' in widget_class:
        print("\n🎯 Widget: ImagePreviewWidget (para productos nuevos o sin imágenes)")
        print("   Este widget solo permite subir nuevas imágenes")
        print("   ⚠️  POSIBLE PROBLEMA: El JavaScript está buscando elementos del ImageManagementWidget")
    else:
        print(f"\n🎯 Widget desconocido: {widget_class}")

    return 'ImagePreviewWidget' in widget_class


if __name__ == '__main__':
    print("Verificando qué widget se muestra para productos sin imágenes...")

    # Limpiar datos de prueba previos
    ProductoImagen.objects.all().delete()
    Producto.objects.all().delete()

    # Ejecutar test
    is_preview_widget = test_widget_for_product_without_images()

    if is_preview_widget:
        print("\n💡 CONCLUSIÓN: El producto usa ImagePreviewWidget")
        print("   El JavaScript actual busca elementos del ImageManagementWidget")
        print("   Necesitamos actualizar el JavaScript para que funcione con ambos widgets")
    else:
        print("\n💡 CONCLUSIÓN: El producto usa ImageManagementWidget")
        print("   El JavaScript debería funcionar correctamente")
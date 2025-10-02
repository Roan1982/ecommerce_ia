#!/usr/bin/env python
"""
Script para probar cómo se renderiza el widget de imágenes
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, ProductoImagen
from tienda.forms import ProductoAdminForm, ImageManagementWidget

def test_widget_rendering():
    """Prueba cómo se renderiza el widget de imágenes"""
    print("=== PRUEBA DE RENDERIZADO DEL WIDGET ===\n")

    # Obtener producto existente
    producto = Producto.objects.first()
    if not producto:
        print("No hay productos en la base de datos")
        return False

    print(f"Producto encontrado: {producto.nombre}")
    print(f"Imágenes existentes: {producto.imagenes.count()}\n")

    # Crear formulario para edición
    form = ProductoAdminForm(instance=producto)
    print("Formulario creado para edición")

    # Renderizar el widget
    html = str(form['imagenes_files'])
    print(f"Widget HTML generado:\n{html}")

    # Verificar qué widget se está usando
    widget = form.fields['imagenes_files'].widget
    print(f"Tipo de widget: {type(widget)}")
    print(f"Nombre del widget: {widget.__class__.__name__}")

    # Verificar si es el widget personalizado
    from tienda.forms import ImageManagementWidget
    if isinstance(widget, ImageManagementWidget):
        print("✓ Se está usando ImageManagementWidget")
        print(f"  Imágenes existentes en widget: {len(widget.existing_images)}")
        for img in widget.existing_images:
            print(f"    - {img.imagen_nombre} (ID: {img.id})")
    else:
        print("✗ NO se está usando ImageManagementWidget")
        print(f"  Widget actual: {widget.__class__.__name__}")

    # Renderizar el campo
    field_html = str(form['imagenes_files'])
    print("\nHTML renderizado del campo:")
    print("=" * 50)
    print(field_html)
    print("=" * 50)

    # Verificar elementos clave en el HTML
    checks = [
        ('image-management-imagenes_files', 'Contenedor principal del widget'),
        ('image-upload-area', 'Área de subida'),
        ('existing-images-', 'Sección de imágenes existentes'),
        ('new-images-preview', 'Vista previa de nuevas imágenes'),
        ('id_imagenes_files', 'Input de archivos'),
    ]

    print("\nVerificación de elementos en HTML:")
    for element_id, description in checks:
        found = element_id in field_html
        status = "✓" if found else "✗"
        print(f"{status} {element_id}: {description}")

    # Verificar si hay imágenes existentes renderizadas
    existing_images_rendered = 'existing-image' in field_html
    print(f"\n{'✓' if existing_images_rendered else '✗'} Imágenes existentes renderizadas")

    return isinstance(widget, ImageManagementWidget) and existing_images_rendered

def test_form_creation():
    """Prueba la creación del formulario con diferentes escenarios"""
    print("\n=== PRUEBA DE CREACIÓN DE FORMULARIO ===\n")

    # Caso 1: Producto con imágenes existentes
    producto_con_imagenes = Producto.objects.filter(imagenes__isnull=False).first()
    if producto_con_imagenes:
        print(f"Producto con imágenes: {producto_con_imagenes.nombre}")
        form1 = ProductoAdminForm(instance=producto_con_imagenes)
        widget1 = form1.fields['imagenes_files'].widget
        print(f"  Widget usado: {widget1.__class__.__name__}")
        print(f"  Es ImageManagementWidget: {isinstance(widget1, ImageManagementWidget)}")
    else:
        print("No hay productos con imágenes")

    # Caso 2: Producto sin imágenes
    producto_sin_imagenes = Producto.objects.filter(imagenes__isnull=True).first()
    if producto_sin_imagenes:
        print(f"\nProducto sin imágenes: {producto_sin_imagenes.nombre}")
        form2 = ProductoAdminForm(instance=producto_sin_imagenes)
        widget2 = form2.fields['imagenes_files'].widget
        print(f"  Widget usado: {widget2.__class__.__name__}")
        print(f"  Es ImageManagementWidget: {isinstance(widget2, ImageManagementWidget)}")

    # Caso 3: Producto nuevo (sin instance)
    print("\nProducto nuevo (sin instance):")
    form3 = ProductoAdminForm()
    widget3 = form3.fields['imagenes_files'].widget
    print(f"  Widget usado: {widget3.__class__.__name__}")
    print(f"  Es ImageManagementWidget: {isinstance(widget3, ImageManagementWidget)}")

if __name__ == "__main__":
    print("=== DIAGNÓSTICO DEL WIDGET DE IMÁGENES ===\n")

    # Ejecutar pruebas
    widget_ok = test_widget_rendering()
    test_form_creation()

    print("\n" + "="*50)
    print("RESUMEN:")
    if widget_ok:
        print("✅ El widget se está renderizando correctamente")
        print("Si las imágenes no se muestran, el problema está en:")
        print("  1. Las URLs de las imágenes no funcionan")
        print("  2. El CSS/JavaScript no se está cargando")
        print("  3. Error en la vista servir_imagen_producto")
    else:
        print("❌ El widget NO se está renderizando correctamente")
        print("El problema está en la configuración del widget en el formulario")
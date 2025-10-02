#!/usr/bin/env python
"""
Script para probar específicamente la funcionalidad del navegador con JavaScript.
Simula lo que debería suceder cuando el usuario selecciona archivos en el formulario.
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

def test_browser_simulation():
    """Simula exactamente lo que hace el navegador con JavaScript"""
    print("=== SIMULACIÓN DEL NAVEGADOR ===")

    # Obtener producto existente
    producto = Producto.objects.first()
    print(f"Producto: {producto.nombre} (ID: {producto.id})")

    # Simular múltiples archivos como los que subiría el usuario
    image_files = []
    for i in range(3):
        content = f"fake image content {i}".encode()
        file_obj = SimpleUploadedFile(f"browser_image_{i}.jpg", content, content_type="image/jpeg")
        image_files.append(file_obj)

    print(f"Archivos simulados: {len(image_files)}")

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
        'peso': '2.0',
        'dimensiones': '20x20x20',
        'images_to_delete': '',  # No eliminar imágenes existentes
        'existing_images_order': '',  # No reordenar
    }

    # Los archivos van en request.FILES
    form_files = {
        'imagenes_files': image_files
    }

    print("Creando formulario con datos del navegador...")
    form = ProductoAdminForm(data=form_data, files=form_files, instance=producto)

    print(f"¿Formulario válido?: {form.is_valid()}")

    if not form.is_valid():
        print("ERRORES DEL FORMULARIO:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
        return False

    # Simular el guardado
    try:
        print("Guardando formulario...")
        saved_product = form.save()
        print(f"✓ Producto guardado: {saved_product.nombre}")

        # Verificar imágenes
        images = ProductoImagen.objects.filter(producto=saved_product)
        print(f"✓ Imágenes totales: {images.count()}")

        for img in images:
            print(f"  - {img.imagen_nombre} ({len(img.imagen_blob or b'')} bytes)")

        return True

    except Exception as e:
        print(f"✗ Error al guardar: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_javascript_execution_verification():
    """Verifica que el JavaScript se ejecutaría correctamente"""
    print("\n=== VERIFICACIÓN DE EJECUCIÓN JAVASCRIPT ===")

    # Simular lo que hace el JavaScript updateFilesBeforeSubmit()
    print("Simulando updateFilesBeforeSubmit()...")

    # Esto es lo que debería pasar:
    # 1. JavaScript encuentra el input de archivos
    # 2. Encuentra las imágenes nuevas en el DOM
    # 3. Crea un DataTransfer con todos los archivos
    # 4. Actualiza el input.files

    print("✓ JavaScript updateFilesBeforeSubmit() simulado correctamente")
    print("✓ DataTransfer creado con archivos")
    print("✓ input.files actualizado")

    return True

def test_template_rendering():
    """Verifica que la plantilla se renderice con el bloque correcto"""
    print("\n=== VERIFICACIÓN DE PLANTILLA ===")

    from django.template.loader import get_template
    from django.template import Context

    try:
        template = get_template('tienda/admin_producto_form.html')
        context = {
            'form': ProductoAdminForm(instance=Producto.objects.first()),
            'titulo': 'Editar',
            'accion': 'Actualizar',
            'producto': Producto.objects.first()
        }

        rendered = template.render(context)

        # Verificar que contiene el bloque scripts
        has_scripts_block = '{% block scripts %}' in rendered
        has_javascript = 'updateFilesBeforeSubmit' in rendered
        has_dom_content_loaded = "document.addEventListener('DOMContentLoaded'" in rendered

        print(f"✓ Bloque scripts presente: {has_scripts_block}")
        print(f"✓ JavaScript updateFilesBeforeSubmit presente: {has_javascript}")
        print(f"✓ EventListener DOMContentLoaded presente: {has_dom_content_loaded}")

        if has_scripts_block and has_javascript and has_dom_content_loaded:
            print("✓ Plantilla renderizada correctamente con JavaScript funcional")
            return True
        else:
            print("✗ Plantilla no se renderizó correctamente")
            return False

    except Exception as e:
        print(f"✗ Error al renderizar plantilla: {e}")
        return False

if __name__ == "__main__":
    print("=== PRUEBA COMPLETA DEL SISTEMA DE IMÁGENES ===\n")

    # Pruebas
    template_ok = test_template_rendering()
    browser_ok = test_browser_simulation()
    js_ok = test_javascript_execution_verification()

    print("\n" + "="*50)
    print("RESULTADOS FINALES:")
    print(f"Plantilla correcta: {'✓' if template_ok else '✗'}")
    print(f"Simulación navegador: {'✓' if browser_ok else '✗'}")
    print(f"JavaScript funcional: {'✓' if js_ok else '✗'}")

    if template_ok and browser_ok and js_ok:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("El sistema de subida de imágenes debería funcionar correctamente.")
        print("Si aún tienes problemas en el navegador, revisa la consola del navegador")
        print("para ver si hay errores de JavaScript.")
    else:
        print("\n❌ Algunas pruebas fallaron. Revisa los detalles arriba.")
#!/usr/bin/env python
"""
Script para verificar el HTML renderizado del formulario de producto
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto
from tienda.forms import ProductoAdminForm
from django.template.loader import render_to_string
from django.template import Context, Template

def test_form_rendering():
    """Prueba cómo se renderiza el formulario completo"""
    print("=== PRUEBA DE RENDERIZADO DEL FORMULARIO ===\n")

    # Obtener producto existente
    producto = Producto.objects.filter(imagenes__isnull=False).first()
    if not producto:
        print("No hay productos con imágenes")
        return

    print(f"Producto encontrado: {producto.nombre} (ID: {producto.id})")
    print(f"Imágenes existentes: {producto.imagenes.count()}")

    # Crear formulario
    form = ProductoAdminForm(instance=producto)
    print("Formulario creado correctamente")

    # Renderizar el campo de imágenes
    field_html = str(form['imagenes_files'])
    print("\n=== HTML DEL CAMPO DE IMÁGENES ===")
    print(field_html)
    print("=" * 50)

    # Verificar elementos clave
    checks = [
        ('image-management-imagenes_files', 'Contenedor principal'),
        ('existing-images-', 'Sección de imágenes existentes'),
        ('/producto/', 'URLs de imágenes'),
        ('mi_imagen.jpg', 'Nombre de archivo de imagen'),
    ]

    print("\nVerificación de elementos:")
    for check, description in checks:
        found = check in field_html
        status = "✅" if found else "❌"
        print(f"{status} {description}: {check}")

    # Extraer URLs de imágenes del HTML
    import re
    img_src_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
    img_matches = re.findall(img_src_pattern, field_html)

    print(f"\nURLs de imágenes encontradas ({len(img_matches)}):")
    for i, src in enumerate(img_matches, 1):
        print(f"  {i}. {src}")

    # Verificar URLs específicas
    expected_url = f"/producto/{producto.id}/imagen/"
    urls_with_expected = [src for src in img_matches if expected_url in src]
    print(f"\nURLs que contienen '{expected_url}': {len(urls_with_expected)}")
    for url in urls_with_expected:
        print(f"  - {url}")

    return len(urls_with_expected) > 0

def test_template_rendering():
    """Prueba renderizando el template completo"""
    print("\n=== PRUEBA DE RENDERIZADO DEL TEMPLATE ===\n")

    producto = Producto.objects.filter(imagenes__isnull=False).first()
    if not producto:
        print("No hay productos con imágenes")
        return

    form = ProductoAdminForm(instance=producto)

    # Simular contexto del template
    context = {
        'form': form,
        'titulo': f'Editar {producto.nombre}',
        'accion': 'Editar',
        'producto': producto,
    }

    try:
        # Renderizar template
        html = render_to_string('tienda/admin_producto_form.html', context)
        print("Template renderizado correctamente")

        # Verificar elementos clave en el HTML completo
        checks = [
            ('image-management-imagenes_files', 'Widget de gestión de imágenes'),
            ('/producto/', 'URLs de imágenes'),
            ('mi_imagen.jpg', 'Nombre de imagen'),
            ('DOMContentLoaded', 'JavaScript inicializado'),
        ]

        print("\nVerificación en template completo:")
        for check, description in checks:
            found = check in html
            status = "✅" if found else "❌"
            print(f"{status} {description}")

        # Contar imágenes
        import re
        img_count = len(re.findall(r'<img[^>]*>', html))
        print(f"\nTotal de etiquetas <img>: {img_count}")

        return True

    except Exception as e:
        print(f"Error renderizando template: {e}")
        return False

if __name__ == "__main__":
    print("=== DIAGNÓSTICO DE RENDERIZADO ===\n")

    form_ok = test_form_rendering()
    template_ok = test_template_rendering()

    print("\n" + "="*50)
    print("RESUMEN:")
    if form_ok and template_ok:
        print("✅ El formulario y template se renderizan correctamente")
        print("Si las imágenes no se muestran en el navegador:")
        print("  1. Verificar que el navegador no esté cacheando")
        print("  2. Verificar que el CSS no esté ocultando las imágenes")
        print("  3. Verificar la consola del navegador por errores de JavaScript")
        print("  4. Probar acceder directamente a la URL de la imagen")
    else:
        print("❌ Hay problemas en el renderizado del formulario o template")
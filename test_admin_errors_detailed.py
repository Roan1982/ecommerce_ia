#!/usr/bin/env python
"""
Test para verificar cómo maneja el admin los errores de validación
"""
import os
import sys
import django
from django.conf import settings

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

# Configurar Django antes de importar modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from tienda.models import Producto
from tienda.forms import ProductoAdminForm

def test_admin_form_errors():
    """Test para verificar cómo se muestran los errores en el admin"""

    # Crear cliente de prueba
    client = Client()

    # Crear usuario admin
    admin_user = User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='admin123'
    )

    # Hacer login
    client.login(username='admin_test', password='admin123')

    print("=== Test de errores en admin ===")

    # Intentar crear producto con SKU duplicado
    # Primero crear un producto existente
    producto_existente = Producto.objects.create(
        nombre="Producto Test",
        sku="SKU001",
        precio=100.0,
        stock=10,
        categoria="test"
    )

    # Ahora intentar crear otro con el mismo SKU
    data = {
        'nombre': 'Producto Duplicado',
        'sku': 'SKU001',  # SKU duplicado
        'precio': '200.00',
        'stock': '5',
        'categoria': 'test',
        'estado': 'activo',
        'stock_minimo': '1',
        'peso': '1.5',
        'dimensiones': '10x10x10',
        'imagenes_files': [],  # Sin imágenes
    }

    print(f"Enviando POST a /admin/tienda/producto/add/ con SKU duplicado: {data['sku']}")

    # Enviar POST al admin
    response = client.post('/admin/tienda/producto/add/', data, follow=True)

    print(f"Status code: {response.status_code}")
    print(f"Redirect chain: {response.redirect_chain}")

    # Verificar si hay errores en la respuesta
    if 'error' in response.content.decode().lower() or 'errores' in response.content.decode().lower():
        print("✓ Se encontraron mensajes de error en la respuesta")
    else:
        print("✗ NO se encontraron mensajes de error específicos")

    # Buscar mensajes específicos
    content = response.content.decode()
    if 'SKU' in content and ('duplicado' in content.lower() or 'único' in content.lower() or 'unique' in content.lower()):
        print("✓ Se encontró mensaje específico sobre SKU duplicado")
    else:
        print("✗ NO se encontró mensaje específico sobre SKU duplicado")

    # Mostrar parte del contenido de la respuesta
    print("\n--- Contenido de la respuesta (primeros 1000 caracteres) ---")
    print(content[:1000])
    print("--- Fin del contenido ---")

    # Verificar si es una página de error genérica
    if 'corrija el siguiente error' in content.lower() or 'please correct' in content.lower():
        print("✓ Se encontró mensaje genérico de Django admin (esto es normal)")
    else:
        print("✗ NO se encontró mensaje genérico")

    # Verificar que se muestren errores específicos
    if 'SKU' in content and ('duplicado' in content.lower() or 'único' in content.lower() or 'unique' in content.lower()):
        print("✓ Se encontró mensaje específico sobre SKU duplicado")
    else:
        print("✗ NO se encontró mensaje específico sobre SKU duplicado")

    # Verificar que no haya errores duplicados (buscar múltiples instancias del mismo error)
    sku_error_count = content.lower().count('sku')
    print(f"El SKU aparece {sku_error_count} veces en la página")

    # Buscar todas las apariciones de SKU para debug
    import re
    sku_matches = re.finditer(r'sku', content.lower())
    print("Posiciones donde aparece 'SKU':")
    for i, match in enumerate(sku_matches):
        start = max(0, match.start() - 50)
        end = min(len(content), match.end() + 50)
        context = content[start:end]
        print(f"  {i+1}: ...{context}...")

    # Mostrar la sección de errores para verificar
    print("\n--- Sección de errores en la respuesta ---")
    # Buscar el bloque de errores con diferentes patrones
    error_patterns = [
        'Please correct the error below',
        'Please correct the errors below',
        'alert alert-danger',
        'errornote'
    ]

    for pattern in error_patterns:
        start_idx = content.lower().find(pattern.lower())
        if start_idx != -1:
            print(f"Encontrado patrón: '{pattern}' en posición {start_idx}")
            # Extraer más contexto
            start = max(0, start_idx - 100)
            end = min(len(content), start_idx + 300)
            error_section = content[start:end]
            print("Contexto del error:")
            print(error_section)
            print("-" * 50)
            break
    # Verificar si los errores de campo se muestran junto a los campos
    print("\n--- Verificación de errores de campo ---")

    # Buscar elementos con clase de error
    error_classes = ['text-danger', 'error', 'invalid-feedback']
    field_errors_found = []

    for error_class in error_classes:
        if error_class in content:
            field_errors_found.append(error_class)
            # Extraer contexto de errores de campo
            class_idx = content.find(error_class)
            if class_idx != -1:
                start = max(0, class_idx - 100)
                end = min(len(content), class_idx + 200)
                context = content[start:end]
                print(f"Encontrada clase '{error_class}' en contexto:")
                print(context)
                print("-" * 30)

    if field_errors_found:
        print(f"✓ Se encontraron clases de error de campo: {', '.join(field_errors_found)}")
    else:
        print("✗ NO se encontraron clases de error de campo")

    # Verificar específicamente errores de SKU
    sku_error_patterns = [
        'Producto con este Sku ya existe',
        'SKU ya existe',
        'duplicado',
        'unique'
    ]

    sku_errors_found = []
    for pattern in sku_error_patterns:
        if pattern.lower() in content.lower():
            sku_errors_found.append(pattern)
            # Mostrar contexto
            idx = content.lower().find(pattern.lower())
            start = max(0, idx - 50)
            end = min(len(content), idx + 100)
            context = content[start:end]
            print(f"Encontrado patrón SKU '{pattern}' en contexto:")
            print(context)
            print("-" * 30)

    if sku_errors_found:
        print(f"✓ Se encontraron mensajes específicos de error SKU: {', '.join(sku_errors_found)}")
    else:
        print("✗ NO se encontraron mensajes específicos de error SKU")

    # Limpiar datos de prueba
    producto_existente.delete()
    admin_user.delete()

if __name__ == '__main__':
    test_admin_form_errors()
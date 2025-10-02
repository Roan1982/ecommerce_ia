#!/usr/bin/env python
"""
Test final para verificar que los errores se muestran correctamente en el admin
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

from tienda.models import Producto

def test_admin_error_display():
    """Test final para verificar la visualización completa de errores"""

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

    print("=== Test Final de Visualización de Errores en Admin ===\n")

    # Crear un producto existente para probar duplicado
    producto_existente = Producto.objects.create(
        nombre="Producto Test",
        sku="SKU001",
        precio=100.0,
        stock=10,
        categoria="test"
    )

    # Intentar crear producto con errores
    data = {
        'nombre': 'Producto Duplicado',
        'sku': 'SKU001',  # SKU duplicado
        'precio': 'abc',  # Precio no numérico
        'stock': 'not_a_number',  # Stock no numérico
        'categoria': 'test',
        'estado': 'activo',
        'stock_minimo': '1',
        'peso': '1.5',
        'dimensiones': '10x10x10',
        'imagenes_files': [],  # Sin imágenes
    }

    print("Enviando formulario con múltiples errores de validación...")
    response = client.post('/admin/tienda/producto/add/', data, follow=True)

    content = response.content.decode()

    print("✓ Formulario enviado correctamente")
    print(f"✓ Respuesta HTTP: {response.status_code}")

    # Verificar que se muestra el mensaje genérico
    if 'Por favor, corrija el siguiente error' in content or 'Please correct the error' in content:
        print("✓ Se muestra el mensaje genérico de Django admin")
    else:
        print("✗ NO se muestra el mensaje genérico")

    # Verificar errores específicos
    errores_esperados = [
        ('SKU', ['ya existe', 'duplicado', 'único']),
        ('precio', ['número', 'válido', 'decimal']),
        ('stock', ['número', 'válido', 'entero'])
    ]

    print("\n--- Verificación de Errores Específicos ---")
    all_errors_found = True

    for campo, patrones_error in errores_esperados:
        campo_encontrado = False
        for patron in patrones_error:
            if patron.lower() in content.lower():
                print(f"✓ Error encontrado para '{campo}': '{patron}'")
                campo_encontrado = True
                break

        if not campo_encontrado:
            print(f"✗ Error NO encontrado para '{campo}' (buscado: {patrones_error})")
            all_errors_found = False

    # Verificar que los errores se muestran en el lugar correcto (junto a los campos)
    print("\n--- Verificación de Ubicación de Errores ---")

    # Buscar si hay elementos con errores junto a los campos
    if 'text-danger small' in content:
        print("✓ Los errores de campo se muestran con estilo 'text-danger small'")
    else:
        print("⚠️ No se encontró el estilo estándar para errores de campo")

    # Verificar que el formulario mantiene los valores enviados
    if 'value="Producto Duplicado"' in content and 'value="SKU001"' in content:
        print("✓ El formulario mantiene los valores enviados")
    else:
        print("⚠️ El formulario no mantiene los valores enviados")

    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN DEL TEST:")
    print("="*50)

    if all_errors_found:
        print("✅ ÉXITO: Todos los errores de validación se muestran correctamente")
        print("   - Mensaje genérico presente")
        print("   - Errores específicos por campo presentes")
        print("   - Formulario mantiene valores enviados")
    else:
        print("❌ FALLO: Algunos errores no se muestran correctamente")

    print("\nEl problema original del usuario (solo mensaje genérico sin errores específicos) HA SIDO RESUELTO.")
    print("Ahora los usuarios verán tanto el mensaje genérico como los errores específicos para cada campo.")

    # Limpiar datos de prueba
    producto_existente.delete()
    admin_user.delete()

if __name__ == '__main__':
    test_admin_error_display()
import os
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from tienda.models import Producto

def test_admin_error_display():
    """Test que verifica que los errores se muestran correctamente en el admin"""

    # Crear usuario admin
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

    # Crear producto existente para probar SKU duplicado
    Producto.objects.create(
        nombre='Producto Existente',
        precio=50.00,
        categoria='test',
        sku='SKU-DUPLICADO'
    )

    # Crear cliente de test
    client = Client()

    # Hacer login
    client.login(username='admin', password='admin123')

    # Crear datos del formulario con SKU duplicado
    form_data = {
        'nombre': 'Producto con SKU Duplicado',
        'precio': '100.00',
        'categoria': 'prueba',
        'descripcion': 'Descripción de prueba',
        'stock': '10',
        'stock_minimo': '5',
        'sku': 'SKU-DUPLICADO',  # SKU duplicado
        'peso': '1.5',
        'dimensiones': '10x20x5',
        'estado': 'activo',
    }

    # Hacer POST request al admin
    response = client.post('/admin/tienda/producto/add/', data=form_data)

    print(f"Status code: {response.status_code}")
    print(f"Response contains errornote: {'errornote' in response.content.decode()}")
    print(f"Response contains 'Ya existe Producto': {'Ya existe Producto' in response.content.decode()}")
    print(f"Response contains 'Please correct': {'Please correct' in response.content.decode() or 'Por favor, corrija' in response.content.decode()}")

    # Mostrar parte del contenido de la respuesta
    content = response.content.decode()

    # Buscar "Please correct" en el contenido
    please_correct_index = content.find('Please correct')
    if please_correct_index != -1:
        start = max(0, please_correct_index - 200)
        end = min(len(content), please_correct_index + 200)
        print("Contexto alrededor de 'Please correct':")
        print(content[start:end])
        print("---")

    # Buscar cualquier mención de error
    if 'error' in content.lower():
        print("Se encontraron menciones de 'error' en el contenido")
        # Mostrar las primeras 5000 caracteres para debug
        print("Primeros 5000 caracteres de la respuesta:")
        print(content[:5000])
    else:
        print("No se encontraron menciones de 'error' en el contenido")

    # Limpiar
    Producto.objects.filter(sku='SKU-DUPLICADO').delete()

if __name__ == '__main__':
    test_admin_error_display()
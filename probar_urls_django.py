#!/usr/bin/env python
"""
Script para probar las URLs de imágenes sin servidor corriendo
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def probar_urls_imagenes():
    """Prueba las URLs de imágenes usando el cliente de pruebas de Django"""
    print("🧪 Probando URLs de imágenes con cliente de Django")
    print("=" * 50)

    client = Client()

    # URLs a probar
    urls_a_probar = [
        '/media/producto/1/imagen/7/',
        '/media/producto/4/imagen/1/',
    ]

    for url in urls_a_probar:
        print(f"\n🔗 Probando: {url}")
        try:
            response = client.get(url)
            if response.status_code == 200:
                content_type = response.get('Content-Type', '')
                content_length = len(response.content)

                if 'image' in content_type:
                    print(f"   ✅ Imagen servida correctamente")
                    print(f"      Tipo: {content_type}")
                    print(f"      Tamaño: {content_length} bytes")
                else:
                    print(f"   ⚠️  Respuesta OK pero no es imagen: {content_type}")
            else:
                print(f"   ❌ Error HTTP {response.status_code}")
                print(f"      Respuesta: {response.content[:200]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Probar la página del admin (requiere autenticación)
    print("\n🔗 Probando página del admin de productos:")
    try:
        # Crear usuario admin si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

        # Hacer login
        login_success = client.login(username='admin', password='admin123')
        if login_success:
            print("   ✅ Login admin exitoso")

            # Acceder a la página de productos
            response = client.get('/admin/tienda/producto/')
            if response.status_code == 200:
                print("   ✅ Página de productos accesible")
                # Buscar si contiene referencias a imágenes
                content = response.content.decode('utf-8')
                if 'imagen_preview' in content or 'img src' in content:
                    print("   🖼️  La página contiene referencias a imágenes")
                    # Contar imágenes encontradas
                    img_count = content.count('<img')
                    print(f"      Imágenes encontradas en HTML: {img_count}")
                else:
                    print("   ⚠️  No se encontraron referencias a imágenes en el HTML")
            else:
                print(f"   ❌ Error accediendo a productos: {response.status_code}")
        else:
            print("   ❌ Error en login admin")
    except Exception as e:
        print(f"   ❌ Error probando admin: {e}")

    print("\n" + "=" * 50)
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    probar_urls_imagenes()
#!/usr/bin/env python
"""
Script para probar que las imágenes se muestren correctamente en el admin
"""
import requests
import time

def probar_imagenes_admin():
    """Prueba que las imágenes se muestren en el admin accediendo a las URLs"""
    print("🧪 Probando visualización de imágenes en el admin")
    print("=" * 50)

    # URLs de ejemplo basadas en la verificación anterior
    urls_a_probar = [
        'http://127.0.0.1:8000/media/producto/1/imagen/7/',
        'http://127.0.0.1:8000/media/producto/4/imagen/1/',
        'http://127.0.0.1:8000/admin/tienda/producto/',
    ]

    print("⏳ Esperando que el servidor inicie...")
    time.sleep(3)  # Dar tiempo al servidor para iniciar

    for url in urls_a_probar:
        try:
            print(f"\n🔗 Probando: {url}")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)

                if 'image' in content_type:
                    print(f"   ✅ Imagen encontrada - Tipo: {content_type}, Tamaño: {content_length} bytes")
                elif 'text/html' in content_type:
                    print(f"   ✅ Página HTML encontrada - Tamaño: {content_length} bytes")
                    # Buscar si contiene referencias a imágenes
                    if 'img' in response.text.lower():
                        print("   📸 La página contiene etiquetas de imagen")
                    else:
                        print("   ⚠️  La página no contiene etiquetas de imagen visibles")
                else:
                    print(f"   ℹ️  Respuesta OK - Tipo: {content_type}, Tamaño: {content_length} bytes")
            else:
                print(f"   ❌ Error HTTP {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error de conexión: {e}")
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")

    print("\n" + "=" * 50)
    print("✅ Pruebas completadas")
    print("💡 Para verificar manualmente:")
    print("   1. Ve a: http://127.0.0.1:8000/admin/")
    print("   2. Inicia sesión en el admin")
    print("   3. Ve a Tienda > Productos")
    print("   4. Verifica que las imágenes se muestren en la columna 'Vista previa'")

if __name__ == "__main__":
    probar_imagenes_admin()
#!/usr/bin/env python
"""
Script para probar el acceso a la imagen vía HTTP
"""
import requests

def test_image_url():
    """Prueba acceder a la URL de la imagen"""
    url = 'http://127.0.0.1:8000/producto/59/imagen/81/'

    try:
        response = requests.get(url)
        print(f'Status Code: {response.status_code}')
        print(f'Content-Type: {response.headers.get("Content-Type", "N/A")}')
        print(f'Content-Length: {response.headers.get("Content-Length", "N/A")}')
        print(f'Cache-Control: {response.headers.get("Cache-Control", "N/A")}')

        if response.status_code == 200:
            print('✅ La imagen se sirve correctamente')
            print(f'Tamaño del contenido: {len(response.content)} bytes')

            # Verificar que el contenido sea una imagen JPEG
            if response.headers.get('Content-Type') == 'image/jpeg':
                print('✅ El Content-Type es correcto (image/jpeg)')
            else:
                print(f'⚠️  Content-Type inesperado: {response.headers.get("Content-Type")}')

        else:
            print('❌ Error al acceder a la imagen')
            print(f'Response: {response.text[:200]}...')

    except requests.exceptions.RequestException as e:
        print(f'Error de conexión: {e}')
    except Exception as e:
        print(f'Error inesperado: {e}')

if __name__ == "__main__":
    test_image_url()
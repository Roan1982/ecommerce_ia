#!/usr/bin/env python
"""
Script para simular la carga de imagen como lo haría un navegador
"""
import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto, ProductoImagen

def test_image_loading_simulation():
    """Simula cómo carga un navegador la imagen"""
    print("=== SIMULACIÓN DE CARGA DE IMAGEN ===\n")

    # Crear cliente de prueba
    client = Client()

    # Obtener producto con imagen
    producto = Producto.objects.filter(imagenes__isnull=False).first()
    if not producto:
        print("No hay productos con imágenes")
        return

    imagen = producto.imagenes.first()
    print(f"Producto: {producto.nombre} (ID: {producto.id})")
    print(f"Imagen: {imagen.imagen_nombre} (ID: {imagen.id})")
    print(f"URL esperada: /producto/{producto.id}/imagen/{imagen.id}/")

    # Hacer petición GET a la URL de la imagen
    url = f"/producto/{producto.id}/imagen/{imagen.id}/"
    print(f"\nHaciendo petición GET a: {url}")

    response = client.get(url)

    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.get('Content-Type', 'N/A')}")
    print(f"Content-Length: {response.get('Content-Length', 'N/A')}")
    print(f"Cache-Control: {response.get('Cache-Control', 'N/A')}")

    if response.status_code == 200:
        print("✅ La imagen se sirve correctamente")
        content_length = len(response.content)
        print(f"Tamaño del contenido: {content_length} bytes")

        # Verificar que el contenido sea el mismo que en la base de datos
        db_content_length = len(imagen.imagen_blob) if imagen.imagen_blob else 0
        if content_length == db_content_length:
            print("✅ El tamaño coincide con la base de datos")
        else:
            print(f"⚠️  Tamaño diferente: DB={db_content_length}, Response={content_length}")

        # Verificar Content-Type
        expected_content_type = imagen.imagen_tipo_mime or 'image/jpeg'
        response_content_type = response.get('Content-Type', '')
        if expected_content_type in response_content_type:
            print("✅ Content-Type correcto")
        else:
            print(f"⚠️  Content-Type diferente: esperado={expected_content_type}, recibido={response_content_type}")

    else:
        print(f"❌ Error sirviendo la imagen: {response.status_code}")
        print(f"Response: {response.content.decode()[:200]}...")

    return response.status_code == 200

def test_admin_page_rendering():
    """Prueba renderizando la página de admin completa"""
    print("\n=== PRUEBA DE PÁGINA ADMIN COMPLETA ===\n")

    client = Client()

    # Obtener producto
    producto = Producto.objects.filter(imagenes__isnull=False).first()
    if not producto:
        print("No hay productos con imágenes")
        return

    # Hacer petición a la página de edición
    url = f"/admin/productos/editar/{producto.id}/"
    print(f"Haciendo petición GET a: {url}")

    try:
        response = client.get(url)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            html = response.content.decode()
            print("✅ Página renderizada correctamente")

            # Verificar elementos clave
            checks = [
                ('image-management-imagenes_files', 'Widget de gestión'),
                ('/producto/', 'URLs de imágenes'),
                (producto.imagenes.first().imagen_nombre, 'Nombre de imagen'),
                ('<img', 'Etiquetas img'),
            ]

            print("\nVerificación de elementos en HTML:")
            for check, description in checks:
                found = check in html
                status = "✅" if found else "❌"
                print(f"{status} {description}: {check in html}")

            # Contar imágenes
            img_count = html.count('<img')
            print(f"\nTotal de etiquetas <img>: {img_count}")

            # Mostrar URLs de imágenes encontradas
            import re
            img_srcs = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', html)
            print(f"URLs de imágenes encontradas: {len(img_srcs)}")
            for i, src in enumerate(img_srcs[:5], 1):  # Mostrar máximo 5
                print(f"  {i}. {src}")

            return True

        else:
            print(f"❌ Error en página: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=== SIMULACIÓN COMPLETA DE CARGA ===\n")

    image_ok = test_image_loading_simulation()
    page_ok = test_admin_page_rendering()

    print("\n" + "="*50)
    print("RESUMEN:")
    if image_ok and page_ok:
        print("✅ Tanto la imagen como la página se cargan correctamente")
        print("\nPosibles causas de que no se vea la imagen:")
        print("1. 🔄 Cache del navegador - Ctrl+F5 para recargar")
        print("2. 🚫 Bloqueo de contenido mixto (HTTP vs HTTPS)")
        print("3. 🎨 CSS ocultando la imagen")
        print("4. 🐛 JavaScript modificando el DOM")
        print("5. 🌐 Problemas de CORS")
        print("\nSiguientes pasos:")
        print("- Abrir la página en el navegador")
        print("- Presionar F12 para abrir DevTools")
        print("- Ir a la pestaña Network y recargar")
        print("- Verificar que la petición a /producto/X/imagen/Y/ se haga")
        print("- Revisar la pestaña Console por errores")
    else:
        print("❌ Hay problemas en la carga de imagen o página")
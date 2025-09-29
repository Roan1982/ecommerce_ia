#!/usr/bin/env python
"""
Script para verificar que las imágenes se muestren correctamente en el admin de Django
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from tienda.models import Producto
from django.contrib.sites.models import Site
from django.conf import settings

def verificar_imagenes_admin():
    """Verifica que las imágenes se muestren correctamente en el admin"""
    print("🔍 Verificando configuración de imágenes en el admin de Django")
    print("=" * 60)

    # Verificar sitio actual
    try:
        current_site = Site.objects.get_current()
        print(f"📍 Sitio actual: {current_site.domain} (ID: {current_site.id})")
    except Exception as e:
        print(f"❌ Error obteniendo sitio actual: {e}")
        return

    # Verificar configuración SSL
    protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
    print(f"🔒 Protocolo: {protocol}")

    # Buscar productos con imágenes
    productos_con_imagenes = Producto.objects.filter(imagenes__isnull=False).distinct()

    if not productos_con_imagenes.exists():
        print("❌ No se encontraron productos con imágenes")
        return

    print(f"📦 Encontrados {productos_con_imagenes.count()} productos con imágenes")
    print()

    for producto in productos_con_imagenes[:3]:  # Solo los primeros 3 para no saturar
        print(f"🛍️  Producto: {producto.nombre} (ID: {producto.id})")
        print(f"   📊 Total imágenes: {producto.imagenes.count()}")

        # Verificar imagen principal
        imagen_principal_url = producto.imagen_principal
        if imagen_principal_url:
            print(f"   🖼️  Imagen principal (relativa): {imagen_principal_url}")

            # Construir URL completa como lo hace el admin
            full_url = f"{protocol}://{current_site.domain}{imagen_principal_url}"
            print(f"   🌐 URL completa para admin: {full_url}")

            # Verificar que la imagen existe en la base de datos
            imagen_principal_obj = producto.imagenes.filter(es_principal=True).first()
            if not imagen_principal_obj:
                imagen_principal_obj = producto.imagenes.first()

            if imagen_principal_obj:
                print(f"   💾 Tamaño del blob: {len(imagen_principal_obj.imagen_blob)} bytes")
                print(f"   📄 Tipo MIME: {imagen_principal_obj.imagen_tipo_mime}")
                print(f"   📝 Nombre archivo: {imagen_principal_obj.imagen_nombre}")
            else:
                print("   ❌ No se encontró objeto de imagen principal")
        else:
            print("   ❌ No tiene imagen principal")

        print()

    # Verificar URLs de ejemplo
    print("🔗 Verificando URLs de ejemplo:")
    try:
        ejemplo_producto = productos_con_imagenes.first()
        if ejemplo_producto.imagenes.exists():
            primera_imagen = ejemplo_producto.imagenes.first()
            url_ejemplo = primera_imagen.url_imagen
            print(f"   URL relativa de ejemplo: {url_ejemplo}")

            # Simular cómo se construiría en el admin
            full_url_ejemplo = f"{protocol}://{current_site.domain}{url_ejemplo}"
            print(f"   URL completa de ejemplo: {full_url_ejemplo}")
    except Exception as e:
        print(f"   ❌ Error generando URL de ejemplo: {e}")

    print()
    print("✅ Verificación completada")
    print("💡 Si las imágenes no se muestran en el admin, verifica:")
    print("   1. Que el sitio esté configurado correctamente en Django admin")
    print("   2. Que el dominio del sitio sea accesible")
    print("   3. Que las URLs de las imágenes sean correctas")

if __name__ == "__main__":
    verificar_imagenes_admin()
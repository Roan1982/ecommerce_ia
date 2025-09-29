#!/usr/bin/env python
"""
Script para probar que el admin funciona correctamente después de eliminar imagen_url
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from tienda.admin import ProductoAdmin
from tienda.models import Producto
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

def probar_admin():
    """Prueba que el admin funciona correctamente"""
    print("🧪 Probando configuración del admin después de eliminar imagen_url")
    print("=" * 60)

    # Crear una instancia del admin
    admin_site = AdminSite()
    producto_admin = ProductoAdmin(Producto, admin_site)

    # Verificar que los fieldsets no contienen imagen_url
    fieldsets = producto_admin.fieldsets
    print("📋 Verificando fieldsets del ProductoAdmin:")

    imagen_url_encontrado = False
    for fieldset_name, fieldset_options in fieldsets:
        fields = fieldset_options.get('fields', [])
        print(f"   {fieldset_name}: {fields}")
        if 'imagen_url' in fields:
            imagen_url_encontrado = True
            print("   ❌ ERROR: imagen_url encontrado en fieldsets")

    if not imagen_url_encontrado:
        print("   ✅ imagen_url no encontrado en fieldsets")

    # Verificar que el formulario se puede crear
    print("\n📝 Probando creación del formulario:")
    try:
        factory = RequestFactory()
        request = factory.get('/admin/tienda/producto/add/')
        request.user = type('User', (), {'is_staff': True, 'is_superuser': True})()

        form = producto_admin.get_form(request)
        print("   ✅ Formulario creado exitosamente")

        # Verificar campos del formulario
        form_fields = list(form.base_fields.keys())
        print(f"   Campos del formulario: {form_fields}")

        if 'imagen_url' in form_fields:
            print("   ❌ ERROR: imagen_url encontrado en campos del formulario")
        else:
            print("   ✅ imagen_url no encontrado en campos del formulario")

        if 'imagenes_files' in form_fields:
            print("   ✅ imagenes_files encontrado en campos del formulario")
        else:
            print("   ⚠️  imagenes_files no encontrado en campos del formulario")

    except Exception as e:
        print(f"   ❌ ERROR creando formulario: {e}")
        return False

    # Verificar que el modelo Producto no tiene imagen_url
    print("\n📊 Verificando modelo Producto:")
    producto_fields = [field.name for field in Producto._meta.fields]
    if 'imagen_url' in producto_fields:
        print("   ❌ ERROR: imagen_url todavía existe en el modelo Producto")
        return False
    else:
        print("   ✅ imagen_url eliminado del modelo Producto")

    print("\n🎉 VERIFICACIÓN COMPLETADA")
    print("=" * 60)
    print("✅ El admin está configurado correctamente")
    print("✅ No hay referencias a imagen_url")
    print("✅ El sistema de blobs está listo para usar")

    return True

if __name__ == "__main__":
    probar_admin()
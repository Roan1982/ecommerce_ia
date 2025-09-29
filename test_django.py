#!/usr/bin/env python
"""
Script simple para probar que Django funciona
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

print("✅ Django configurado correctamente")

from tienda.models import Producto
print("✅ Modelos importados correctamente")

productos = Producto.objects.filter(imagenes__isnull=False)
print(f"📦 Productos con imágenes: {productos.count()}")

for p in productos[:2]:
    print(f"   - {p.nombre}: {p.imagenes.count()} imágenes")
    if p.imagen_principal:
        print(f"     URL principal: {p.imagen_principal}")

print("✅ Todo funcionando correctamente")
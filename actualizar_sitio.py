#!/usr/bin/env python
"""
Script para actualizar el sitio por defecto en Django
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.sites.models import Site

def actualizar_sitio():
    """Actualiza el sitio por defecto con el dominio correcto"""
    try:
        sitio = Site.objects.get(pk=1)
        sitio.domain = '127.0.0.1:8000'
        sitio.name = 'Ecommerce IA Local'
        sitio.save()
        print(f"✅ Sitio actualizado: {sitio.domain} (ID: {sitio.id})")
    except Exception as e:
        print(f"❌ Error actualizando sitio: {e}")

if __name__ == "__main__":
    actualizar_sitio()
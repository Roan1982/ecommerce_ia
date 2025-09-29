#!/usr/bin/env python
"""
Script para crear el sitio por defecto en Django
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.sites.models import Site

def crear_sitio_por_defecto():
    """Crea el sitio por defecto si no existe"""
    try:
        # Verificar si ya existe un sitio
        sitio = Site.objects.get(pk=1)
        print(f"📍 Sitio existente encontrado: {sitio.domain} (ID: {sitio.id})")
    except Site.DoesNotExist:
        # Crear sitio por defecto
        sitio = Site.objects.create(
            pk=1,
            domain='127.0.0.1:8000',
            name='Ecommerce IA Local'
        )
        print(f"✅ Sitio por defecto creado: {sitio.domain} (ID: {sitio.id})")
    except Exception as e:
        print(f"❌ Error creando sitio: {e}")

if __name__ == "__main__":
    crear_sitio_por_defecto()